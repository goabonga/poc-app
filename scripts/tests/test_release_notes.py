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


BUILD_OK = {"arch": "amd64", "state": "Successfully built"}
BUILD_OK_ARM = {"arch": "arm64", "state": "Successfully built"}
BUILD_KO = {"arch": "arm64", "state": "Failed to build"}
RESULTS = [
    {"series": "noble", "state": "success", "published": True, "builds": [BUILD_OK, BUILD_OK_ARM]},
    {"series": "jammy", "state": "failure", "published": False, "builds": [BUILD_OK, BUILD_KO]},
    {"series": "stonking", "state": "missing", "published": False, "builds": []},
]
ISSUES = {"jammy/arm64": 12, "stonking/*": 13}


def test_apt_section_explains_how_to_install_from_the_ppa() -> None:
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", DETAILS, RESULTS, ISSUES)
    assert "sudo add-apt-repository ppa:goabonga/poc" in text
    assert "sudo apt install poc-hello\n" in text
    assert "deb https://ppa.launchpadcontent.net/goabonga/poc/ubuntu <series> main" in text
    assert "one of noble" in text
    assert "ABCDEF0123456789" in text
    assert "for Ubuntu" in text


def test_apt_section_marks_what_failed_and_links_the_issues() -> None:
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", DETAILS, RESULTS, ISSUES)
    assert "| noble | amd64 ✅, arm64 ✅ |" in text
    assert "| jammy | amd64 ⚠️ built, not published yet, arm64 ❌ failed (#12) |" in text
    assert "| stonking | ❌ not built (missing) (#13) |" in text


def test_apt_section_lists_the_packages_attached_to_the_release() -> None:
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", DETAILS, RESULTS, ISSUES)
    assert "- `poc-hello_0.3.0_noble_arm64.deb`" in text
    assert "- `poc-hello_0.3.0_jammy_amd64.deb`" in text
    assert "jammy_arm64" not in text
    assert "sudo apt install ./poc-hello_0.3.0_noble_amd64.deb" in text


def test_apt_section_without_published_series_does_not_send_to_the_ppa() -> None:
    results = [RESULTS[1], RESULTS[2]]
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", DETAILS, results, ISSUES)
    assert "add-apt-repository" not in text
    assert "No series is published in the archive yet." in text
    assert "| jammy |" in text


def test_apt_section_leaves_out_what_launchpad_did_not_tell() -> None:
    details = {**DETAILS, "fingerprint": ""}
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", details, RESULTS, ISSUES)
    assert "add-apt-repository" in text
    assert "signed with the key" not in text


def test_apt_section_without_a_ppa_only_offers_the_debs() -> None:
    text = rn.section("apt", "poc-hello", "0.3.0", "ignored", None, RESULTS)
    assert "add-apt-repository" not in text
    assert "sudo apt install ./poc-hello_0.3.0_noble_amd64.deb" in text


def test_asset_names_say_what_the_file_is() -> None:
    deb = {"series": "noble", "arch": "arm64"}
    assert rn.asset_name("poc-hello", "0.4.0", deb) == "poc-hello_0.4.0_noble_arm64.deb"


def test_parse_debs_keeps_the_well_formed_entries() -> None:
    text = '[{"series":"a","arch":"b","url":"u"},{"series":"a"},"x"]'
    assert rn.parse_debs(text) == [{"series": "a", "arch": "b", "url": "u"}]
    assert rn.parse_debs("") == []
    assert rn.parse_debs("not json") == []


def test_parse_results_and_issues_tolerate_garbage() -> None:
    assert rn.parse_results("not json") == []
    assert rn.parse_results("") == []
    assert rn.parse_results('[{"series":"a"},"x",{"nope":1}]') == [{"series": "a"}]
    assert rn.parse_issues("not json") == {}
    assert rn.parse_issues('{"a/b": 3, "c": "x"}') == {"a/b": 3}
    assert rn.parse_issues("[1]") == {}


def test_aur_section_explains_how_to_install_from_the_aur() -> None:
    text = rn.section("aur", "poc-pinger", "0.3.0", "https://aur.archlinux.org/packages/poc-pinger")
    assert "yay -S poc-pinger" in text
    assert "git clone https://aur.archlinux.org/poc-pinger.git" in text
    assert "makepkg -si" in text


def test_aur_section_mentions_the_archive_attached_to_the_release() -> None:
    name = rn.aur_archive_name("poc-pinger", "0.3.0")
    assert name == "poc-pinger_0.3.0_aur.tar.gz"
    url = "https://aur.archlinux.org/packages/poc-pinger"
    text = rn.section("aur", "poc-pinger", "0.3.0", url, archive=name)
    assert "`poc-pinger_0.3.0_aur.tar.gz`" in text and "yay -S poc-pinger" in text
    assert "attached" not in rn.section("aur", "poc-pinger", "0.3.0", url)


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


def test_main_notes_reads_the_notes_and_writes_them_back(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("notes\n"))
    argv = ["notes", "aur", "pinger", "0.3.0", AUR_URL, "--package", "poc-pinger"]
    assert rn.main(argv) == 0
    out = capsys.readouterr().out
    assert out.startswith("notes\n\n<!-- package:aur -->")
    assert "yay -S poc-pinger" in out


def test_main_falls_back_to_the_historical_package_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert rn.main(["notes", "aur", "hello", "0.3.0", AUR_URL]) == 0
    assert "yay -S poc-hello" in capsys.readouterr().out


def test_main_notes_looks_the_ppa_up_for_apt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io
    import json

    seen: list[tuple[str, str]] = []

    def fake(ppa: str, package: str) -> dict[str, str]:
        seen.append((ppa, package))
        return DETAILS

    monkeypatch.setattr(rn, "ppa_details", fake)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    argv = [
        "notes", "apt", "hello", "0.3.0", "x", "--ppa", "ppa:goabonga/poc",
        "--results", json.dumps(RESULTS), "--issues", json.dumps(ISSUES),
    ]
    assert rn.main(argv) == 0
    assert seen == [("ppa:goabonga/poc", "poc-hello")]
    out = capsys.readouterr().out
    assert "ABCDEF0123456789" in out and "poc-hello_0.3.0_noble_arm64.deb" in out and "(#12)" in out


def test_main_assets_lists_what_to_attach(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    debs = [
        {"series": "noble", "arch": "amd64", "url": "https://l/a.deb", "sha256": "aa"},
        {"series": "noble", "arch": "arm64", "url": "https://l/b.deb", "sha256": "bb"},
    ]
    assert rn.main(["assets", "poc-hello", "0.3.0", json.dumps(debs)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "poc-hello_0.3.0_noble_amd64.deb\thttps://l/a.deb\taa",
        "poc-hello_0.3.0_noble_arm64.deb\thttps://l/b.deb\tbb",
    ]


def test_main_needs_a_command() -> None:
    with pytest.raises(SystemExit):
        rn.main([])
