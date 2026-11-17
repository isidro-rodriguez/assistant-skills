#!/usr/bin/env python3
"""Create Python projects from acodo-template and keep their AGENTS.md shared rules in sync.

Subcommands:
  new NAME --dest DIR   Copy the template, rename the package and project, reset version
                        and CHANGELOG, write AGENTS.md (+ CLAUDE.md importing it), git init
                        and uv lock.
  sync DIR              Replace the shared block (between <!-- shared:start --> and
                        <!-- shared:end -->) in DIR/AGENTS.md with the current one.
  check DIR             Exit 1 if DIR/AGENTS.md is missing the shared block or it has drifted.

Options for `new`: --description, --python (default 3.13), --template (git URL or local path;
default the public acodo-template), --no-git, --no-lock.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
TEMPLATE_URL = "https://github.com/isidro-rodriguez/acodo-template"
TEMPLATE_PKG, TEMPLATE_NAME = "acodo_template", "acodo-template"
SHARED_RE = re.compile(r"<!-- shared:start.*?<!-- shared:end -->\n?", re.S)
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
TEXT_SUFFIXES = {".py", ".toml", ".md", ".yaml", ".yml", ".txt", ".cfg", ".ini", ""}

CHANGELOG = """# Changelog

Todos los cambios relevantes de `{name}` se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Added

- Estructura inicial del proyecto a partir de `acodo-template`.
"""


class ScaffoldError(Exception):
    pass


def shared_block() -> str:
    return (ASSETS / "AGENTS.shared.md").read_text(encoding="utf-8")


def render_agents(name: str, description: str, package: str, python: str) -> str:
    text = (ASSETS / "AGENTS.project.md").read_text(encoding="utf-8")
    for key, val in {"{shared}": shared_block().rstrip("\n"), "{name}": name,
                     "{description}": description, "{package}": package, "{python}": python}.items():
        text = text.replace(key, val)
    return text


def _fetch_template(src: str, dest: Path) -> None:
    if Path(src).is_dir():
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        return
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", src, f"{tmp}/t"],
                           capture_output=True, text=True)
        if r.returncode:
            raise ScaffoldError(f"git clone {src} failed: {r.stderr.strip()}")
        shutil.copytree(f"{tmp}/t", dest, ignore=shutil.ignore_patterns(".git"))


def _replace_everywhere(root: Path, pairs: list[tuple[str, str]]) -> None:
    for f in root.rglob("*"):
        if not f.is_file() or f.suffix not in TEXT_SUFFIXES or f.name == "uv.lock":
            continue
        text = f.read_text(encoding="utf-8")
        new = text
        for a, b in pairs:
            new = new.replace(a, b)
        if new != text:
            f.write_text(new, encoding="utf-8")


def cmd_new(args) -> int:
    name = args.name
    if not NAME_RE.match(name):
        raise ScaffoldError("NAME must be lowercase kebab-case (e.g. mi-cli).")
    package = name.replace("-", "_")
    dest = Path(args.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise ScaffoldError(f"{dest} exists and is not empty.")
    _fetch_template(args.template, dest)

    (dest / "src" / TEMPLATE_PKG).rename(dest / "src" / package)
    _replace_everywhere(dest, [
        (f"https://github.com/isidro-rodriguez/{TEMPLATE_NAME}", f"https://github.com/isidro-rodriguez/{name}"),
        (TEMPLATE_PKG, package), (TEMPLATE_NAME, name),
    ])

    py = dest / "pyproject.toml"
    text = py.read_text(encoding="utf-8")
    text = re.sub(r'^version = ".*"$', 'version = "0.1.0"', text, count=1, flags=re.M)
    text = re.sub(r'^description = ".*"$', f'description = "{args.description}"', text, count=1, flags=re.M)
    # Console script named after the project instead of the template's generic `main`.
    text = re.sub(r'^main = "(\w+)\.main:main"$', rf'{name} = "\1.main:main"', text, count=1, flags=re.M)
    py.write_text(text, encoding="utf-8")

    (dest / "CHANGELOG.md").write_text(CHANGELOG.format(name=name), encoding="utf-8")
    (dest / "AGENTS.md").write_text(
        render_agents(name, args.description, package, args.python), encoding="utf-8")
    shutil.copy(ASSETS / "CLAUDE.md", dest / "CLAUDE.md")
    readme = dest / "README.md"
    rtext = readme.read_text(encoding="utf-8")
    rtext = re.sub(r"^# .*$", f"# {name}\n\n{args.description}", rtext, count=1, flags=re.M)
    rtext = rtext.replace("uv run main ", f"uv run {name} ")
    rtext = re.sub(r"^Renombra el paquete.*\n\n?", "", rtext, flags=re.M)
    readme.write_text(rtext, encoding="utf-8")

    notes = []
    if not args.no_lock:
        if shutil.which("uv"):
            r = subprocess.run(["uv", "lock"], cwd=dest, capture_output=True, text=True)
            notes.append("uv.lock regenerated" if r.returncode == 0 else f"uv lock failed: {r.stderr.strip()[-300:]}")
        else:
            notes.append("uv not found: run `uv lock` before the first commit")
    if not args.no_git and shutil.which("git"):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=dest, check=True)
        notes.append("git initialised (nothing committed)")
    print(f"Created {name} in {dest} (package {package}, version 0.1.0). " + "; ".join(notes) + ".")
    print("Next: uv sync && poe check (or the uv run commands), then review AGENTS.md › Project rules.")
    return 0


def cmd_sync(args) -> int:
    f = Path(args.dir) / "AGENTS.md"
    if not f.exists():
        raise ScaffoldError(f"{f} not found. Migrate the project's CLAUDE.md first (see SKILL.md).")
    text = f.read_text(encoding="utf-8")
    if not SHARED_RE.search(text):
        raise ScaffoldError("AGENTS.md has no shared block markers; add them by migrating (see SKILL.md).")
    new = SHARED_RE.sub(lambda _: shared_block(), text, count=1)
    if new == text:
        print("Shared block already up to date.")
        return 0
    f.write_text(new, encoding="utf-8")
    print(f"Updated the shared block in {f}.")
    return 0


def cmd_check(args) -> int:
    f = Path(args.dir) / "AGENTS.md"
    if not f.exists():
        print(f"FAIL: {f} not found.", file=sys.stderr)
        return 1
    m = SHARED_RE.search(f.read_text(encoding="utf-8"))
    if not m:
        print("FAIL: AGENTS.md has no shared block.", file=sys.stderr)
        return 1
    if m.group(0).rstrip() != shared_block().rstrip():
        print("FAIL: shared block has drifted; run `scaffold.py sync`.", file=sys.stderr)
        return 1
    claude = Path(args.dir) / "CLAUDE.md"
    if claude.exists() and "@AGENTS.md" not in claude.read_text(encoding="utf-8"):
        print("WARN: CLAUDE.md does not import AGENTS.md (`@AGENTS.md`).")
    print("OK: shared block up to date.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("name")
    n.add_argument("--dest", required=True)
    n.add_argument("--description", default="Proyecto Python.")
    n.add_argument("--python", default="3.13")
    n.add_argument("--template", default=TEMPLATE_URL)
    n.add_argument("--no-git", action="store_true")
    n.add_argument("--no-lock", action="store_true")
    for c in ("sync", "check"):
        sub.add_parser(c).add_argument("dir")
    args = ap.parse_args()
    try:
        return {"new": cmd_new, "sync": cmd_sync, "check": cmd_check}[args.cmd](args)
    except ScaffoldError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
