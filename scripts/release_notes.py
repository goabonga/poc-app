#!/usr/bin/env python3

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Chris <goabonga@pm.me>

"""Document a released package in the notes of its GitHub Release.

Two commands, run by package-build.yml and package-published.yml:

    release_notes.py notes KIND COMPONENT VERSION URL [--package NAME] \\
        [--ppa PPA] [--results JSON] [--issues JSON] [--archive NAME] \\
        < notes.md > new-notes.md
    release_notes.py assets PACKAGE VERSION DEBS_JSON

``notes`` reads the current release notes on stdin and writes them back with
one section for the package, how to install it and where it comes from.
Nothing about the PPA is written down here: its signing key, its series and
its pages come from the public Launchpad API, and the package and PPA names
from the dispatch poc-apt and poc-aur send. The section sits between two
markers, so a rerun replaces it instead of piling up a second copy, and the
notes around it are left alone.

``assets`` prints, for the ``.deb`` files Launchpad built, the name each is
attached to the release under, its URL and its SHA-256, tab separated.
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
    # Launchpad's API is behind a cache that keeps an answer, an empty one
    # included, for a long time.
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
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


def asset_name(package: str, version: str, deb: dict[str, str]) -> str:
    """The name a built .deb is attached to the release under.

    Launchpad's own file names carry a revision and a ``~series`` that GitHub
    rewrites; this one says what the file is.
    """
    return f"{package}_{version}_{deb['series']}_{deb['arch']}.deb"


def parse_debs(text: str) -> list[dict[str, str]]:
    """The .deb files poc-apt reports: ``[{series, arch, url, sha256}, ...]``."""
    try:
        debs = json.loads(text) if text.strip() else []
    except ValueError:
        return []
    return [deb for deb in debs if isinstance(deb, dict) and {"series", "arch", "url"} <= deb.keys()]


BUILT = "Successfully built"


def parse_results(text: str) -> list[dict[str, Any]]:
    """What poc-apt reports for each series: ``{series, version, state, published, builds}``."""
    try:
        results = json.loads(text) if text.strip() else []
    except ValueError:
        return []
    return [
        result
        for result in results
        if isinstance(result, dict) and "series" in result and isinstance(result.get("builds", []), list)
    ]


def parse_issues(text: str) -> dict[str, int]:
    """The issues opened for failed builds, ``{"<series>/<arch>": number}``."""
    try:
        issues = json.loads(text) if text.strip() else {}
    except ValueError:
        return {}
    return {key: number for key, number in issues.items() if isinstance(number, int)} if isinstance(issues, dict) else {}


def built_archs(result: dict[str, Any]) -> list[str]:
    """The architectures a series was built for, whatever happened to the build."""
    return [build["arch"] for build in result.get("builds", []) if "arch" in build]


def arch_outcome(result: dict[str, Any], build: dict[str, Any], issues: dict[str, int]) -> str:
    """How a build ended, for the table of the notes."""
    if build.get("state") != BUILT:
        issue = issues.get(f"{result['series']}/{build.get('arch', '')}")
        return f"{build.get('arch', '?')} ❌ failed" + (f" (#{issue})" if issue else "")
    if not result.get("published"):
        return f"{build['arch']} ⚠️ built, not published yet"
    return f"{build['arch']} ✅"


def series_row(result: dict[str, Any], issues: dict[str, int]) -> str:
    series = result["series"]
    builds = result.get("builds", [])
    if not builds:
        # Nothing was built at all: not uploaded, rejected or never built.
        issue = issues.get(f"{series}/*")
        return f"| {series} | ❌ not built ({result.get('state', 'unknown')})" + (f" (#{issue})" if issue else "") + " |"
    return f"| {series} | " + ", ".join(arch_outcome(result, build, issues) for build in builds) + " |"


def attached_names(package: str, version: str, results: list[dict[str, Any]]) -> list[str]:
    """The names of the .deb files attached to the release: the builds that succeeded."""
    return [
        asset_name(package, version, {"series": result["series"], "arch": build["arch"]})
        for result in results
        for build in result.get("builds", [])
        if build.get("state") == BUILT
    ]


def apt_section(
    package: str,
    version: str,
    details: dict[str, str] | None,
    results: list[dict[str, Any]],
    issues: dict[str, int] | None = None,
) -> str:
    issues = issues or {}
    published = [result["series"] for result in results if result.get("published")]
    table = ""
    if results:
        rows = "\n".join(series_row(result, issues) for result in results)
        table = f"""### Build results

| Series | Architectures |
| --- | --- |
{rows}"""
    names = attached_names(package, version, results)
    files = ""
    if names:
        listed = "\n".join(f"- `{name}`" for name in names)
        files = f"""The packages Launchpad built are also attached to this release, one per
series and architecture, to install without adding the archive:

{listed}

```bash
sudo apt install ./{names[0]}
```"""
    if details is None or not published:
        intro = "## Install with apt"
        if details is not None and not published:
            intro += "\n\nNo series is published in the archive yet."
        return "\n\n".join(part for part in (intro, table, files) if part)
    series_list = ", ".join(published)
    by_hand = f"""To add the archive by hand instead, put these lines in your software sources,
with `<series>` one of {series_list}:

```
deb {details["sources_url"]} <series> main
deb-src {details["sources_url"]} <series> main
```"""
    key = ""
    if details["fingerprint"]:
        key = f"The archive is signed with the key `{details['fingerprint']}`."
    install = f"""The package is built by Launchpad for {details['distribution'].capitalize()} and published in a personal
package archive (PPA). The packages in it are unsupported and the archive is
untrusted, so add it only if you trust its owner.

```bash
sudo add-apt-repository {details["ppa"]}
sudo apt update
sudo apt install {package}
```"""
    page = f"Builds and their logs: [{details['ppa']}]({details['page_url']})."
    return "\n\n".join(
        part for part in ("## Install with apt", install, by_hand, key, table, files, page) if part
    )


def aur_archive_name(package: str, version: str) -> str:
    """The name the archive of the AUR package is attached to the release under."""
    return f"{package}_{version}_aur.tar.gz"


def aur_section(package: str, url: str, archive: str = "") -> str:
    attached = (
        f"\n\nThe recipe as the AUR serves it, the `PKGBUILD` and its `.SRCINFO`, is attached\n"
        f"to this release: `{archive}`."
        if archive
        else ""
    )
    if not url.startswith(f"{AUR}/"):
        return f"""## Arch Linux package

The package recipe was prepared, but it was not pushed to the AUR (no deploy
key is configured), so it cannot be installed with an AUR helper yet. The
recipe is available at {url}.{attached}"""
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

Package page: [{package}]({url}).{attached}"""


def section(
    kind: str,
    package: str,
    version: str,
    url: str,
    details: dict[str, str] | None = None,
    results: list[dict[str, Any]] | None = None,
    issues: dict[str, int] | None = None,
    archive: str = "",
) -> str:
    if kind == "apt":
        return apt_section(package, version, details, results or [], issues)
    if kind == "aur":
        return aur_section(package, url, archive)
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
    commands = parser.add_subparsers(dest="command", required=True)
    notes = commands.add_parser("notes", help="write the package section into the release notes")
    notes.add_argument("kind", choices=["apt", "aur"])
    notes.add_argument("component")
    notes.add_argument("version")
    notes.add_argument("url")
    notes.add_argument("--package", default="", help="the name of the package")
    notes.add_argument("--ppa", default="", help="the PPA, as ppa:<owner>/<name> (apt only)")
    notes.add_argument("--results", default="", help="what happened to each series, as JSON (apt only)")
    notes.add_argument("--issues", default="", help="the issues of failed builds, as JSON (apt only)")
    notes.add_argument("--archive", default="", help="the name of the AUR archive attached to the release (aur only)")
    assets = commands.add_parser("assets", help="list the .deb files to attach")
    assets.add_argument("package")
    assets.add_argument("version")
    assets.add_argument("debs")
    args = parser.parse_args(argv)
    if args.command == "assets":
        for deb in parse_debs(args.debs):
            print(f"{asset_name(args.package, args.version, deb)}\t{deb['url']}\t{deb.get('sha256', '')}")
        return 0
    # Older dispatches do not carry the package name: poc-<component> is
    # what poc-apt and poc-aur have always called it.
    package = args.package or f"poc-{args.component}"
    details = ppa_details(args.ppa, package) if args.kind == "apt" and args.ppa else None
    text = section(
        args.kind,
        package,
        args.version,
        args.url,
        details,
        parse_results(args.results),
        parse_issues(args.issues),
        args.archive,
    )
    sys.stdout.write(upsert(sys.stdin.read(), args.kind, text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
