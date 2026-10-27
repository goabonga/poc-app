# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parent.parent / "format_summary.py"
spec = importlib.util.spec_from_file_location("format_summary", SCRIPT)
assert spec is not None and spec.loader is not None
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)


@pytest.fixture
def report(tmp_path: Path) -> Callable[[str, Any], str]:
    def write(name: str, content: Any) -> str:
        path = tmp_path / name
        _ = path.write_text(
            content if isinstance(content, str) else json.dumps(content)
        )
        return str(path)

    return write


@pytest.fixture
def summary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    return path


def test_table_escapes_cells() -> None:
    assert (
        fs.table(["a", "b"], [("x|y", "l1\nl2")])
        == "| a | b |\n| --- | --- |\n| x\\|y | l1 l2 |"
    )


def test_fenced_keeps_the_tail() -> None:
    text = fs.fenced("\n".join(str(n) for n in range(100)), limit=3)
    assert text == "```text\n... 97 earlier lines omitted\n97\n98\n99\n```"
    assert fs.fenced("one") == "```text\none\n```"


def test_a_missing_report_is_explained() -> None:
    assert "No report was produced" in fs.license_headers("/nonexistent/report")
    assert "No report was produced" in fs.license_headers(None)


def test_license_headers_clean(report: Callable[[str, Any], str]) -> None:
    text = fs.license_headers(report("h.txt", "All files have license headers.\n" * 5))
    assert "5 location(s) checked" in text


def test_license_headers_missing(report: Callable[[str, Any], str]) -> None:
    text = fs.license_headers(
        report("h.txt", "All files have license headers.\nMissing header: a.go\n")
    )
    assert text.startswith("## ❌ SPDX license headers")
    assert "Missing header: a.go" in text


@pytest.mark.parametrize(
    ("status", "icon"), [("success", "✅"), ("failure", "❌"), ("cancelled", "⚠️")]
)
def test_text_summary(
    report: Callable[[str, Any], str], status: str, icon: str
) -> None:
    assert fs.text_summary("gofmt", report("o.txt", "output"), status).startswith(
        f"## {icon} gofmt"
    )


def test_text_summary_without_output(report: Callable[[str, Any], str]) -> None:
    assert "printed nothing" in fs.text_summary("go", report("o.txt", " "), "success")
    assert "printed nothing" in fs.text_summary("go", "/nonexistent", "success")


def test_release_summary(report: Callable[[str, Any], str]) -> None:
    assert "Nothing to release" in fs.release_summary("/nonexistent")
    assert "Nothing to release" in fs.release_summary(report("r.json", {"bumps": {}}))
    text = fs.release_summary(
        report(
            "r.json",
            {
                "bumps": {
                    "x": {"current_version": "0.1.0", "next_version": "0.2.0"},
                    "y": {},
                }
            },
        )
    )
    assert "| x | 0.1.0 | 0.2.0 |" in text
    assert "| y |  |  |" in text


def test_emit_appends_to_the_step_summary(summary_file: Path) -> None:
    fs.emit("one")
    fs.emit("two")
    assert summary_file.read_text() == "one\ntwo\n"


def test_emit_prints_without_a_step_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    fs.emit("one")
    assert capsys.readouterr().out == "one\n"


def test_main_dispatches_every_command(
    report: Callable[[str, Any], str],
    summary_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_STATUS", "success")
    fs.main(["headers", report("h.txt", "All files have license headers.")])
    fs.main(["release", report("rel.json", {"bumps": {}})])
    fs.main(["text", "gofmt", report("o.txt", "ok")])
    content = summary_file.read_text()
    for title in ("SPDX license headers", "release", "gofmt"):
        assert title in content


def test_main_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        fs.main([])
