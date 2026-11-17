#!/usr/bin/env python3
"""Create Python projects from acodo-template and keep their AGENTS.md shared rules in sync.

Subcommands:
  new NAME --dest DIR   Copy the template, rename the package, project and command, remove
                        <!-- template-only --> blocks, reset version and CHANGELOG, rebuild
                        AGENTS.md from the template's own Project rules with the current
                        shared block (+ CLAUDE.md importing it), git init and uv lock.
  sync DIR              Replace the shared block (between <!-- shared:start --> and
                        <!-- shared:end -->) in DIR/AGENTS.md with the current one.
  assemble DIR --rules FILE --name NAME --description TEXT
                        Write DIR/AGENTS.md as header + shared block + FILE (the project
                        rules, starting with "## Project rules") and DIR/CLAUDE.md as
                        "@AGENTS.md". Used by migrate, so the layout is always identical.
  check DIR             Exit 1 if DIR/AGENTS.md is missing the shared block or it has drifted.

Options for `new`: --description, --template (git URL or local path;
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
# Markers count only on a line of their own, so prose may quote them safely.
TEMPLATE_ONLY_RE = re.compile(
    r"^[ \t]*<!-- template-only:start -->[ \t]*\n.*?^[ \t]*<!-- template-only:end -->[ \t]*(?:\n|\Z)",
    re.S | re.M)
MARKER_LINE_RE = re.compile(r"^[ \t]*<!-- template-only:(?:start|end) -->[ \t]*$", re.M)
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


HEADER = """# AGENTS.md

Instructions for AI agents working on **{name}**: {description}

The shared sections below are the same in every project. Project-specific rules are at the
end, under **Project rules**, and take precedence when they differ.

"""


def compose(name: str, description: str, project_rules: str) -> str:
    """Header + shared block + project rules, with one blank line between parts."""
    rules = project_rules.strip("\n")
    if not rules.startswith("## Project rules"):
        raise ScaffoldError("Project rules must start with a '## Project rules' heading.")
    return (HEADER.replace("{name}", name).replace("{description}", description.strip())
            + shared_block().rstrip("\n") + "\n\n" + rules + "\n")


def strip_template_only(text: str) -> str:
    """Remove <!-- template-only --> blocks and the blank-line runs they leave behind."""
    return re.sub(r"\n{3,}", "\n\n", TEMPLATE_ONLY_RE.sub("", text))


def project_rules_of(agents_md: str) -> str:
    """The '## Project rules' section of an AGENTS.md (template-only blocks removed)."""
    i = agents_md.find("## Project rules")
    if i < 0:
        raise ScaffoldError("The template's AGENTS.md has no '## Project rules' section; "
                            "migrate the template first (see SKILL.md › migrate).")
    return strip_template_only(agents_md[i:])


def _fetch_template(src: str, dest: Path) -> None:
    if Path(src).is_dir():
        # A local template may have been used: leave out git data, environments,
        # caches and build output, and respect nothing else.
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", ".coverage",
            "coverage.xml", "htmlcov", "dist", "build", "site", "*.egg-info", "*.bundle"))
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
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary file without a telling suffix
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
    py.write_text(text, encoding="utf-8")

    (dest / "CHANGELOG.md").write_text(CHANGELOG.format(name=name), encoding="utf-8")
    agents = dest / "AGENTS.md"
    if not agents.exists():
        raise ScaffoldError("The template has no AGENTS.md; migrate the template first.")
    agents.write_text(compose(name, args.description,
                              project_rules_of(agents.read_text(encoding="utf-8"))),
                      encoding="utf-8")
    shutil.copy(ASSETS / "CLAUDE.md", dest / "CLAUDE.md")
    readme = dest / "README.md"
    rtext = strip_template_only(readme.read_text(encoding="utf-8"))
    rtext = re.sub(r"^# .*\n+", f"# {name}\n\n{args.description}\n\n", rtext, count=1, flags=re.M)
    readme.write_text(rtext, encoding="utf-8")
    leftovers = [str(f.relative_to(dest)) for f in dest.rglob("*")
                 if f.is_file() and f.suffix in {".md", ".toml", ".yaml", ".yml"}
                 and MARKER_LINE_RE.search(f.read_text(encoding="utf-8", errors="ignore"))]
    if leftovers:
        raise ScaffoldError(f"Unbalanced template-only markers left in: {', '.join(leftovers)}")

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


def cmd_assemble(args) -> int:
    d = Path(args.dir)
    rules = Path(args.rules).read_text(encoding="utf-8")
    (d / "AGENTS.md").write_text(compose(args.name, args.description, rules), encoding="utf-8")
    shutil.copy(ASSETS / "CLAUDE.md", d / "CLAUDE.md")
    n = len((d / "AGENTS.md").read_text(encoding="utf-8").splitlines())
    print(f"Wrote {d / 'AGENTS.md'} ({n} lines) and CLAUDE.md (@AGENTS.md).")
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
    n.add_argument("--template", default=TEMPLATE_URL)
    n.add_argument("--no-git", action="store_true")
    n.add_argument("--no-lock", action="store_true")
    for c in ("sync", "check"):
        sub.add_parser(c).add_argument("dir")
    a = sub.add_parser("assemble")
    a.add_argument("dir")
    a.add_argument("--rules", required=True, help="file with the project rules")
    a.add_argument("--name", required=True)
    a.add_argument("--description", required=True)
    args = ap.parse_args()
    try:
        return {"new": cmd_new, "sync": cmd_sync, "check": cmd_check,
                "assemble": cmd_assemble}[args.cmd](args)
    except ScaffoldError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
