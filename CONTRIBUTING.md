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
uv tool install multicz --with multicz-go-deps-plugin
multicz validate --strict
python3 scripts/add_license_header.py --path . --types go,sh,py,yml,yaml --check
uvx pytest scripts/tests --import-mode=importlib
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

## Releasing

Releases are automated: on every push to `main`, the `release` workflow runs
`multicz bump` (signed commit + tag, per affected component) and publishes a
GitHub Release. Maintainers do not bump versions or edit the changelog by
hand.

## Reporting bugs and asking for features

Please open a GitHub issue. For security-sensitive reports, follow
[SECURITY.md](SECURITY.md) instead of the public tracker.
