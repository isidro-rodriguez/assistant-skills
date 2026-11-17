#!/usr/bin/env python3
"""Create, check and upgrade a Zensical documentation site with the canonical layout.

Subcommands:
  new DIR       Create the canonical layout in DIR (never overwrites without --force):
                zensical.toml, docs/ (index, manifest, favicons, fonts, stylesheets),
                docs_templates/ (main.html, es.html.jinja with --package) and,
                with --gh-pages, .github/workflows/docs.yml.
  favicons DIR  Regenerate docs/assets/favicon/ from a logo (SVG or PNG).
  sync DIR      Refresh the managed copies (es.html.jinja) and the zensical block
                of AGENTS.md.
  check DIR     Compare DIR with the canonical layout; exit 1 on any FAIL.
  measure DIR   Measure the built site in a browser against Practical Typography:
                body text 15-25 px, line spacing 120-145 %, 45-90 characters per
                line; exit 1 if a page is out of range. Fonts are the project's choice.
  upgrade DIR   Upgrade Zensical in the lock, then diff every template in
                docs_templates/ against the new theme and build the site.

Favicon generation needs Pillow (and resvg-py for SVG logos); run it as
  uv run --with pillow --with resvg-py python scripts/site.py ...
measure needs Playwright and a Chromium-based browser (Chrome or Edge installed, or
`playwright install chromium`):
  uv run --with playwright python scripts/site.py measure .
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
TYPOGRAPHY = "docs/assets/stylesheets/typography.css"
FONTS = "docs/assets/fonts"
MAIN = "docs_templates/main.html"
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
HEAD_LINKS = [*(f"assets/favicon/{n}" for n in
                ("favicon.ico", "favicon-32x32.png", "favicon-16x16.png", "apple-touch-icon.png")),
              "site.webmanifest"]
IGNORED_SITE = {"site/", "/site/", "site", "/site"}
AGENTS_RE = re.compile(r"<!-- zensical:start.*?<!-- zensical:end -->\n?", re.S)
THEME_PROBE = """
import importlib.metadata as m, importlib.util as u, json, pathlib
for pkg in ("zensical_ui", "zensical"):
    spec = u.find_spec(pkg)
    if spec and spec.origin:
        d = pathlib.Path(spec.origin).parent / "templates"
        if (d / "base.html").exists():
            print(json.dumps({"dir": str(d), "package": pkg,
                              "zensical": m.version("zensical")}))
            break
"""


class SiteError(Exception):
    """A problem the user must fix; printed without a traceback."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Lowercase ASCII slug for file names (``pyMedia`` -> ``pymedia``)."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not s:
        raise SiteError(f"Cannot derive a file name from {name!r}; pass --slug.")
    return s


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


def _starter_files() -> list[str]:
    """Typography and fonts that `new` copies once; afterwards they belong to the project."""
    return [TYPOGRAPHY, *(f"{FONTS}/{p.name}" for p in sorted((SITE / FONTS).iterdir()))]


def _managed_files(with_mkdocstrings: bool) -> list[str]:
    """Files kept identical to the skill's copy (refreshed by `sync`)."""
    return [ES_JINJA] if with_mkdocstrings else []


def _uses_mkdocstrings(cfg: dict) -> bool:
    return "mkdocstrings" in cfg.get("project", {}).get("plugins", {})


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
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", args.theme_color):
        raise SiteError("--theme-color must be a #rrggbb colour.")
    slug = args.slug or slugify(args.name)
    gh = _github_parts(args.repo_url)
    site_url = args.site_url or (f"https://{gh[0].lower()}.github.io/{gh[1]}/" if gh else "")
    if not site_url:
        raise SiteError("Pass --site-url: it can only be derived from a GitHub --repo-url.")
    logo = Path(args.logo)
    values = {
        "name": args.name, "description": args.description, "author": args.author,
        "site_url": site_url if site_url.endswith("/") else site_url + "/",
        "repo_url": args.repo_url, "repo_name": "/".join(gh) if gh else args.repo_url,
        "year": str(dt.date.today().year), "theme_color": args.theme_color.lower(),
        "slug": slug, "logo": f"logo{logo.suffix.lower()}", "package": args.package or "",
    }
    log: list[str] = []
    toml = _render("zensical.toml.tmpl", values)
    if args.package:
        plugins = _render("mkdocstrings.toml.tmpl", values)
        toml = toml.replace("\n[project.theme]\n", plugins + "\n[project.theme]\n", 1)
    _write(root / "zensical.toml", toml, args.force, log)
    _write(root / "docs/index.md", _render("index.md.tmpl", values), args.force, log)
    _write(root / "docs/site.webmanifest", _render("site.webmanifest.tmpl", values), args.force, log)
    _write(root / f"docs/assets/stylesheets/{slug}.css", _render("project.css.tmpl", values),
           args.force, log)
    _copy(SITE / MAIN, root / MAIN, args.force, log)
    for rel in [*_starter_files(), *_managed_files(bool(args.package))]:
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
    deps = "zensical" + (" mkdocstrings-python mkdocs-api-autonav" if args.package else "")
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
    if theme.get("custom_dir") != "docs_templates":
        r.fail('[project.theme] custom_dir is not "docs_templates": docs_templates/main.html '
               "(favicons, manifest) is ignored.")
    if theme.get("language") != "es":
        r.fail('[project.theme] language is not "es".')
    css = project.get("extra_css", [])
    tcss = TYPOGRAPHY.removeprefix("docs/")
    if tcss in css and theme.get("font", None) is not False:
        r.warn(f"{tcss} is loaded but [project.theme] font is not false: the theme's "
               "Google Fonts variables override its font choices.")
    for rel in [*css, *project.get("extra_javascript", [])]:
        if isinstance(rel, str) and not rel.startswith(("http:", "https:")) \
                and not (docs / rel).exists():
            r.fail(f"extra_css/extra_javascript points to a missing file: docs/{rel}.")
    for key in ("favicon", "logo"):
        rel = theme.get(key)
        if not rel:
            r.fail(f"[project.theme] {key} is not set.")
        elif not (docs / rel).exists():
            r.fail(f"[project.theme] {key} points to a missing file: docs/{rel}.")
    if theme.get("favicon") and not theme["favicon"].startswith("assets/favicon/"):
        r.warn(f"[project.theme] favicon is {theme['favicon']}; canonical: "
               "assets/favicon/favicon-32x32.png.")
    color = project.get("extra", {}).get("theme_color", "")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(color)):
        r.fail("[project.extra] theme_color is missing or not #rrggbb (main.html reads it).")
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
    fav = root / "docs/assets/favicon"
    for name, size in FAVICONS.items():
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
    man = root / "docs/site.webmanifest"
    if not man.exists():
        r.fail("missing docs/site.webmanifest.")
    else:
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            r.fail(f"docs/site.webmanifest is not valid JSON: {err}")
            data = {}
        for icon in data.get("icons", []):
            src = icon.get("src", "")
            if src.startswith("/"):
                r.fail(f"manifest icon {src} is absolute; use a relative path.")
            elif not (root / "docs" / src).exists():
                r.fail(f"manifest icon {src} not found in docs/.")
        color = cfg.get("project", {}).get("extra", {}).get("theme_color")
        if color and data.get("theme_color", "").lower() != str(color).lower():
            r.warn("manifest theme_color differs from [project.extra] theme_color.")
        if data.get("start_url", "./") .startswith("/"):
            r.fail("manifest start_url is absolute; use \"./\".")


def _check_templates(root: Path, r: Report) -> None:
    main = root / MAIN
    if not main.exists():
        r.fail(f"missing {MAIN}.")
        return
    # main.html may extend a local page template (reCocina: main.html -> page.html ->
    # base.html); then the head belongs to that root template, so read the local chain.
    text, name, seen = "", "main.html", set()
    while name and name not in seen and (root / "docs_templates" / name).exists():
        seen.add(name)
        part = (root / "docs_templates" / name).read_text(encoding="utf-8")
        text += part
        m = re.search(r"""{%-?\s*extends\s+['"]([^'"]+)['"]""", part)
        name = m.group(1) if m else ""
    if not re.search(r"{%-?\s*block\s+extrahead\s*-?%}", text):
        r.fail(f"{MAIN} (or the local template it extends) has no extrahead block "
               "(favicons, manifest, theme colour).")
    for link in HEAD_LINKS:
        if not re.search(rf"""['"]{re.escape(link)}['"]\s*\|\s*url""", text):
            r.fail(f"{MAIN} does not link {link} with a relative path (`'{link}' | url`).")
    if "theme-color" not in text:
        r.fail(f"{MAIN} has no theme-color meta.")
    for path in sorted((root / "docs_templates").rglob("*.html")):
        for m in re.finditer(r"""['"](/[^'"]*)['"]\s*\|\s*url""", path.read_text(encoding="utf-8")):
            r.fail(f"{path.relative_to(root)}: absolute path {m.group(1)} breaks the site "
                   "under a sub-path; drop the leading '/'.")
    if not filecmp.cmp(SITE / MAIN, main, shallow=False):
        r.info(f"{MAIN} differs from the canonical template (project blocks kept).")


def _check_repo(cfg: dict, root: Path, r: Report) -> None:
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
    _check_templates(root, r)
    _check_repo(cfg, root, r)
    return r.finish()


# ---------------------------------------------------------------------------
# measure
# ---------------------------------------------------------------------------

# Practical Typography, "summary of key rules": body text 15-25 px on the web, line
# spacing 120-145 % of the point size, 45-90 characters per line on average.
SIZE_PX = (15.0, 25.0)
LEADING = (1.20, 1.45)
MEASURE = (45.0, 90.0)
VIEWPORTS = ((1280, 900), (1920, 1080))
# Measured on the home page when it has no long paragraph of its own.
PROBE = ("La tipografía de una página se juzga por su texto corrido: el tamaño de la letra, "
         "el interlineado y la longitud de las líneas deciden si se lee con comodidad. "
         "Este párrafo de prueba solo existe durante la medición y nunca se publica.")
# Fonts Butterick singles out as overused defaults: a warning, never a failure.
SYSTEM_FONTS = {"times new roman", "times", "arial", "helvetica", "calibri", "cambria",
                "verdana", "segoe ui", "-apple-system", "system-ui", "roboto"}
MEASURE_JS = """
(probe) => {
  const article = document.querySelector("article") || document.querySelector(".md-content");
  if (!article) return [];
  const out = [];
  let paras = [...article.querySelectorAll("p")].filter(
    (p) => p.textContent.replace(/\\s+/g, " ").trim().length >= 120);
  if (!paras.length && probe) {
    // Short pages still have a typography: measure a probe paragraph set like body text.
    const p = document.createElement("p");
    p.textContent = probe;
    article.appendChild(p);
    paras = [p];
  }
  for (const p of paras) {
    if (p.closest("table, pre, nav, figure, .admonition-title, footer")) continue;
    const text = p.textContent.replace(/\\s+/g, " ").trim();
    const cs = getComputedStyle(p);
    const size = parseFloat(cs.fontSize);
    const leading = cs.lineHeight === "normal" ? NaN : parseFloat(cs.lineHeight);
    const width = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    // Average character width of this very text, set on one line in the same font.
    const probe = document.createElement("span");
    probe.style.cssText = "position:absolute;visibility:hidden;white-space:nowrap";
    probe.textContent = text;
    p.appendChild(probe);
    const perChar = probe.getBoundingClientRect().width / text.length;
    probe.remove();
    out.push({size, leading: leading / size, chars: width / perChar,
              family: cs.fontFamily.split(",")[0].replace(/["']/g, "").trim()});
  }
  return out;
}
"""


def _pages(site: Path, limit: int) -> list[str]:
    """Relative URLs of the home page and the largest pages (the most text to measure)."""
    files = [p for p in site.rglob("index.html")
             if "assets" not in p.parts and "python" not in p.parts]
    files.sort(key=lambda p: (p.parent != site, -p.stat().st_size))
    rels = [p.relative_to(site).parent.as_posix() for p in files[:limit]]
    return ["" if r == "." else r + "/" for r in rels]


def _median(values: list[float]) -> float:
    values = sorted(values)
    return values[len(values) // 2]


def cmd_measure(args: argparse.Namespace) -> int:
    import functools
    import http.server
    import threading
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as err:
        raise SiteError("measure needs Playwright: run with "
                        "`uv run --with playwright python scripts/site.py measure .`.") from err
    root = Path(args.dir).resolve()
    site = root / _load_toml(root).get("project", {}).get("site_dir", "site")
    if not (site / "index.html").exists():
        raise SiteError(f"{site}/index.html not found: build the site first.")
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

    handler = functools.partial(Quiet, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    r = Report()
    families: set[str] = set()
    measured = 0
    with sync_playwright() as pw:
        browser = None
        for channel in ("chrome", "msedge", None):
            try:
                browser = pw.chromium.launch(channel=channel) if channel else pw.chromium.launch()
                break
            except Exception:  # noqa: BLE001 - try the next browser
                continue
        if browser is None:
            raise SiteError("No browser for Playwright: install Chrome or Edge, or run "
                            "`uv run --with playwright playwright install chromium`.")
        for width, height in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            for rel in _pages(site, args.pages):
                page.goto(base + rel, wait_until="load")
                page.evaluate("document.fonts.ready")
                rows = page.evaluate(MEASURE_JS, PROBE if rel == "" else None)
                if not rows:
                    continue
                measured += 1
                size = _median([x["size"] for x in rows])
                lead = _median([x["leading"] for x in rows])
                chars = _median([x["chars"] for x in rows])
                families |= {x["family"] for x in rows}
                where = f"/{rel} at {width}px"
                line = f"{where}: {size:.1f} px, line spacing {lead:.0%}, {chars:.0f} characters"
                problems = []
                if not SIZE_PX[0] <= size <= SIZE_PX[1]:
                    problems.append(f"size outside {SIZE_PX[0]:.0f}-{SIZE_PX[1]:.0f} px")
                if not (LEADING[0] - 0.005) <= lead <= (LEADING[1] + 0.005):
                    problems.append(f"line spacing outside {LEADING[0]:.0%}-{LEADING[1]:.0%}")
                if not MEASURE[0] <= chars <= MEASURE[1]:
                    problems.append(f"line length outside {MEASURE[0]:.0f}-{MEASURE[1]:.0f}")
                if problems:
                    r.fail(f"{line} ({'; '.join(problems)}).")
                else:
                    r.info(line)
            page.close()
        browser.close()
    server.shutdown()
    if not measured:
        r.warn("no page has paragraphs long enough to measure.")
    for fam in sorted(families):
        if fam.lower() in SYSTEM_FONTS:
            r.warn(f"body text in {fam}: Practical Typography advises against system fonts.")
    r.info(f"body fonts: {', '.join(sorted(families)) or 'none measured'}")
    return r.finish()


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def _run(cmd: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def _theme(root: Path) -> dict:
    p = _run(["uv", "run", "--no-sync", "python", "-c", THEME_PROBE], root)
    if p.returncode or not p.stdout.strip():
        raise SiteError(f"Cannot locate the installed Zensical theme (`uv sync` first?):\n{p.stderr}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def _blocks(text: str) -> set[str]:
    return set(re.findall(r"{%-?\s*block\s+(\w+)", text))


def _resolve(name: str, local: Path, theme: Path) -> Path | None:
    """Template lookup as Zensical does it: docs_templates/ first, then the theme."""
    for d in (local, theme):
        if (d / name).exists():
            return d / name
    return None


def _chain_blocks(name: str, local: Path, theme: Path) -> set[str]:
    """Blocks defined by a template and every template it extends."""
    found: set[str] = set()
    seen: set[Path] = set()
    path = _resolve(name, local, theme)
    while path and path not in seen:
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        found |= _blocks(text)
        m = re.search(r"""{%-?\s*extends\s+['"]([^'"]+)['"]""", text)
        # A local template may extend the theme's template of the same name.
        path = None if not m else (
            theme / m.group(1) if (theme / m.group(1)).exists() and local / m.group(1) == path
            else _resolve(m.group(1), local, theme))
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
    old = _theme(root)
    snap = Path(tempfile.mkdtemp(prefix="zensical-theme-"))
    shutil.copytree(old["dir"], snap, dirs_exist_ok=True)
    pinned = _bump_pin(root, args.to)
    if pinned:
        print(f"pyproject.toml pinned zensical=={pinned}; pin moved.")
    spec = f"zensical=={args.to}" if args.to else "zensical"
    for cmd in (["uv", "lock", "--upgrade-package", spec, "--upgrade-package", "zensical-ui"],
                ["uv", "sync"]):
        p = _run(cmd, root)
        if p.returncode:
            raise SiteError(f"`{' '.join(cmd)}` failed:\n{p.stderr}")
    new = _theme(root)
    print(f"Zensical {old['zensical']} -> {new['zensical']} "
          f"(theme package: {old['package']} -> {new['package']})\n")
    new_dir = Path(new["dir"])
    review = 0
    for ov in _overrides(root):
        rel = ov.relative_to(root / "docs_templates").as_posix()
        text = ov.read_text(encoding="utf-8")
        before, after = snap / rel, new_dir / rel
        extends = re.search(r"""{%-?\s*extends\s+['"]([^'"]+)['"]""", text)
        if extends:
            # A block override survives as long as every block still exists upstream.
            base = extends.group(1)
            missing = _blocks(text) - _chain_blocks(base, root / "docs_templates", new_dir)
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
    n.add_argument("--theme-color", required=True, help="#rrggbb")
    n.add_argument("--logo", required=True, help="SVG or PNG")
    n.add_argument("--slug", help="stylesheet name (default: from --name)")
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
    m = sub.add_parser("measure", help="check the built site against Practical Typography")
    m.add_argument("dir")
    m.add_argument("--pages", type=int, default=12, help="pages to sample (default: 12)")
    u = sub.add_parser("upgrade", help="upgrade Zensical and review template overrides")
    u.add_argument("dir")
    u.add_argument("--to", help="target version (default: latest)")
    args = ap.parse_args()
    handler = {"new": cmd_new, "favicons": cmd_favicons, "sync": cmd_sync,
               "check": cmd_check, "measure": cmd_measure, "upgrade": cmd_upgrade}[args.cmd]
    try:
        return handler(args)
    except SiteError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
