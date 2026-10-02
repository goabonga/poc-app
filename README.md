# poc-app

[![CI](https://github.com/goabonga/poc-app/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/goabonga/poc-app/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/goabonga/poc-app/blob/main/LICENSE)

Two independently-versioned Go command-line tools, released by multicz.

## Binaries

| Binary | Role |
| --- | --- |
| [`greeter`](cmd/greeter) | Prints a greeting for the name given as its first argument. |
| [`pinger`](cmd/pinger) | Reports the TCP connect latency to a `host:port` address. |

## Requirements

- Go (version pinned in [`go.mod`](go.mod))

## Getting started (development)

```bash
git clone https://github.com/goabonga/poc-app.git
cd poc-app
go build ./...
go vet ./...
go test ./...
```

## Versioning and release

`greeter` and `pinger` are versioned independently by
[multicz](https://github.com/goabonga/multicz), driven by
[Conventional Commits](https://www.conventionalcommits.org/). Each
component's `paths` in [`multicz.toml`](multicz.toml) is a curated
`cmd/<name>/**` glob; `multicz-go-deps-plugin`'s `[plugins.go-deps]` gives
it a second chance via the compiler-verified import graph (`go list -deps`)
when a change lands in an `internal/` package the glob doesn't name. On
every push to `main`, CI computes the bump, writes each component's
changelog, tags it, and publishes a GitHub Release. Maintainers do not bump
versions or edit a changelog by hand.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, the commit-message
convention, and the test/lint expectations. By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

Security issues: please follow the disclosure process in
[SECURITY.md](SECURITY.md).

## License

Distributed under the [MIT License](LICENSE).
