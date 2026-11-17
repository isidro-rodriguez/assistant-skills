#!/usr/bin/env python3
"""Deterministic release steps for uv-based Python projects.

Subcommands:
  status            Version, where it lives, CHANGELOG state, commits since the
                    last tag (with a suggested SemVer bump) and lockfile sync.
  check             Validate before a push: CHANGELOG format, top release ==
                    project version, release has entries, uv.lock in sync.
  bump LEVEL|X.Y.Z  Set the new version (major/minor/patch or explicit), promote
                    "## [Unreleased]" to "## [X.Y.Z] - YYYY-MM-DD" and re-lock.
  init              Start versioning an unversioned project: CHANGELOG.md
                    skeleton and version 0.1.0 (only when the user asks).

Global options: --project DIR (member directory in a workspace; default ".").
Exit code 1 on any problem, with the reason on stderr. Never commits, tags or
pushes: those are left to the agent and the user.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    sys.exit("release.py needs Python 3.11+ (tomllib).")

# SemVer 2.0: X.Y.Z with optional pre-release (-beta.3) and build metadata (+abc).
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
RELEASE_H = re.compile(r"^## \[(?P<v>[^\]]+)\](?: - (?P<d>\d{4}-\d{2}-\d{2}))?\s*$", re.M)
SECTIONS = {
    # Keep a Changelog names, English and the Spanish variants already in use.
    "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security",
    "Añadido", "Cambiado", "Obsoleto", "Eliminado", "Corregido", "Seguridad", "Interno",
}
CHANGELOG_SKELETON = """# Changelog

Todos los cambios relevantes de `{name}` se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]
"""


class ReleaseError(Exception):
    pass


# --------------------------------------------------------------------------
# Version source
# --------------------------------------------------------------------------

def _project_table_span(text: str) -> tuple[int, int]:
    m = re.search(r"^\[project\]\s*$", text, re.M)
    if not m:
        raise ReleaseError("pyproject.toml has no [project] table.")
    nxt = re.search(r"^\[", text[m.end():], re.M)
    return m.end(), m.end() + nxt.start() if nxt else len(text)


def version_source(root: Path) -> tuple[Path, str]:
    """Return (file, current_version). Supports static [project].version and
    dynamic versions read from a file ([tool.hatch.version] path)."""
    py = root / "pyproject.toml"
    if not py.exists():
        raise ReleaseError(f"No pyproject.toml in {root}.")
    data = tomllib.loads(py.read_text(encoding="utf-8"))
    project = data.get("project", {})
    if "version" in project:
        return py, str(project["version"])
    if "version" in project.get("dynamic", []):
        path = data.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
        if not path:
            raise ReleaseError("Dynamic version without [tool.hatch.version] path; set it by hand.")
        f = root / path
        m = re.search(r"""^(?:__version__|version)\s*(?::\s*str)?\s*=\s*["']([^"']+)["']""",
                      f.read_text(encoding="utf-8"), re.M)
        if not m:
            raise ReleaseError(f"No version assignment found in {path}.")
        return f, m.group(1)
    raise ReleaseError("pyproject.toml declares no version.")


def write_version(root: Path, new: str) -> Path:
    f, old = version_source(root)
    text = f.read_text(encoding="utf-8")
    if f.name == "pyproject.toml":
        a, b = _project_table_span(text)
        block, n = re.subn(r'^(version\s*=\s*)["\'][^"\']*["\']', rf'\g<1>"{new}"', text[a:b],
                           count=1, flags=re.M)
        text = text[:a] + block + text[b:]
    else:
        text, n = re.subn(r"""^((?:__version__|version)\s*(?::\s*str)?\s*=\s*)["'][^"']*["']""",
                          rf'\g<1>"{new}"', text, count=1, flags=re.M)
    if n != 1:
        raise ReleaseError(f"Could not rewrite the version in {f}.")
    f.write_text(text, encoding="utf-8")
    return f


def next_version(current: str, level: str) -> str:
    if SEMVER.match(level):
        return level
    m = SEMVER.match(current)
    if not m:
        raise ReleaseError(f"Current version {current!r} is not X.Y.Z.")
    major, minor, patch = (int(x) for x in m.groups()[:3])
    if m.group(4) and level == "patch":
        return f"{major}.{minor}.{patch}"   # 1.2.0-beta.3 + patch -> 1.2.0 (final release)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ReleaseError(f"Unknown level {level!r} (major, minor, patch or X.Y.Z).")


def _key(v: str) -> tuple:
    """SemVer precedence: core numbers, then a release ranks above its pre-releases,
    then pre-release identifiers (numeric < alphanumeric)."""
    m = SEMVER.match(v)
    core = tuple(int(x) for x in m.groups()[:3])
    pre = m.group(4)
    if pre is None:
        return core + ((1,),)
    ids = tuple((0, int(x), "") if x.isdigit() else (1, 0, x) for x in pre.split("."))
    return core + ((0,) + ids,)


# --------------------------------------------------------------------------
# CHANGELOG
# --------------------------------------------------------------------------

def parse_changelog(text: str) -> list[dict]:
    heads = list(RELEASE_H.finditer(text))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.end():end]
        out.append({"version": h.group("v"), "date": h.group("d"), "start": h.start(),
                    "body": body, "sections": re.findall(r"^### (.+?)\s*$", body, re.M),
                    "entries": len(re.findall(r"^\s*[-*] ", body, re.M))})
    return out


def changelog_problems(text: str, version: str) -> list[str]:
    probs = []
    rel = parse_changelog(text)
    if not rel:
        return ["CHANGELOG.md has no '## [X.Y.Z] - YYYY-MM-DD' or '## [Unreleased]' headings."]
    seen = []
    for r in rel:
        v = r["version"]
        if v == "Unreleased":
            if r is not rel[0]:
                probs.append("'## [Unreleased]' must be the first section.")
            continue
        if not SEMVER.match(v):
            probs.append(f"Release heading [{v}] is not SemVer (X.Y.Z or X.Y.Z-pre).")
            continue
        if not r["date"]:
            probs.append(f"Release [{v}] has no date ('## [{v}] - YYYY-MM-DD').")
        elif dt.date.fromisoformat(r["date"]) > dt.date.today():
            probs.append(f"Release [{v}] is dated in the future ({r['date']}).")
        if v in seen:
            probs.append(f"Release [{v}] appears twice.")
        seen.append(v)
        for s in r["sections"]:
            if s not in SECTIONS:
                probs.append(f"[{v}] uses unknown section '### {s}'.")
    if seen and [_key(v) for v in seen] != sorted((_key(v) for v in seen), reverse=True):
        probs.append("Releases are not in descending order.")
    if seen and seen[0] != version:
        probs.append(f"Top release in CHANGELOG is {seen[0]}, project version is {version}.")
    top = next((r for r in rel if r["version"] == version), None)
    if top is not None and top["entries"] == 0:
        probs.append(f"Release [{version}] has no entries.")
    return probs


def promote(text: str, new: str, today: str) -> str:
    rel = parse_changelog(text)
    unrel = next((r for r in rel if r["version"] == "Unreleased"), None)
    if any(r["version"] == new for r in rel):
        raise ReleaseError(f"CHANGELOG already has a [{new}] section.")
    if unrel is None or unrel["entries"] == 0:
        raise ReleaseError(
            "Nothing under '## [Unreleased]'. Write the entries first (Spanish, explain the why), "
            "grouped under ### Added / Changed / Fixed / Removed…")
    head = f"## [{new}] - {today}"
    # Keep an empty [Unreleased] on top for the next cycle.
    return text[:unrel["start"]] + f"## [Unreleased]\n\n{head}" + text[unrel["start"] + len("## [Unreleased]"):]


# --------------------------------------------------------------------------
# git / uv
# --------------------------------------------------------------------------

def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def git_info(root: Path) -> dict:
    if not shutil.which("git") or run(["git", "rev-parse"], root).returncode:
        return {"git": False}
    tag = run(["git", "describe", "--tags", "--abbrev=0"], root).stdout.strip() or None
    base, base_kind = tag, "tag"
    if not tag:
        # No tags (unpublished projects): start from the last release commit, i.e. the most
        # recent one that changed the version or added a dated CHANGELOG section.
        try:
            vfile, _ = version_source(root)
            paths = [str(vfile.relative_to(root))]
            if (root / "CHANGELOG.md").exists():
                paths.append("CHANGELOG.md")
            last = run(["git", "log", "-1", "--format=%h", "-G",
                        r"^((__version__|version)\s*(:\s*str)?\s*=|## \[[0-9])", "--", *paths],
                       root).stdout.strip()
            base, base_kind = (last or None), "last release commit"
        except ReleaseError:
            base = None
    rng = f"{base}..HEAD" if base else "HEAD"
    log = run(["git", "log", "--format=%s", rng, "--", "."], root).stdout.splitlines()
    dirty = bool(run(["git", "status", "--porcelain", "--", "."], root).stdout.strip())
    shallow = run(["git", "rev-parse", "--is-shallow-repository"], root).stdout.strip() == "true"
    return {"git": True, "last_tag": tag, "since": f"{base} ({base_kind})" if base else "beginning",
            "commits": log, "dirty": dirty, "shallow": shallow}


def suggest(commits: list[str]) -> tuple[str | None, dict]:
    kinds: dict[str, int] = {}
    breaking = False
    for c in commits:
        m = re.match(r"^(\w+)(?:\([^)]*\))?(!)?:", c)
        if not m:
            kinds["other"] = kinds.get("other", 0) + 1
            continue
        kinds[m.group(1)] = kinds.get(m.group(1), 0) + 1
        breaking |= bool(m.group(2)) or "BREAKING CHANGE" in c
    if breaking:
        return "major", kinds
    if kinds.get("feat"):
        return "minor", kinds
    if any(kinds.get(k) for k in ("fix", "perf", "refactor")):
        return "patch", kinds
    return None, kinds


def lock_state(root: Path) -> str:
    lock_root = next((p for p in [root, *root.parents] if (p / "uv.lock").exists()), None)
    if lock_root is None:
        return "no uv.lock"
    if not shutil.which("uv"):
        return "uv not installed (cannot verify)"
    r = run(["uv", "lock", "--check"], lock_root)
    return "in sync" if r.returncode == 0 else "OUT OF SYNC (run `uv lock`)"


def relock(root: Path) -> str:
    lock_root = next((p for p in [root, *root.parents] if (p / "uv.lock").exists()), None)
    if lock_root is None or not shutil.which("uv"):
        return "skipped (no uv.lock or uv)"
    r = run(["uv", "lock"], lock_root)
    if r.returncode:
        raise ReleaseError("uv lock failed:\n" + r.stderr[-1500:])
    return lock_state(root)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_status(root: Path, as_json: bool) -> int:
    info: dict = {"project": str(root)}
    try:
        f, v = version_source(root)
        info |= {"version": v, "version_file": str(f.relative_to(root))}
    except ReleaseError as e:
        info["version_error"] = str(e)
        v = None
    cl = root / "CHANGELOG.md"
    if cl.exists():
        rel = parse_changelog(cl.read_text(encoding="utf-8"))
        un = next((r for r in rel if r["version"] == "Unreleased"), None)
        info["changelog"] = {"top_release": next((r["version"] for r in rel if r["version"] != "Unreleased"), None),
                             "unreleased_entries": un["entries"] if un else None}
    else:
        info["changelog"] = None
    g = git_info(root)
    if g.get("git"):
        level, kinds = suggest(g["commits"])
        info["git"] = {"last_tag": g["last_tag"], "counted_since": g["since"],
                       "commits_since": len(g["commits"]), "commits": g["commits"][:15],
                       "commit_types": kinds, "suggested_bump": level,
                       "uncommitted_changes": g["dirty"], "shallow_clone": g["shallow"]}
    info["lock"] = lock_state(root)
    versioned = v not in (None, "0.0.0") and info["changelog"] is not None
    info["versioned_project"] = versioned
    if as_json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        for k, val in info.items():
            print(f"{k:18} {json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else val}")
        if not versioned:
            print("\nThis project is not versioned (version 0.0.0 or no CHANGELOG.md). "
                  "Don't bump; ask the user whether to start versioning (`init`).")
        if g.get("shallow"):
            print("\nShallow clone: commits since the last tag may be incomplete "
                  "(`git fetch --depth=200 --tags`).")
    return 0


def cmd_check(root: Path) -> int:
    probs = []
    try:
        _, v = version_source(root)
    except ReleaseError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    cl = root / "CHANGELOG.md"
    if not cl.exists():
        probs.append("CHANGELOG.md missing.")
    else:
        probs += changelog_problems(cl.read_text(encoding="utf-8"), v)
    lock = lock_state(root)
    if lock.startswith("OUT"):
        probs.append(f"uv.lock {lock}.")
    for p in probs:
        print(f"FAIL: {p}", file=sys.stderr)
    if not probs:
        print(f"OK: version {v}, CHANGELOG consistent, uv.lock {lock}.")
    return 1 if probs else 0


def cmd_bump(root: Path, level: str, today: str | None) -> int:
    _, cur = version_source(root)
    new = next_version(cur, level)
    if SEMVER.match(cur) and _key(new) <= _key(cur):
        raise ReleaseError(f"New version {new} is not greater than {cur}.")
    cl = root / "CHANGELOG.md"
    if not cl.exists():
        raise ReleaseError("CHANGELOG.md missing (use `init` if the user wants to start versioning).")
    date = today or dt.date.today().isoformat()
    text = promote(cl.read_text(encoding="utf-8"), new, date)
    f = write_version(root, new)          # only write once the CHANGELOG step is known to work
    cl.write_text(text, encoding="utf-8")
    lock = relock(root)
    probs = changelog_problems(text, new)
    print(f"Bumped {cur} -> {new} in {f.relative_to(root)}; CHANGELOG [{new}] - {date}; uv.lock {lock}.")
    for p in probs:
        print(f"FAIL: {p}", file=sys.stderr)
    print(f"Suggested commit: chore: bump versión a {new}")
    return 1 if probs else 0


def cmd_init(root: Path) -> int:
    py = root / "pyproject.toml"
    data = tomllib.loads(py.read_text(encoding="utf-8"))
    name = data.get("project", {}).get("name", root.name)
    cl = root / "CHANGELOG.md"
    if cl.exists():
        raise ReleaseError("CHANGELOG.md already exists.")
    cl.write_text(CHANGELOG_SKELETON.format(name=name), encoding="utf-8")
    _, cur = version_source(root)
    msg = f"Created CHANGELOG.md for {name}."
    if cur == "0.0.0":
        write_version(root, "0.1.0")
        msg += " Version 0.0.0 -> 0.1.0 (first release once [Unreleased] has entries)."
    print(msg)
    print("Next: add entries under [Unreleased], then `bump 0.1.0`-style or `bump minor`.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="project or workspace-member directory (default .)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--json", action="store_true")
    sub.add_parser("check")
    b = sub.add_parser("bump"); b.add_argument("level", help="major | minor | patch | X.Y.Z")
    b.add_argument("--date", help="release date YYYY-MM-DD (default today)")
    sub.add_parser("init")
    args = ap.parse_args()
    root = Path(args.project).resolve()
    try:
        if args.cmd == "status":
            return cmd_status(root, args.json)
        if args.cmd == "check":
            return cmd_check(root)
        if args.cmd == "bump":
            return cmd_bump(root, args.level, args.date)
        return cmd_init(root)
    except ReleaseError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
