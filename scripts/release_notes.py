#!/usr/bin/env python3

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

"""Document a released package in the notes of its GitHub Release.

Run by package-published.yml once poc-apt or poc-aur reported a package:

    release_notes.py KIND COMPONENT VERSION URL [--package NAME] [--ppa PPA] \\
        < notes.md > new-notes.md

reads the current release notes on stdin and writes them back with one
section for the package, how to install it and where it comes from. Nothing
about the PPA is written down here: its signing key, its series and its
pages come from the public Launchpad API, and the package and PPA names from
the dispatch poc-apt and poc-aur send. The section sits between two markers,
so a rerun replaces it instead of piling up a second copy, and the notes
around it are left alone.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

LAUNCHPAD_API = "https://api.launchpad.net/1.0"
AUR = "https://aur.archlinux.org"


def markers(kind: str) -> tuple[str, str]:
    return f"<!-- package:{kind} -->", f"<!-- /package:{kind} -->"


def fetch(url: str, params: dict[str, str] | None = None) -> Any:
    """The JSON a public Launchpad API URL returns."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
        return json.load(response)


def ppa_details(ppa: str, package: str) -> dict[str, str] | None:
    """What Launchpad says about a PPA and the series ``package`` is built for.

    ``ppa`` is ``ppa:<owner>/<name>``. Returns ``None`` when Launchpad cannot
    be reached or does not know the PPA, so the release notes still get the
    parts that do not depend on it.
    """
    if not ppa.startswith("ppa:") or "/" not in ppa:
        return None
    owner, name = ppa.removeprefix("ppa:").split("/", 1)
    archive_api = f"{LAUNCHPAD_API}/~{owner}/+archive/ubuntu/{name}"
    try:
        archive = fetch(archive_api)
        sources = fetch(
            archive_api,
            {
                "ws.op": "getPublishedSources",
                "source_name": package,
                "exact_match": "true",
                "order_by_date": "true",
            },
        )
    except (urllib.error.URLError, ValueError, OSError):
        return None
    distribution = archive["distribution_link"].rsplit("/", 1)[-1]
    entries = sources.get("entries") or []
    series = entries[0]["distro_series_link"].rsplit("/", 1)[-1] if entries else ""
    return {
        "ppa": ppa,
        "distribution": distribution,
        "series": series,
        "fingerprint": archive.get("signing_key_fingerprint") or "",
        "sources_url": f"https://ppa.launchpadcontent.net/{owner}/{name}/{distribution}",
        "page_url": f"https://launchpad.net/~{owner}/+archive/{distribution}/{name}/+packages",
    }


def apt_section(package: str, version: str, details: dict[str, str] | None) -> str:
    deb = f"""The `.deb` built for this version is also attached to this release:

```bash
sudo apt install ./{package}_{version}_amd64.deb
```"""
    if details is None:
        return f"## Install with apt\n\n{deb}"
    series = details["series"]
    by_hand = ""
    if series:
        by_hand = f"""

To add the archive by hand instead, put these lines in your software sources:

```
deb {details["sources_url"]} {series} main
deb-src {details["sources_url"]} {series} main
```"""
    key = ""
    if details["fingerprint"]:
        key = f"\n\nThe archive is signed with the key `{details['fingerprint']}`."
    target = f" for {details['distribution'].capitalize()} `{series}`" if series else ""
    return f"""## Install with apt

The package is built by Launchpad{target} and published in a personal
package archive (PPA). The packages in it are unsupported and the archive is
untrusted, so add it only if you trust its owner.

```bash
sudo add-apt-repository {details["ppa"]}
sudo apt update
sudo apt install {package}
```{by_hand}{key}

{deb}

Builds and their logs: [{details["ppa"]}]({details["page_url"]})."""


def aur_section(package: str, url: str) -> str:
    if not url.startswith(f"{AUR}/"):
        return f"""## Arch Linux package

The package was built, but it was not pushed to the AUR (no deploy key is
configured), so it cannot be installed with an AUR helper yet. The built
package is available at {url}."""
    return f"""## Install from the AUR

For Arch Linux and its derivatives. The package is a recipe (a `PKGBUILD`) on
the Arch User Repository: it downloads the sources of this release and builds
them on your machine. Use an AUR helper:

```bash
yay -S {package}
```

or build it by hand:

```bash
git clone {AUR}/{package}.git
cd {package}
makepkg -si
```

Package page: [{package}]({url})."""


def section(
    kind: str, package: str, version: str, url: str, details: dict[str, str] | None = None
) -> str:
    if kind == "apt":
        return apt_section(package, version, details)
    if kind == "aur":
        return aur_section(package, url)
    raise ValueError(f"unknown package kind: {kind!r}")


def upsert(notes: str, kind: str, text: str) -> str:
    """The notes with the section of ``kind`` set to ``text``."""
    start, end = markers(kind)
    block = f"{start}\n{text}\n{end}"
    if start in notes and end in notes:
        head, rest = notes.split(start, 1)
        tail = rest.split(end, 1)[1]
        return f"{head}{block}{tail}"
    return f"{notes.rstrip()}\n\n{block}\n" if notes.strip() else f"{block}\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["apt", "aur"])
    parser.add_argument("component")
    parser.add_argument("version")
    parser.add_argument("url")
    parser.add_argument("--package", default="", help="the name of the package")
    parser.add_argument("--ppa", default="", help="the PPA, as ppa:<owner>/<name> (apt only)")
    args = parser.parse_args(argv)
    # Older dispatches do not carry the package name: poc-<component> is
    # what poc-apt and poc-aur have always called it.
    package = args.package or f"poc-{args.component}"
    details = ppa_details(args.ppa, package) if args.kind == "apt" and args.ppa else None
    text = section(args.kind, package, args.version, args.url, details)
    sys.stdout.write(upsert(sys.stdin.read(), args.kind, text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
