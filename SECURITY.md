# Security Policy

## Supported versions

Security fixes are applied only to the latest released version of each
binary (`greeter`, `pinger`) on the `main` branch.

| Version | Supported |
| --- | --- |
| latest release | ✅ |
| older releases | ❌ |

## Reporting a vulnerability

**Please do not open a public issue.** GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
is the preferred channel:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**.
3. Describe the issue with reproduction steps and a suggested mitigation.

If you cannot use GitHub's form, email **goabonga@pm.me** with the same
information. PGP encryption is available on request.

You can expect an acknowledgement within **3 business days**, a triage
assessment within **10 business days**, and a fix or written mitigation
plan before any public disclosure.

## Scope

`pinger` opens outbound TCP connections to an address given on its command
line; `greeter` only formats a string. Neither parses untrusted network
input or runs a subprocess. Vulnerabilities in the Go toolchain or standard
library should be reported upstream, but please let us know so the pinned
`go` directive can be bumped.

Thanks for helping keep the project and its users safe.
