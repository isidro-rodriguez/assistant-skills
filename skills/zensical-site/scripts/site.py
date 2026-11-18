#!/usr/bin/env python3
"""Create, check and upgrade a Zensical documentation site on the techsical theme.

Subcommands:
  new DIR       Create the canonical layout in DIR (never overwrites without --force):
                zensical.toml (theme techsical), docs/ (index, manifest, favicons,
                logo), es.html.jinja with --package and, with --gh-pages,
                .github/workflows/docs.yml.
  favicons DIR  Regenerate docs/assets/favicon/ from a logo (SVG or PNG).
  sync DIR      Refresh the managed copies (es.html.jinja) and the zensical block
                of AGENTS.md.
  check DIR     Compare DIR with the canonical layout; exit 1 on any FAIL.
  upgrade DIR   Upgrade techsical and Zensical in the lock, then diff every template
                in docs_templates/ against the new themes and build the site.

Favicon generation needs Pillow (and resvg-py for SVG logos); run it as
  uv run --with pillow --with resvg-py python scripts/site.py ...
Everything else uses only the standard library (Python 3.11+, for tomllib).
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import filecmp
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from string import Template

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SITE = ASSETS / "site"
THEME = "techsical"
DEFAULT_PRIMARY = "#164e63"  # techsical's own primary colour
ES_JINJA = "docs_templates/python/material/languages/es.html.jinja"
WORKFLOW = ".github/workflows/docs.yml"
FAVICONS = {  # file name -> square size in px (0: multi-size .ico)
    "favicon.ico": 0,
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "apple-touch-icon.png": 180,
    "android-chrome-192x192.png": 192,
    "android-chrome-512x512.png": 512,
}
# What techsical already puts in <head>; a site template that repeats it duplicates it.
HEAD_MARKERS = ("assets/favicon/", "site.webmanifest", "theme-color")
IGNORED_SITE = {"site/", "/site/", "site", "/site"}
AGENTS_RE = re.compile(r"<!-- zensical:start.*?<!-- zensical:end -->\n?", re.S)
# Template folders in lookup order after docs_templates/: techsical's (when the site
# uses it) and Zensical's own theme (zensical_ui since 0.1, zensical before).
THEME_PROBE = """
import importlib.metadata as m, importlib.util as u, json, pathlib
out = {"dirs": [], "versions": {}}
spec = u.find_spec("techsical")
if spec and spec.origin:
    out["dirs"].append(str(pathlib.Path(spec.origin).parent / "theme"))
    out["versions"]["techsical"] = m.version("techsical")
for pkg in ("zensical_ui", "zensical"):
    spec = u.find_spec(pkg)
    if spec and spec.origin:
        d = pathlib.Path(spec.origin).parent / "templates"
        if (d / "base.html").exists():
            out["dirs"].append(str(d))
            out["package"] = pkg
            out["versions"]["zensical"] = m.version("zensical")
            break
print(json.dumps(out))
"""


class SiteError(Exception):
    """A problem the user must fix; printed without a traceback."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write(path: Path, text: str, force: bool, log: list[str]) -> None:
    if path.exists() and not force:
        log.append(f"kept     {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    log.append(f"wrote    {path}")


def _copy(src: Path, dest: Path, force: bool, log: list[str]) -> None:
    if dest.exists() and not force:
        log.append(f"kept     {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    log.append(f"copied   {dest}")


def _render(name: str, values: dict[str, str]) -> str:
    return Template((ASSETS / name).read_text(encoding="utf-8")).substitute(values)


def _load_toml(root: Path) -> dict:
    f = root / "zensical.toml"
    if not f.exists():
        raise SiteError(f"{f} not found.")
    try:
        return tomllib.loads(f.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as err:
        raise SiteError(f"{f} is not valid TOML: {err}") from err


def _png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def _managed_files(with_mkdocstrings: bool) -> list[str]:
    """Files kept identical to the skill's copy (refreshed by `sync`)."""
    return [ES_JINJA] if with_mkdocstrings else []


def _uses_mkdocstrings(cfg: dict) -> bool:
    return "mkdocstrings" in cfg.get("project", {}).get("plugins", {})


def _techsical(cfg: dict) -> dict:
    """The site's [project.extra.techsical] table."""
    return cfg.get("project", {}).get("extra", {}).get("techsical", {}) or {}


def _site_color(cfg: dict) -> str:
    """Colour of the browser bar, as techsical-head.html picks it."""
    tx = _techsical(cfg)
    return str(tx.get("theme_color") or tx.get("primary") or DEFAULT_PRIMARY)


def update_agents(root: Path, log: list[str]) -> None:
    """Insert or refresh the zensical block at the end of AGENTS.md, if the file exists."""
    f = root / "AGENTS.md"
    if not f.exists():
        log.append("skipped  AGENTS.md (not found)")
        return
    block = (ASSETS / "AGENTS.zensical.md").read_text(encoding="utf-8")
    text = f.read_text(encoding="utf-8")
    new = AGENTS_RE.sub(lambda _: block, text, count=1) if AGENTS_RE.search(text) \
        else text.rstrip("\n") + "\n\n" + block
    if new != text:
        f.write_text(new, encoding="utf-8", newline="\n")
        log.append(f"updated  {f}")
    else:
        log.append(f"kept     {f}")


# ---------------------------------------------------------------------------
# favicons
# ---------------------------------------------------------------------------

def make_favicons(logo: Path, out: Path, log: list[str], missing_only: bool = False) -> None:
    """Render the favicon set of FAVICONS from an SVG or PNG logo."""
    try:
        from PIL import Image
    except ImportError as err:
        raise SiteError("Favicons need Pillow: run with "
                        "`uv run --with pillow --with resvg-py python scripts/site.py ...`.") from err
    if not logo.exists():
        raise SiteError(f"Logo {logo} not found.")
    out.mkdir(parents=True, exist_ok=True)

    def render(size: int) -> Image.Image:
        if logo.suffix.lower() == ".svg":
            try:
                import resvg_py
            except ImportError as err:
                raise SiteError("SVG logos need resvg-py: add `--with resvg-py`.") from err
            import io
            png = bytes(resvg_py.svg_to_bytes(svg_path=str(logo), width=size, height=size))
            return Image.open(io.BytesIO(png)).convert("RGBA")
        img = Image.open(logo).convert("RGBA")
        # Pad to a square canvas so a wide logo isn't distorted.
        side = max(img.size)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        return canvas.resize((size, size), Image.LANCZOS)

    for name, size in FAVICONS.items():
        if missing_only and (out / name).exists():
            log.append(f"kept     {out / name}")
            continue
        if size:
            render(size).save(out / name, optimize=True)
        else:
            render(256).save(out / name, sizes=[(16, 16), (32, 32), (48, 48)])
        log.append(f"wrote    {out / name}")


# ---------------------------------------------------------------------------
# new / favicons / sync
# ---------------------------------------------------------------------------

def _github_parts(repo_url: str) -> tuple[str, str] | None:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    return (m.group(1), m.group(2)) if m else None


def cmd_new(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    for opt, val in (("--primary", args.primary), ("--accent", args.accent)):
        if val and not re.fullmatch(r"#[0-9a-fA-F]{6}", val):
            raise SiteError(f"{opt} must be a #rrggbb colour.")
    gh = _github_parts(args.repo_url)
    site_url = args.site_url or (f"https://{gh[0].lower()}.github.io/{gh[1]}/" if gh else "")
    if not site_url:
        raise SiteError("Pass --site-url: it can only be derived from a GitHub --repo-url.")
    logo = Path(args.logo)
    accent = f'accent = "{args.accent.lower()}"\n' if args.accent else ""
    values = {
        "name": args.name, "description": args.description, "author": args.author,
        "site_url": site_url if site_url.endswith("/") else site_url + "/",
        "repo_url": args.repo_url, "repo_name": "/".join(gh) if gh else args.repo_url,
        "year": str(dt.date.today().year), "primary": args.primary.lower(), "accent": accent,
        "logo": f"logo{logo.suffix.lower()}", "package": args.package or "",
    }
    log: list[str] = []
    toml = _render("zensical.toml.tmpl", values)
    if args.package:
        plugins = _render("mkdocstrings.toml.tmpl", values)
        toml = toml.replace("\n[project.theme]\n", plugins + "\n[project.theme]\n", 1)
    _write(root / "zensical.toml", toml, args.force, log)
    _write(root / "docs/index.md", _render("index.md.tmpl", values), args.force, log)
    _write(root / "docs/site.webmanifest", _render("site.webmanifest.tmpl", values), args.force, log)
    for rel in _managed_files(bool(args.package)):
        _copy(SITE / rel, root / rel, args.force, log)
    if args.gh_pages:
        _copy(SITE / WORKFLOW, root / WORKFLOW, args.force, log)
    _copy(logo, root / "docs/assets/images" / values["logo"], args.force, log)
    fav = root / "docs/assets/favicon"
    if args.force or not (fav / "favicon.ico").exists():
        make_favicons(logo, fav, log)
    else:
        log.append(f"kept     {fav}/ (run `favicons` to regenerate)")
    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if not IGNORED_SITE & {ln.strip() for ln in lines}:
        gi.write_text("\n".join([*lines, "site/"]) + "\n", encoding="utf-8", newline="\n")
        log.append(f"updated  {gi} (site/)")
    update_agents(root, log)
    print("\n".join(log))
    deps = THEME + (" mkdocstrings-python mkdocs-api-autonav" if args.package else "")
    print(f"\nNext: `uv add --dev {deps}`, then `uv run zensical build`.")
    return 0


def cmd_favicons(args: argparse.Namespace) -> int:
    log: list[str] = []
    make_favicons(Path(args.logo), Path(args.dir) / "docs/assets/favicon", log, args.missing_only)
    print("\n".join(log))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    cfg = _load_toml(root)
    log: list[str] = []
    for rel in _managed_files(_uses_mkdocstrings(cfg)):
        if (root / rel).exists() and filecmp.cmp(SITE / rel, root / rel, shallow=False):
            continue
        _copy(SITE / rel, root / rel, True, log)
    update_agents(root, log)
    print("\n".join(log) or "Managed copies already up to date.")
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

class Report:
    """Collects check findings and prints them grouped by level."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def add(self, level: str, msg: str) -> None:
        self.items.append((level, msg))

    def fail(self, msg: str) -> None:
        self.add("FAIL", msg)

    def warn(self, msg: str) -> None:
        self.add("WARN", msg)

    def info(self, msg: str) -> None:
        self.add("INFO", msg)

    def finish(self) -> int:
        for level in ("FAIL", "WARN", "INFO"):
            for lv, msg in self.items:
                if lv == level:
                    print(f"{lv}: {msg}")
        fails = sum(lv == "FAIL" for lv, _ in self.items)
        warns = sum(lv == "WARN" for lv, _ in self.items)
        print(f"\n{fails} FAIL, {warns} WARN" if self.items else "OK: canonical layout.")
        return 1 if fails else 0


def _check_toml(cfg: dict, root: Path, r: Report) -> None:
    project = cfg.get("project", {})
    theme = project.get("theme", {})
    docs = root / project.get("docs_dir", "docs")
    if theme.get("name") != THEME:
        r.fail(f'[project.theme] name is not "{THEME}".')
    if theme.get("language", "es") != "es":
        r.fail('[project.theme] language is not "es".')
    if "navigation.instant" in theme.get("features", []):
        r.fail("[project.theme] features has navigation.instant: it swaps pages without "
               "loading them and cancels techsical's page transitions; drop it (and "
               "navigation.instant.prefetch).")
    if theme.get("font", False) is not False:
        r.warn("[project.theme] font is set: techsical serves its fonts itself; choose "
               "other families with font_text/font_ui/font_code in [project.extra.techsical].")
    if theme.get("palette"):
        r.info("[project.theme] palette is set: techsical already has light, dark and system "
               "toggles; keep it only if the project changes them.")
    for rel in [*project.get("extra_css", []), *project.get("extra_javascript", [])]:
        if isinstance(rel, str) and not rel.startswith(("http:", "https:")) \
                and not (docs / rel).exists():
            r.fail(f"extra_css/extra_javascript points to a missing file: docs/{rel}.")
    for key in ("favicon", "logo"):
        rel = theme.get(key)
        if rel and not (docs / rel).exists():
            r.fail(f"[project.theme] {key} points to a missing file: docs/{rel}.")
    if not theme.get("logo"):
        r.fail("[project.theme] logo is not set.")
    if theme.get("favicon") and not theme["favicon"].startswith("assets/favicon/"):
        r.warn(f"[project.theme] favicon is {theme['favicon']}; techsical's default is "
               "assets/favicon/favicon-32x32.png: drop the key.")
    if "theme_color" in project.get("extra", {}):
        r.fail("[project.extra] theme_color is the old main.html setting: techsical takes "
               "the colour from [project.extra.techsical] primary (or theme_color there).")
    tx = _techsical(cfg)
    for key in ("primary", "accent", "primary_dark", "accent_dark", "theme_color"):
        if key in tx and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(tx[key])):
            r.fail(f"[project.extra.techsical] {key} is not a #rrggbb colour.")
    if "primary" not in tx:
        r.warn("[project.extra.techsical] primary is not set: the site uses techsical's "
               "default colour.")
    site_url = project.get("site_url", "")
    if site_url and not site_url.endswith("/"):
        r.warn("site_url should end with '/'.")
    gh = _github_parts(project.get("repo_url", ""))
    m = re.match(r"https://[^/]+\.github\.io/([^/]+)/", site_url)
    if gh and m and m.group(1) != gh[1]:
        r.fail(f"site_url path /{m.group(1)}/ does not match the repo name {gh[1]} "
               "(GitHub Pages paths are case-sensitive).")
    if _uses_mkdocstrings(cfg):
        mk = project["plugins"]["mkdocstrings"]
        if mk.get("locale") != "es":
            r.fail('[project.plugins.mkdocstrings] locale is not "es".')
        if mk.get("custom_templates") != "docs_templates":
            r.fail('[project.plugins.mkdocstrings] custom_templates is not "docs_templates".')


def _check_files(cfg: dict, root: Path, r: Report) -> None:
    tx = _techsical(cfg)
    fav = root / "docs/assets/favicon"
    for name, size in FAVICONS.items() if tx.get("favicons") is not False else ():
        f = fav / name
        if not f.exists():
            r.fail(f"missing favicon: {f.relative_to(root)} (run `favicons`).")
        elif size and _png_size(f) != (size, size):
            r.fail(f"{f.relative_to(root)} is not a {size}x{size} PNG.")
    for rel in _managed_files(_uses_mkdocstrings(cfg)):
        f = root / rel
        if not f.exists():
            r.fail(f"missing managed file {rel} (run `sync`).")
        elif not filecmp.cmp(SITE / rel, f, shallow=False):
            r.fail(f"{rel} differs from the managed copy (run `sync`).")
    if tx.get("manifest") is False:
        return
    man = root / "docs/site.webmanifest"
    if not man.exists():
        r.fail("missing docs/site.webmanifest (or set manifest = false in "
               "[project.extra.techsical]).")
        return
    try:
        data = json.loads(man.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        r.fail(f"docs/site.webmanifest is not valid JSON: {err}")
        return
    for icon in data.get("icons", []):
        src = icon.get("src", "")
        if src.startswith("/"):
            r.fail(f"manifest icon {src} is absolute; use a relative path.")
        elif not (root / "docs" / src).exists():
            r.fail(f"manifest icon {src} not found in docs/.")
    if data.get("theme_color", "").lower() != _site_color(cfg).lower():
        r.warn(f"manifest theme_color differs from the site colour {_site_color(cfg)}.")
    if data.get("start_url", "./").startswith("/"):
        r.fail('manifest start_url is absolute; use "./".')


def _template_chain(root: Path, name: str) -> str:
    """Text of a local template and the local templates it extends."""
    text, seen = "", set()
    while name and name not in seen and (root / "docs_templates" / name).exists():
        seen.add(name)
        part = (root / "docs_templates" / name).read_text(encoding="utf-8")
        text += part
        m = re.search(r"""{%-?\s*extends\s+['"]([^'"]+)['"]""", part)
        name = m.group(1) if m else ""
    return text


def _check_templates(cfg: dict, root: Path, r: Report) -> None:
    d = root / "docs_templates"
    overrides = [p for p in sorted(d.rglob("*.html"))
                 if "python" not in p.relative_to(d).parts] if d.exists() else []
    custom_dir = cfg.get("project", {}).get("theme", {}).get("custom_dir")
    if overrides and custom_dir != "docs_templates":
        r.fail('docs_templates/ has templates but [project.theme] custom_dir is not '
               '"docs_templates": they are ignored.')
    elif not overrides and custom_dir:
        r.warn(f'[project.theme] custom_dir = "{custom_dir}" with no templates to override: '
               "drop it (Zensical would publish the folder's other files).")
    # main.html may extend a local page template (reCocina: main.html -> page.html).
    head = _template_chain(root, "main.html")
    for marker in HEAD_MARKERS:
        if marker in head:
            r.fail(f"docs_templates/main.html repeats techsical's head ({marker}): remove "
                   "it, and the file if nothing else is left.")
            break
    if (d / "partials/icons.html").exists():
        r.warn("docs_templates/partials/icons.html replaces techsical's head hook "
               "(stylesheets, colours, favicons).")
    for path in overrides:
        for m in re.finditer(r"""['"](/[^'"]*)['"]\s*\|\s*url""", path.read_text(encoding="utf-8")):
            r.fail(f"{path.relative_to(root)}: absolute path {m.group(1)} breaks the site "
                   "under a sub-path; drop the leading '/'.")
    for path in overrides:
        r.info(f"{path.relative_to(root)} overrides a template: `upgrade` reviews it.")


def _check_repo(cfg: dict, root: Path, r: Report) -> None:
    py = root / "pyproject.toml"
    if py.exists() and not re.search(r"""["']techsical\b""", py.read_text(encoding="utf-8")):
        r.fail("pyproject.toml does not depend on techsical (`uv add --dev techsical`).")
    gi = root / ".gitignore"
    if not gi.exists() or not IGNORED_SITE & {
            ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()}:
        r.warn(".gitignore does not ignore site/.")
    workflows = list((root / ".github/workflows").glob("*.y*ml"))
    builds = [w for w in workflows if "zensical build" in w.read_text(encoding="utf-8")]
    if workflows and not builds:
        r.warn("no GitHub workflow runs `zensical build`.")
    wf = root / WORKFLOW
    if wf.exists() and not filecmp.cmp(SITE / WORKFLOW, wf, shallow=False):
        r.info(f"{WORKFLOW} differs from the canonical workflow.")
    agents = root / "AGENTS.md"
    if agents.exists():
        m = AGENTS_RE.search(agents.read_text(encoding="utf-8"))
        block = (ASSETS / "AGENTS.zensical.md").read_text(encoding="utf-8")
        if not m:
            r.warn("AGENTS.md has no zensical block (run `sync`).")
        elif m.group(0).rstrip() != block.rstrip():
            r.warn("AGENTS.md zensical block has drifted (run `sync`).")


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.dir).resolve()
    r = Report()
    cfg = _load_toml(root)
    _check_toml(cfg, root, r)
    _check_files(cfg, root, r)
    _check_templates(cfg, root, r)
    _check_repo(cfg, root, r)
    return r.finish()


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def _run(cmd: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def _theme(root: Path) -> dict:
    """Installed theme folders (techsical first, then Zensical's) and versions."""
    p = _run(["uv", "run", "--no-sync", "python", "-c", THEME_PROBE], root)
    data = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
    if p.returncode or "package" not in data:
        raise SiteError(f"Cannot locate the installed Zensical theme (`uv sync` first?):\n{p.stderr}")
    return data


def _blocks(text: str) -> set[str]:
    return set(re.findall(r"{%-?\s*block\s+(\w+)", text))


def _resolve(name: str, dirs: list[Path], after: Path | None = None) -> Path | None:
    """Template lookup as Zensical does it: docs_templates/, techsical, Zensical's theme.

    A template that extends its own name (`header.html` extending `header.html`)
    continues the search in the folders after its own (``after``).
    """
    start = dirs.index(after) + 1 if after in dirs else 0
    for d in dirs[start:]:
        if (d / name).exists():
            return d / name
    return None


def _chain_blocks(name: str, dirs: list[Path]) -> set[str]:
    """Blocks defined by a template and every template it extends."""
    found: set[str] = set()
    seen: set[Path] = set()
    path = _resolve(name, dirs)
    while path and path not in seen:
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        found |= _blocks(text)
        m = re.search(r"""{%-?\s*extends\s+['"]([^'"]+)['"]""", text)
        if not m:
            break
        owner = next(d for d in dirs if path.is_relative_to(d))
        path = _resolve(m.group(1), dirs, owner if m.group(1) == path.relative_to(owner).as_posix()
                        else None)
    return found


PIN_RE = re.compile(r"""(["'])zensical\s*==\s*([0-9][^"',;\s]*)\1""")


def _latest_version() -> str:
    import urllib.request
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/zensical/json", timeout=20) as resp:
            return json.load(resp)["info"]["version"]
    except OSError as err:
        raise SiteError(f"Cannot ask PyPI for the latest Zensical ({err}); pass --to.") from err


def _bump_pin(root: Path, target: str | None) -> str | None:
    """Rewrite an exact `zensical==X` pin in pyproject.toml; return the old version."""
    f = root / "pyproject.toml"
    text = f.read_text(encoding="utf-8") if f.exists() else ""
    m = PIN_RE.search(text)
    if not m:
        return None
    target = target or _latest_version()
    f.write_text(PIN_RE.sub(lambda mm: f"{mm.group(1)}zensical=={target}{mm.group(1)}", text,
                            count=1), encoding="utf-8", newline="\n")
    return m.group(2)


def _overrides(root: Path) -> list[Path]:
    d = root / "docs_templates"
    # python/ holds mkdocstrings templates, which don't come from the theme.
    return sorted(p for p in d.rglob("*.html") if "python" not in p.relative_to(d).parts)


def cmd_upgrade(args: argparse.Namespace) -> int:
    root = Path(args.dir).resolve()
    local = root / "docs_templates"
    old = _theme(root)
    snap = Path(tempfile.mkdtemp(prefix="zensical-theme-"))
    old_dirs = []
    for i, d in enumerate(old["dirs"]):
        shutil.copytree(d, snap / str(i), dirs_exist_ok=True)
        old_dirs.append(snap / str(i))
    pinned = _bump_pin(root, args.to)
    if pinned:
        print(f"pyproject.toml pinned zensical=={pinned}; pin moved.")
    lock = ["uv", "lock", "--upgrade-package", f"zensical=={args.to}" if args.to else "zensical",
            "--upgrade-package", "zensical-ui"]
    if "techsical" in old["versions"]:
        # techsical pins a narrow Zensical range: a new Zensical comes with a new techsical.
        lock += ["--upgrade-package", "techsical"]
    for cmd in (lock, ["uv", "sync"]):
        p = _run(cmd, root)
        if p.returncode:
            raise SiteError(f"`{' '.join(cmd)}` failed:\n{p.stderr}")
    new = _theme(root)
    for pkg in ("techsical", "zensical"):
        if pkg in old["versions"] or pkg in new["versions"]:
            print(f"{pkg} {old['versions'].get(pkg, '-')} -> {new['versions'].get(pkg, '-')}")
    print(f"(Zensical theme package: {old['package']} -> {new['package']})\n")
    new_dirs = [Path(d) for d in new["dirs"]]
    review = 0
    for ov in _overrides(root):
        rel = ov.relative_to(local).as_posix()
        text = ov.read_text(encoding="utf-8")
        found_before, found_after = _resolve(rel, old_dirs), _resolve(rel, new_dirs)
        before = found_before or snap / "-" / rel
        after = found_after or Path("/nonexistent") / rel
        extends = re.search(r"""{%-?\s*extends\s+['"]([^'"]+)['"]""", text)
        if extends:
            # A block override survives as long as every block still exists upstream.
            base = extends.group(1)
            missing = _blocks(text) - _chain_blocks(
                base, new_dirs if base == rel else [local, *new_dirs])
            if missing:
                review += 1
                print(f"REVIEW {rel}: blocks {sorted(missing)} no longer exist upstream.")
            else:
                print(f"ok     {rel}: extends {base}; all its blocks still exist.")
            continue
        if not before.exists() and not after.exists():
            print(f"ok     {rel}: project template, not an override.")
        elif not after.exists():
            review += 1
            print(f"REVIEW {rel}: the theme no longer has this template; the override is dead.")
        elif before.exists() and filecmp.cmp(before, after, shallow=False):
            print(f"ok     {rel}: upstream unchanged.")
        else:
            review += 1
            print(f"REVIEW {rel}: upstream changed; port these changes into the override:")
            a = before.read_text(encoding="utf-8").splitlines() if before.exists() else []
            diff = difflib.unified_diff(a, after.read_text(encoding="utf-8").splitlines(),
                                        f"old/{rel}", f"new/{rel}", lineterm="", n=2)
            print("\n".join(f"    {ln}" for ln in diff))
    if old["package"] != new["package"]:
        for f in [*root.glob("tests/**/*.py"), *root.glob("scripts/**/*.py")]:
            src = f.read_text(encoding="utf-8", errors="replace")
            if re.search(rf"""['"]{old['package']}['"]""", src) and "templates" in src:
                review += 1
                print(f"REVIEW {f.relative_to(root)}: refers to the old theme package "
                      f"{old['package']!r}; look in {new['package']!r} first.")
    build = ["uv", "run", "zensical", "build"]
    configs = [root / "pyproject.toml", root / "vercel.json", *root.glob(".github/workflows/*.y*ml")]
    if any(f.exists() and "zensical build --strict" in f.read_text(encoding="utf-8")
           for f in configs):
        build.append("--strict")  # the project builds strictly elsewhere: match it
    print(f"\n$ {' '.join(build)}")
    p = _run(build, root)
    out = p.stdout + p.stderr
    clean = p.returncode == 0 and "No issues found" in out
    print(f"\nBuild: {'No issues found' if clean else 'FAILED or with issues'}")
    if not clean:
        print("\n".join(ln for ln in out.splitlines()[-30:]))
    shutil.rmtree(snap, ignore_errors=True)
    print(f"\n{review} item(s) to review.")
    return 0 if clean and not review else 1


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="create the canonical layout")
    n.add_argument("dir")
    n.add_argument("--name", required=True, help="site name, e.g. pyMedia")
    n.add_argument("--description", required=True, help="one line, Spanish")
    n.add_argument("--author", required=True)
    n.add_argument("--repo-url", required=True)
    n.add_argument("--site-url", help="default: GitHub Pages URL derived from --repo-url")
    n.add_argument("--primary", required=True, help="brand colour #rrggbb (also the browser bar)")
    n.add_argument("--accent", help="accent colour #rrggbb (default: techsical's)")
    n.add_argument("--logo", required=True, help="SVG or PNG")
    n.add_argument("--package", help="Python package: adds mkdocstrings and es.html.jinja")
    n.add_argument("--gh-pages", action=argparse.BooleanOptionalAction, default=True,
                   help="add .github/workflows/docs.yml (default: yes)")
    n.add_argument("--force", action="store_true", help="overwrite existing files")
    f = sub.add_parser("favicons", help="regenerate docs/assets/favicon from a logo")
    f.add_argument("dir")
    f.add_argument("--logo", required=True)
    f.add_argument("--missing-only", action="store_true", help="keep existing favicon files")
    for name, hlp in (("sync", "refresh managed copies and AGENTS.md block"),
                      ("check", "compare with the canonical layout")):
        sub.add_parser(name, help=hlp).add_argument("dir")
    u = sub.add_parser("upgrade", help="upgrade Zensical and review template overrides")
    u.add_argument("dir")
    u.add_argument("--to", help="target version (default: latest)")
    args = ap.parse_args()
    handler = {"new": cmd_new, "favicons": cmd_favicons, "sync": cmd_sync,
               "check": cmd_check, "upgrade": cmd_upgrade}[args.cmd]
    try:
        return handler(args)
    except SiteError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
