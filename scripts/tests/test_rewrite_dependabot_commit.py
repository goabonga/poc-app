# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

import importlib.util
import subprocess
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).parent.parent / "rewrite_dependabot_commit.py"
spec = importlib.util.spec_from_file_location("rewrite_dependabot_commit", SCRIPT)
assert spec is not None and spec.loader is not None
rewrite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rewrite)


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ([".github/workflows/ci.yml"], "ci"),
        ([".github/workflows/ci.yml", "go.mod"], "ci"),
        (["go.mod", "go.sum"], "fix(deps)"),
        (["go.sum"], "fix(deps)"),
    ],
)
def test_commit_type(changed: list[str], expected: str) -> None:
    assert rewrite.commit_type(changed) == expected


def test_rewrite_normalizes_the_subject_and_drops_co_authors() -> None:
    message = rewrite.rewrite(
        ["go.mod"],
        "build(deps): bump golang.org/x/net from 1 to 2",
        "Details.\nCo-authored-by: bot <b@x.y>\n",
    )
    assert message == "fix(deps): bump golang.org/x/net from 1 to 2\n\nDetails."


def test_rewrite_without_a_body() -> None:
    assert (
        rewrite.rewrite(["go.mod"], "Bump golang.org/x/net from 1 to 2", "")
        == "fix(deps): Bump golang.org/x/net from 1 to 2"
    )


def test_main_amends_the_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = {
        ("show", "--name-only", "--pretty=", "HEAD"): "go.mod\n",
        ("log", "-1", "--pretty=%s", "HEAD"): "Bump golang.org/x/net from 1 to 2",
        ("log", "-1", "--pretty=%b", "HEAD"): "",
    }
    monkeypatch.setattr(rewrite, "git", lambda *args: answers[args])
    calls: list[Any] = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append((a[0], k)))
    rewrite.main()
    assert calls == [
        (
            [
                "git",
                "commit",
                "--amend",
                "--reset-author",
                "-m",
                "fix(deps): Bump golang.org/x/net from 1 to 2",
                "--quiet",
            ],
            {"check": True},
        )
    ]


def test_git_returns_stripped_output() -> None:
    assert rewrite.git("--version").startswith("git version")


def test_a_single_commit_gives_its_subject_to_the_pull_request() -> None:
    title = rewrite.pull_request_title(
        "chore(deps): bump golang.org/x/net from 0.14.0 to 0.15.2",
        ["fix(deps): bump golang.org/x/net from 0.14.0 to 0.15.2"],
    )
    assert title == "fix(deps): bump golang.org/x/net from 0.14.0 to 0.15.2"


def test_a_group_keeps_its_title_under_the_type_of_the_first_commit() -> None:
    title = rewrite.pull_request_title(
        "bump the x group with 2 updates",
        ["fix(deps): bump a from 1 to 2", "fix(deps): bump b from 1 to 2"],
    )
    assert title == "fix(deps): bump the x group with 2 updates"


@pytest.mark.parametrize("subjects", [[], ["not conventional", "still not"]])
def test_without_a_typed_commit_the_title_is_unchanged(subjects: list[str]) -> None:
    title = "chore(deps): bump the group"
    assert rewrite.pull_request_title(title, subjects) == title


def test_print_title_reads_the_range_and_the_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PR_TITLE", "bump the ci-actions group with 2 updates")
    monkeypatch.setattr(
        rewrite, "git", lambda *args: "ci: bump a from 1 to 2\nci: bump b from 1 to 2"
    )
    rewrite.print_title("origin/main..HEAD")
    assert capsys.readouterr().out == "ci: bump the ci-actions group with 2 updates\n"
