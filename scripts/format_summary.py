#!/usr/bin/env python3

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

"""Turn the output of a CI step into a GitHub job summary.

Each command reads the report of one step and appends a Markdown section to
``$GITHUB_STEP_SUMMARY`` (to stdout when unset). It only formats: the tool
step has already decided whether the job fails.
"""

import argparse
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NotRequired, TypedDict, cast


class Bump(TypedDict):
    current_version: NotRequired[str]
    next_version: NotRequired[str]


class ReleaseReport(TypedDict):
    bumps: NotRequired[dict[str, Bump]]


class Arguments(argparse.Namespace):
    """The parsed command line, typed."""

    command: str = ""
    report: str = ""
    title: str = ""


OK, FAIL, WARN = "✅", "❌", "⚠️"
TAIL_LINES = 40


def load_json(path: str | None) -> object | None:
    """The parsed report, which callers cast to the shape their tool writes."""
    if not (path and Path(path).is_file()):
        return None
    return cast(object, json.loads(Path(path).read_text()))


def read_text(path: str | None) -> str | None:
    return Path(path).read_text() if path and Path(path).is_file() else None


def cell(value: object) -> str:
    """A value that is safe inside a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def fenced(text: str, limit: int = TAIL_LINES) -> str:
    lines = text.strip().splitlines()
    if len(lines) > limit:
        lines = [f"... {len(lines) - limit} earlier lines omitted", *lines[-limit:]]
    return "```text\n" + "\n".join(lines) + "\n```"


def missing_report(title: str, path: str | None) -> str:
    return f"## {WARN} {title}\n\nNo report was produced (`{path}`): the tool did not run to completion.\n"


def license_headers(path: str | None) -> str:
    text = read_text(path)
    if text is None:
        return missing_report("SPDX license headers", path)
    lines = [line for line in text.splitlines() if line.strip()]
    passed = sum(line.startswith("All files have license headers") for line in lines)
    problems = [line for line in lines if not line.startswith("All files have license headers")]
    if not problems:
        return f"## {OK} SPDX license headers\n\n{passed} location(s) checked, every file has its header.\n"
    return (
        f"## {FAIL} SPDX license headers\n\n{passed} location(s) fully headed; the others report:\n\n"
        + fenced("\n".join(problems))
        + "\n\nFix with `scripts/add_license_header.py` (without `--check`).\n"
    )


def text_summary(title: str, path: str | None, status: str) -> str:
    """A tool without a structured report: its status and the end of its output."""
    text = read_text(path)
    icon = OK if status == "success" else FAIL if status == "failure" else WARN
    body = fenced(text) if text and text.strip() else "The tool printed nothing."
    return f"## {icon} {title}\n\n{body}\n"


def release_summary(path: str | None) -> str:
    report = cast("ReleaseReport | None", load_json(path))
    if not report or not report.get("bumps"):
        return f"## {OK} release\n\nNothing to release: no `feat`, `fix` or `perf` commit since the last tag.\n"
    rows = [
        (name, bump.get("current_version", ""), bump.get("next_version", ""))
        for name, bump in report.get("bumps", {}).items()
    ]
    return f"## {OK} release\n\n" + table(["Component", "From", "To"], rows) + "\n"


def emit(text: str) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with Path(target).open("a") as stream:
            _ = stream.write(text + "\n")
    else:
        _ = sys.stdout.write(text + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("headers", "release"):
        _ = sub.add_parser(name).add_argument("report")
    text = sub.add_parser("text")
    _ = text.add_argument("title")
    _ = text.add_argument("report")
    args = parser.parse_args(argv, namespace=Arguments())
    if args.command == "text":
        emit(text_summary(args.title, args.report, os.environ.get("JOB_STATUS", "")))
    elif args.command == "headers":
        emit(license_headers(args.report))
    else:
        emit(release_summary(args.report))


if __name__ == "__main__":
    main()
