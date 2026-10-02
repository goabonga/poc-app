#!/usr/bin/env bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

# Re-author and GPG-sign a Dependabot commit, normalising its subject to
# Conventional Commits.
#
# Everything Dependabot can bump here is either a Go module or a pinned
# GitHub Action, so the routing is a plain two-way split: `ci` for workflow
# changes, `chore(deps)` for everything else (go.mod/go.sum).
#
# Run by `git rebase --exec` in dependabot-rewrite.yml.

set -euo pipefail

# This script amends HEAD in place. It takes no arguments, and anything passed
# to it means it was invoked by mistake -- refuse rather than rewrite somebody's
# commit. It also only ever rewrites a Dependabot commit.
if [ $# -gt 0 ]; then
    cat >&2 <<'USAGE'
rewrite-dependabot-commit.sh takes no arguments: it amends HEAD in place.
It is meant to be run by `git rebase --exec` in dependabot-rewrite.yml.
USAGE
    exit 2
fi

# Rewrite Dependabot's own commits and nothing else. Skipping rather than
# failing keeps the workflow green when `synchronize` replays it over a branch
# this script already rewrote (those commits are re-authored, so they no longer
# match) -- and stops a re-run from force-pushing a fresh SHA every time.
author_email=$(git log -1 --pretty=%ae HEAD)
case "$author_email" in
    *dependabot*) ;;
    *)
        echo "skipping $(git log -1 --pretty=%h HEAD): authored by $author_email, not Dependabot"
        exit 0
        ;;
esac

changed=$(git show --name-only --pretty='' HEAD)
subject=$(git log -1 --pretty=%s HEAD)
body=$(git log -1 --pretty=%b HEAD | sed '/^[Cc]o-authored-by:/d')

# Drop any leading conventional prefix Dependabot already added.
text=$(printf '%s' "$subject" | sed -E 's/^[a-z]+(\([^)]+\))?!?:[[:space:]]*//')

if printf '%s' "$changed" | grep -q '[.]github/workflows/'; then
    prefix="ci"
else
    prefix="chore(deps)"
fi

if [ -n "$body" ]; then
    new_msg=$(printf '%s: %s\n\n%s' "$prefix" "$text" "$body")
else
    new_msg=$(printf '%s: %s' "$prefix" "$text")
fi

git commit --amend --reset-author -m "$new_msg" --quiet
