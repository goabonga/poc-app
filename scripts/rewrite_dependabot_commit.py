#!/usr/bin/env python3

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

"""Re-author and GPG-sign a Dependabot commit as a Conventional Commit.

The type reflects what the bump affects:
  - GitHub Actions bumps -> ci        (not shipped)
  - Go module bumps      -> fix(deps) (linked into the binaries -> patch release)

Dependabot only bumps Go modules and pinned GitHub Actions here, so the
routing is a plain two-way split on the files the commit touches. Run by
`git rebase --exec` in dependabot-rewrite.yml.

The `title` command prints the pull request title matching the rewritten
commits, so the title and the history agree on the type.
"""

import os
import re
import subprocess
import sys

LEADING_TYPE = re.compile(r"^[a-z]+(\([^)]+\))?!?:\s*")
TRAILER = re.compile(r"^co-authored-by:", re.I)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def commit_type(changed: list[str]) -> str:
    if any(".github/workflows/" in path for path in changed):
        return "ci"
    return "fix(deps)"


def rewrite(changed: list[str], subject: str, body: str) -> str:
    """The Conventional Commit message of a Dependabot commit."""
    text = LEADING_TYPE.sub("", subject)
    body = "\n".join(
        line for line in body.splitlines() if not TRAILER.match(line)
    ).strip()
    message = f"{commit_type(changed)}: {text}"
    return f"{message}\n\n{body}" if body else message


def pull_request_title(title: str, subjects: list[str]) -> str:
    """The pull request title, typed like the rewritten commits.

    A single commit gives its subject; a group of commits keeps the title
    text under the type of its first commit.
    """
    if len(subjects) == 1:
        return subjects[0]
    typed = LEADING_TYPE.match(subjects[0]) if subjects else None
    if typed is None:
        return title
    return f"{typed.group(0)}{LEADING_TYPE.sub('', title)}"


def print_title(commit_range: str) -> None:
    subjects = git("log", "--reverse", "--pretty=%s", commit_range).splitlines()
    print(pull_request_title(os.environ["PR_TITLE"], subjects))


def main() -> None:
    changed = git("show", "--name-only", "--pretty=", "HEAD").splitlines()
    message = rewrite(
        changed,
        git("log", "-1", "--pretty=%s", "HEAD"),
        git("log", "-1", "--pretty=%b", "HEAD"),
    )
    _ = subprocess.run(
        ["git", "commit", "--amend", "--reset-author", "-m", message, "--quiet"],
        check=True,
    )


if __name__ == "__main__":
    if sys.argv[1:2] == ["title"]:
        print_title(sys.argv[2])
    else:
        main()
