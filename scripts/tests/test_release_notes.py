# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "release_notes.py"
spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
assert spec is not None and spec.loader is not None
rn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rn)

AUR_URL = "https://aur.archlinux.org/packages/poc-hello"
DETAILS = {
    "ppa": "ppa:goabonga/poc",
    "distribution": "ubuntu",
    "series": "noble",
    "fingerprint": "ABCDEF0123456789",
    "sources_url": "https://ppa.launchpadcontent.net/goabonga/poc/ubuntu",
    "page_url": "https://launchpad.net/~goabonga/+archive/ubuntu/poc/+packages",
}


def test_apt_section_explains_how_to_install_from_the_ppa() -> None:
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", DETAILS)
    assert "sudo add-apt-repository ppa:goabonga/poc" in text
    assert "sudo apt install poc-hello\n" in text
    assert "deb https://ppa.launchpadcontent.net/goabonga/poc/ubuntu noble main" in text
    assert "ABCDEF0123456789" in text
    assert "Ubuntu `noble`" in text
    assert "sudo apt install ./poc-hello_0.3.0_amd64.deb" in text


def test_apt_section_leaves_out_what_launchpad_did_not_tell() -> None:
    details = {**DETAILS, "series": "", "fingerprint": ""}
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", details)
    assert "add-apt-repository" in text
    assert "deb-src" not in text
    assert "signed with the key" not in text


def test_apt_section_without_a_ppa_only_offers_the_deb() -> None:
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored")
    assert "add-apt-repository" not in text
    assert "sudo apt install ./poc-hello_0.3.0_amd64.deb" in text


def test_aur_section_explains_how_to_install_from_the_aur() -> None:
    text = rn.section("aur", "poc-pinger", "0.3.0", "https://aur.archlinux.org/packages/poc-pinger")
    assert "yay -S poc-pinger" in text
    assert "git clone https://aur.archlinux.org/poc-pinger.git" in text
    assert "makepkg -si" in text


def test_aur_section_without_an_aur_push_says_so() -> None:
    text = rn.section("aur", "poc-hello", "0.3.0", "https://github.com/x/releases/download/a")
    assert "not pushed to the AUR" in text
    assert "yay" not in text
    assert "https://github.com/x/releases/download/a" in text


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown package kind"):
        rn.section("rpm", "poc-hello", "0.3.0", "")


def test_ppa_details_come_from_the_launchpad_api(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, str] | None]] = []

    def fake(url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        calls.append((url, params))
        if params:
            return {
                "entries": [{"distro_series_link": "https://api.launchpad.net/1.0/ubuntu/noble"}]
            }
        return {
            "distribution_link": "https://api.launchpad.net/1.0/ubuntu",
            "signing_key_fingerprint": "ABCDEF0123456789",
        }

    monkeypatch.setattr(rn, "fetch", fake)
    assert rn.ppa_details("ppa:goabonga/poc", "poc-hello") == DETAILS
    assert calls[0][0] == "https://api.launchpad.net/1.0/~goabonga/+archive/ubuntu/poc"
    assert calls[1][1] is not None and calls[1][1]["source_name"] == "poc-hello"


def test_ppa_details_without_a_published_source(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        if params:
            return {"entries": []}
        return {"distribution_link": "https://api.launchpad.net/1.0/ubuntu"}

    monkeypatch.setattr(rn, "fetch", fake)
    details = rn.ppa_details("ppa:goabonga/poc", "poc-hello")
    assert details is not None
    assert details["series"] == "" and details["fingerprint"] == ""


@pytest.mark.parametrize("ppa", ["", "goabonga/poc", "ppa:nameonly"])
def test_ppa_details_rejects_a_malformed_ppa(ppa: str) -> None:
    assert rn.ppa_details(ppa, "poc-hello") is None


def test_ppa_details_survive_an_unreachable_launchpad(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        raise OSError("down")

    monkeypatch.setattr(rn, "fetch", fake)
    assert rn.ppa_details("ppa:goabonga/poc", "poc-hello") is None


def test_upsert_appends_after_the_existing_notes() -> None:
    notes = rn.upsert("## [0.3.0]\n- feat: x\n", "apt", "TEXT")
    assert notes == "## [0.3.0]\n- feat: x\n\n<!-- package:apt -->\nTEXT\n<!-- /package:apt -->\n"


def test_upsert_into_empty_notes() -> None:
    assert rn.upsert("", "aur", "TEXT") == "<!-- package:aur -->\nTEXT\n<!-- /package:aur -->\n"


def test_upsert_replaces_its_own_section_only() -> None:
    first = rn.upsert("notes\n", "apt", "OLD")
    both = rn.upsert(first, "aur", "AUR")
    again = rn.upsert(both, "apt", "NEW")
    assert "OLD" not in again
    assert again.count("<!-- package:apt -->") == 1
    assert "NEW" in again and "AUR" in again and again.startswith("notes\n")


def test_upsert_is_stable_when_rerun() -> None:
    once = rn.upsert("notes\n", "apt", "TEXT")
    assert rn.upsert(once, "apt", "TEXT") == once


def test_main_reads_the_notes_and_writes_them_back(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("notes\n"))
    argv = ["aur", "pinger", "0.3.0", AUR_URL, "--package", "poc-pinger"]
    assert rn.main(argv) == 0
    out = capsys.readouterr().out
    assert out.startswith("notes\n\n<!-- package:aur -->")
    assert "yay -S poc-pinger" in out


def test_main_falls_back_to_the_historical_package_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert rn.main(["aur", "hello", "0.3.0", AUR_URL]) == 0
    assert "yay -S poc-hello" in capsys.readouterr().out


def test_main_looks_the_ppa_up_for_apt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    seen: list[tuple[str, str]] = []

    def fake(ppa: str, package: str) -> dict[str, str]:
        seen.append((ppa, package))
        return DETAILS

    monkeypatch.setattr(rn, "ppa_details", fake)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert rn.main(["apt", "hello", "0.3.0", "x", "--ppa", "ppa:goabonga/poc"]) == 0
    assert seen == [("ppa:goabonga/poc", "poc-hello")]
    assert "ABCDEF0123456789" in capsys.readouterr().out


def test_main_needs_its_positional_arguments() -> None:
    with pytest.raises(SystemExit):
        rn.main(["apt"])
