#!/usr/bin/env python3

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

"""Open an issue for each package Launchpad failed to build.

Run by package-complete.yml with what poc-apt reports for each series:

    package_issues.py COMPONENT PACKAGE VERSION RUN_URL RESULTS_JSON

One bug issue is opened per series and architecture whose build did not
succeed, and one for a series that was not built at all (not uploaded, rejected
by Launchpad, never built). Each follows the sections of the bug report
template, with the end of the build log. An issue for the same package,
version, series and architecture is not opened twice: a rerun finds the one
that is there. Prints, as JSON, the number of the issue of each failure,

    {"<series>/<arch>": 12, "<series>/*": 13}

for the notes of the release to link them. ``gh`` has to be authenticated.
"""

import gzip
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

BUILT = "Successfully built"
LOG_LINES = 80
LOG_CHARS = 20_000
# What a failure looks like in a build log, and how far from the end to look for it:
# the last lines of a build log are mostly the cleanup of the chroot.
ERROR = re.compile(r"(^|[\s:])(error|fatal|panic|failed)\b|\*\*\*|^E: ", re.IGNORECASE)
ERROR_WINDOW = 600
ERROR_CONTEXT = 12
# Only Launchpad's own hosts are asked for a log: the URL comes from a payload.
LOG_HOSTS = ("https://launchpad.net/", "https://launchpadlibrarian.net/")


def failures(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """The builds that did not succeed, and the series that have none."""
    found: list[dict[str, str]] = []
    for result in results:
        series = result["series"]
        builds = result.get("builds", [])
        if not builds:
            found.append(
                {
                    "key": f"{series}/*",
                    "series": series,
                    "arch": "*",
                    "state": result.get("state", "unknown"),
                    "url": "",
                    "log_url": "",
                }
            )
        for build in builds:
            if build.get("state") != BUILT:
                found.append(
                    {
                        "key": f"{series}/{build.get('arch', '?')}",
                        "series": series,
                        "arch": build.get("arch", "?"),
                        "state": build.get("state", "unknown"),
                        "url": build.get("url", ""),
                        "log_url": build.get("log_url", ""),
                    }
                )
    return found


def title(package: str, version: str, failure: dict[str, str]) -> str:
    if failure["arch"] == "*":
        return f"{package} {version} was not built for {failure['series']}"
    return f"{package} {version} fails to build on {failure['series']}/{failure['arch']}"


def log_tail(url: str) -> str:
    """The end of a build log, or why there is none."""
    if not url.startswith(LOG_HOSTS):
        return "No build log."
    try:
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            data = response.read()
    except (urllib.error.URLError, OSError) as error:
        return f"The build log could not be fetched: {error}"
    try:
        data = gzip.decompress(data)
    except OSError:
        pass
    return excerpt(data.decode("utf-8", "replace").splitlines())


def excerpt(lines: list[str]) -> str:
    """The lines around the first error of the end of a log, then its last lines."""
    recent = lines[-ERROR_WINDOW:]
    hit = next((index for index, line in enumerate(recent) if ERROR.search(line)), None)
    end = "\n".join(lines[-LOG_LINES:])
    if hit is None:
        return end[-LOG_CHARS:]
    around = "\n".join(recent[max(0, hit - ERROR_CONTEXT) : hit + ERROR_CONTEXT])
    return f"[around the first error]\n{around}\n\n[end of the log]\n{end}"[-LOG_CHARS:]


def body(component: str, package: str, version: str, run_url: str, failure: dict[str, str], tail: str) -> str:
    """The issue, in the sections of the bug report template."""
    where = (
        f"`{failure['series']}`"
        if failure["arch"] == "*"
        else f"`{failure['series']}` on `{failure['arch']}`"
    )
    page = f"\n\nBuild page: {failure['url']}" if failure["url"] else ""
    return f"""### Binary

{component}

### Version

{version} (package `{package}`)

### Description

Launchpad did not build `{package}` {version} for {where}: {failure["state"]}.{page}

Workflow run: {run_url}

### Steps to Reproduce

The source package of this series was uploaded to the PPA by the `publish` workflow of poc-apt, which then followed its builds.

### Expected Behavior

The package builds and is published in the PPA.

### Actual Behavior

The build ended in the state `{failure["state"]}`.

### Operating System

Linux

### Logs / Output

```shell
{tail}
```
"""


def run(*args: str, **kwargs: Any) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs).stdout


def existing(issue_title: str) -> int | None:
    """The issue already opened with that exact title, whatever its state."""
    found = json.loads(
        run("gh", "issue", "list", "--state", "all", "--search", f'"{issue_title}" in:title',
            "--json", "number,title", "--limit", "20")
    )
    return next((issue["number"] for issue in found if issue["title"] == issue_title), None)


def create(issue_title: str, issue_body: str) -> int:
    url = run("gh", "issue", "create", "--title", issue_title, "--body-file", "-",
              "--label", "bug", input=issue_body).strip()
    return int(url.rsplit("/", 1)[-1])


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("usage: package_issues.py COMPONENT PACKAGE VERSION RUN_URL RESULTS_JSON", file=sys.stderr)
        return 2
    component, package, version, run_url, results_json = argv
    issues: dict[str, int] = {}
    for failure in failures(json.loads(results_json or "[]")):
        issue_title = title(package, version, failure)
        number = existing(issue_title)
        if number is None:
            tail = log_tail(failure["log_url"]) if failure["log_url"] else "No build log."
            number = create(issue_title, body(component, package, version, run_url, failure, tail))
        issues[failure["key"]] = number
    print(json.dumps(issues))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
