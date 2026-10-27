# Contributing to poc-app

Thanks for taking the time to contribute. This document is the short version
of how to propose a change and what the project expects in return.

## Code of Conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md). By contributing you agree to abide by
its terms.

## Development setup

```bash
git clone https://github.com/goabonga/poc-app.git
cd poc-app
go build ./...
go test ./...
```

## Quality gates

Before pushing, make sure your code passes the same gates the `ci` workflow
runs:

```bash
go vet ./...
go test ./...
go fmt ./...
uv tool install "multicz>=1.10" --with multicz-go-deps-plugin
multicz validate --strict
python3 scripts/add_license_header.py --path . --types go,sh,py,yml,yaml --check
```

The same gates run as git hooks once installed with
`pre-commit install` (it sets up the pre-commit and commit-msg hooks).

## Commit messages

Commit messages MUST follow
[Conventional Commits](https://www.conventionalcommits.org/). They drive the
version bump and CHANGELOG computed by
[multicz](https://github.com/goabonga/multicz).

| Type | Effect on version | Use it for |
| --- | --- | --- |
| `feat` | minor | new capability |
| `fix` | patch | bug fix |
| `perf` | patch | performance improvement |
| `refactor`, `docs`, `test`, `chore`, `ci`, `build`, `style` | none | maintenance |
| `feat!` / `BREAKING CHANGE:` | major | incompatible change |

Only commits that touch a component's tracked paths (`cmd/<name>/**`,
`go.mod`, `go.sum` — or any file its import graph reaches, per
`multicz-go-deps-plugin`) trigger that component's release. Do not append
`Co-Authored-By` trailers.

The subject is at most 72 characters, has no trailing period and a
lowercase first word after the colon: the signed merge refuses any other
subject, so the `commit-subject` pre-commit hook and the `commit-subjects`
CI job check it first.

## Branches and merging

A branch is named after the GitHub issue it addresses:

```
issue-<number>-<slug>
```

`<number>` is the issue number and `<slug>` a few lowercase words separated
by hyphens. Keep it free of `/`: Git cannot hold `issue-12` and
`issue-12/...` at the same time, and the automation only recognises
`issue-*` as a base branch. A sub-issue branch is created from, and
proposed to, the branch of its parent issue; the parent branch is proposed
to `main` once they are all merged. Dependabot branches (`dependabot/...`)
need no naming.

Adding the `auto-merge` label to a pull request, by someone with write
access, replays its commits GPG-signed onto its base branch once the
required checks passed, then fast-forwards that branch. The history stays
linear. The commits of a branch pushed unsigned, such as by GitHub's
"Update branch", are re-signed in place.

Dependabot pull requests are rewritten as Conventional Commits (`ci` for
workflow bumps, `fix(deps)` for Go modules) and signed. Each one also gets
an issue, assigned to the repository owner, which the pull request closes
when it is merged; if it is closed without a merge, the issue is closed as
not planned. Once CI passed on the rewritten head it is queued for the
signed merge, except major updates, which wait for a maintainer's label.

These workflows read the `AUTO_MERGE_PAT` and `GPG_PRIVATE_KEY` /
`GPG_PASSPHRASE` secrets and the `GIT_USER_NAME`, `GIT_USER_EMAIL` and
`GIT_SIGNING_KEY` variables of the repository.

## Releasing

Releases are automated: on every push to `main`, once the quality jobs
passed, the `release` job of the `ci` workflow runs `multicz bump` (signed
commit + tag, per affected component), the `publish` job builds the binaries
and opens a GitHub Release, and `trigger packaging` starts the poc-apt and
poc-aur pipelines. Maintainers do not bump versions or edit the changelog by
hand.

## Reporting bugs and asking for features

Please open a GitHub issue. For security-sensitive reports, follow
[SECURITY.md](SECURITY.md) instead of the public tracker.
