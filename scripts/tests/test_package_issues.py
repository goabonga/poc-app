# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

import gzip
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parent.parent / "package_issues.py"
spec = importlib.util.spec_from_file_location("package_issues", SCRIPT)
assert spec is not None and spec.loader is not None
pi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi)

LOG = "https://launchpad.net/~o/+archive/ubuntu/p/+build/1/+files/log.txt.gz"
RESULTS: list[dict[str, Any]] = [
    {"series": "noble", "state": "success", "builds": [{"arch": "amd64", "state": "Successfully built"}]},
    {
        "series": "jammy",
        "state": "failure",
        "builds": [
            {"arch": "amd64", "state": "Successfully built"},
            {"arch": "arm64", "state": "Failed to build", "url": "https://launchpad.net/b", "log_url": LOG},
        ],
    },
    {"series": "stonking", "state": "missing", "builds": []},
]


def test_failures_are_the_builds_that_did_not_succeed_and_the_series_without_any() -> None:
    found = pi.failures(RESULTS)
    assert [failure["key"] for failure in found] == ["jammy/arm64", "stonking/*"]
    assert found[0]["state"] == "Failed to build" and found[0]["log_url"] == LOG
    assert found[1]["state"] == "missing"


def test_titles_name_the_series_and_the_architecture() -> None:
    found = pi.failures(RESULTS)
    assert pi.title("poc-hello", "0.6.0", found[0]) == "poc-hello 0.6.0 fails to build on jammy/arm64"
    assert pi.title("poc-hello", "0.6.0", found[1]) == "poc-hello 0.6.0 was not built for stonking"


def test_body_follows_the_bug_report_template() -> None:
    failure = pi.failures(RESULTS)[0]
    text = pi.body("hello", "poc-hello", "0.6.0", "https://run", failure, "the log")
    for section in (
        "### Binary", "### Version", "### Description", "### Steps to Reproduce",
        "### Expected Behavior", "### Actual Behavior", "### Operating System", "### Logs / Output",
    ):
        assert section in text
    assert "`jammy` on `arm64`" in text and "https://launchpad.net/b" in text
    assert "https://run" in text and "```shell\nthe log\n```" in text


def test_log_tail_of_a_gzipped_log_shows_the_first_error_and_the_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = [f"line {n}" for n in range(300)] + ["go: failed to initialize build cache"] + [
        f"cleanup {n}" for n in range(200)
    ]

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return gzip.compress("\n".join(lines).encode())

    monkeypatch.setattr(pi.urllib.request, "urlopen", lambda url, timeout: Response())
    text = pi.log_tail(LOG)
    assert text.startswith("[around the first error]")
    assert "failed to initialize build cache" in text
    assert text.rstrip().endswith("cleanup 199")


def test_log_tail_without_error_is_the_end_of_the_log() -> None:
    assert pi.excerpt([f"l{n}" for n in range(200)]).splitlines()[-1] == "l199"
    assert len(pi.excerpt([f"l{n}" for n in range(200)]).splitlines()) == pi.LOG_LINES


def test_log_tail_only_asks_launchpad() -> None:
    assert pi.log_tail("https://example.com/log") == "No build log."
    assert pi.log_tail("") == "No build log."


def test_log_tail_survives_an_unreachable_log(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(url: str, timeout: int) -> None:
        raise OSError("down")

    monkeypatch.setattr(pi.urllib.request, "urlopen", fail)
    assert "could not be fetched" in pi.log_tail(LOG)


def test_main_opens_each_issue_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    created: list[str] = []
    monkeypatch.setattr(
        pi, "existing", lambda title: 7 if title.endswith("stonking") else None
    )
    monkeypatch.setattr(pi, "log_tail", lambda url: "tail")
    monkeypatch.setattr(pi, "create", lambda title, body: created.append(title) or 12)
    argv = ["hello", "poc-hello", "0.6.0", "https://run", json.dumps(RESULTS)]
    assert pi.main(argv) == 0
    assert created == ["poc-hello 0.6.0 fails to build on jammy/arm64"]
    assert json.loads(capsys.readouterr().out) == {"jammy/arm64": 12, "stonking/*": 7}


def test_main_needs_its_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert pi.main(["hello"]) == 2
    assert "usage" in capsys.readouterr().err
