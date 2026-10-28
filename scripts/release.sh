#!/usr/bin/env bash

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

# Functions to work on a GitHub Release by its tag, draft or not. Source it:
#
#   . scripts/release.sh
#   id=$(release_id hello-v0.6.0)
#
# GITHUB_REPOSITORY (or GH_REPO) names the repository and GH_TOKEN the token.
#
# A release stays a draft until the packages built for it are published, and
# GitHub's endpoint that finds a release by its tag does not return drafts, so
# `gh release view|upload|edit <tag>` cannot be relied on. The release is found
# in the list instead, and everything else goes through its id.

REPO="${GH_REPO:-${GITHUB_REPOSITORY:?GITHUB_REPOSITORY or GH_REPO is required}}"

# The id of the (newest) release of a tag, draft or not; nothing when there is none.
release_id() {
  gh api "repos/$REPO/releases" --paginate \
    --jq ".[] | select(.tag_name == \"$1\") | .id" | head -1
}

release_body() { gh api "repos/$REPO/releases/$1" --jq '.body // ""'; }

# release_set_body ID FILE
release_set_body() { gh api -X PATCH "repos/$REPO/releases/$1" -F "body=@$2" > /dev/null; }

release_is_draft() { [ "$(gh api "repos/$REPO/releases/$1" --jq .draft)" = true ]; }

release_publish() { gh api -X PATCH "repos/$REPO/releases/$1" -F draft=false > /dev/null; }

release_asset_names() { gh api "repos/$REPO/releases/$1" --jq '.assets[].name'; }

# release_attach ID FILE NAME: the asset of that name is replaced if there is one.
release_attach() {
  local id="$1" file="$2" name="$3" existing
  existing=$(gh api "repos/$REPO/releases/$id" --jq ".assets[] | select(.name == \"$name\") | .id")
  for asset in $existing; do
    gh api -X DELETE "repos/$REPO/releases/assets/$asset" > /dev/null
  done
  gh api -X POST "https://uploads.github.com/repos/$REPO/releases/$id/assets?name=$name" \
    -H "Content-Type: application/octet-stream" --input "$file" > /dev/null
}
