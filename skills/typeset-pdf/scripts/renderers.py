"""LaTeX math and Mermaid rendering for build_pdf.py.

Both are extracted from the Markdown *before* conversion (so Markdown never
mangles them), replaced by placeholders, rendered to SVG with Node tools in
this folder (`npm install`), and substituted back into the HTML.

Math:    $inline$, \\(inline\\), $$display$$, \\[display\\]   → MathJax SVG
Mermaid: ```mermaid fenced blocks                              → mermaid-cli SVG
         flowcharts get orthogonal edges (ELK layout) and an automatic
         direction: LR for a single chain of ≤ 4 nodes, TD otherwise.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE_BIN = HERE / "node_modules" / ".bin"
FONTS = HERE.parent / "assets" / "fonts"


class RenderError(RuntimeError):
    pass


def _token(kind: str, i: int) -> str:
    # Alphanumeric only, so Markdown leaves it untouched.
    return f"XQ{kind}{i:04d}QX"


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(?P<fence>```+|~~~+)[ \t]*(?P<info>[^\n]*)\n(?P<body>.*?)^(?P=fence)[ \t]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"(`+)(?:.+?)\1", re.S)
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.S)
# Pandoc rule: opening $ not followed by space; closing $ not preceded by space
# and not followed by a digit. Escaped \$ is ignored.
INLINE_MATH_RE = re.compile(r"(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)|\\\((.+?)\\\)")


def extract(md: str):
    """Return (markdown_with_placeholders, maths, diagrams)."""
    maths: list[dict] = []
    diagrams: list[str] = []
    shielded: dict[str, str] = {}

    def shield(m):  # protect code from math extraction
        key = _token("S", len(shielded))
        shielded[key] = m.group(0)
        return key

    def take_fence(m):
        if m.group("info").strip().lower().startswith("mermaid"):
            diagrams.append(m.group("body"))
            return "\n" + _token("D", len(diagrams) - 1) + "\n"
        return shield(m)

    md = FENCE_RE.sub(take_fence, md)
    md = INLINE_CODE_RE.sub(shield, md)

    def take_display(m):
        maths.append({"tex": (m.group(1) or m.group(2)).strip(), "display": True})
        return "\n\n" + _token("M", len(maths) - 1) + "\n\n"

    def take_inline(m):
        maths.append({"tex": (m.group(1) or m.group(2)).strip(), "display": False})
        return _token("M", len(maths) - 1)

    md = DISPLAY_MATH_RE.sub(take_display, md)
    md = INLINE_MATH_RE.sub(take_inline, md)
    md = md.replace("\\$", "$")

    for key, val in shielded.items():
        md = md.replace(key, val)
    return md, maths, diagrams


# --------------------------------------------------------------------------
# Math
# --------------------------------------------------------------------------

def _node() -> str:
    node = shutil.which("node")
    if not node:
        raise RenderError("Node.js 18+ is required for math/diagrams (https://nodejs.org).")
    if not (HERE / "node_modules").exists():
        raise RenderError(f"Run `npm install` in {HERE} to enable math/diagrams.")
    return node


def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def render_math(maths: list[dict]) -> list[str]:
    if not maths:
        return []
    proc = subprocess.run(
        [_node(), str(HERE / "render_math.cjs")],
        input=json.dumps(maths), capture_output=True, text=True, cwd=HERE,
    )
    if proc.returncode:
        raise RenderError("MathJax failed:\n" + proc.stderr[-2000:])
    out = []
    for item, res in zip(maths, json.loads(proc.stdout)):
        if "error" in res:
            raise RenderError(f"LaTeX error in ${item['tex']}$: {res['error']}")
        # Drop data-* attributes: MathJax leaves raw "<" in data-latex, which is
        # invalid XML and makes the SVG fail to load.
        svg = re.sub(r'\sdata-[\w-]+="[^"]*"', "", res["svg"])
        w = re.search(r'width="([\d.]+ex)"', svg).group(1)
        h = re.search(r'height="([\d.]+ex)"', svg).group(1)
        va = re.search(r"vertical-align:\s*([-\d.]+ex)", svg)
        alt = item["tex"].replace('"', "&quot;").replace("<", "&lt;")
        style = f"width:{w};height:{h}" + (f";vertical-align:{va.group(1)}" if va else "")
        img = f'<img class="math" alt="{alt}" style="{style}" src="{_data_uri(svg)}">'
        out.append(f'<div class="math-display">{img}</div>' if item["display"] else img)
    return out


# --------------------------------------------------------------------------
# Mermaid
# --------------------------------------------------------------------------

HEADER_RE = re.compile(r"^(\s*)(flowchart|graph)(?:[ \t]+(TB|TD|BT|RL|LR))?[ \t]*$", re.M | re.I)
LINK_RE = re.compile(
    r"\s*(?:"
    r"<?--\s+[^-|>][^>]*?\s+-->"          # A -- text --> B
    r"|<?-\.+->?|<?=+>|<?-{2,}[>xo]?|~~~"  # -->, ---, -.->, ==>, --x, --o, ~~~
    r")(?:\|[^|]*\|)?\s*"
)
NODE_ID_RE = re.compile(r"^\s*([A-Za-z0-9_\-]+)")


def flowchart_direction(src: str) -> str | None:
    """'LR' for one chain of ≤ 4 nodes, 'TD' otherwise; None if not a flowchart."""
    if not HEADER_RE.search(src):
        return None
    edges, nodes = [], set()
    for raw in src.splitlines()[1:]:
        line = raw.split("%%")[0].strip()
        if not line:
            continue
        if re.match(r"(subgraph|end\b|classDef|class |style |linkStyle|click |direction )", line):
            if line.startswith("subgraph"):
                return "TD"  # grouped diagrams are never a single chain
            continue
        parts = LINK_RE.split(line)
        groups = []
        for part in parts:
            ids = [NODE_ID_RE.match(p).group(1) for p in part.split("&") if NODE_ID_RE.match(p)]
            groups.append(ids)
            nodes.update(ids)
        for a, b in zip(groups, groups[1:]):
            edges += [(x, y) for x in a for y in b]
    if not nodes or len(nodes) > 4:
        return "TD"
    outd, ind = {}, {}
    for a, b in edges:
        outd[a] = outd.get(a, 0) + 1
        ind[b] = ind.get(b, 0) + 1
    simple_path = (
        len(edges) == len(nodes) - 1
        and all(v <= 1 for v in outd.values())
        and all(v <= 1 for v in ind.values())
        and sum(1 for n in nodes if ind.get(n, 0) == 0) == 1
    )
    return "LR" if simple_path else "TD"


def apply_direction(src: str) -> str:
    if re.search(r"%%\s*direction:\s*keep", src):
        return src
    d = flowchart_direction(src)
    if d is None:
        return src
    return HEADER_RE.sub(lambda m: f"{m.group(1)}flowchart {d}", src, count=1)


def _chrome() -> str | None:
    for cand in (os.environ.get("PUPPETEER_EXECUTABLE_PATH"), "google-chrome", "chromium",
                 "chromium-browser", "chrome",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if cand and (shutil.which(cand) or Path(cand).exists()):
            return shutil.which(cand) or cand
    return None  # let puppeteer use its own download


MERMAID_CONFIG = {
    "theme": "neutral",
    "layout": "elk",                 # orthogonal edge routing
    "htmlLabels": False,             # SVG <text>, which WeasyPrint can draw
    "flowchart": {"htmlLabels": False, "curve": "linear", "padding": 12},
    "elk": {"nodePlacementStrategy": "BRANDES_KOEPF", "mergeEdges": False},
    "themeVariables": {"fontFamily": "Charis SIL, serif", "fontSize": "14px"},
}


def render_mermaid(diagrams: list[str]) -> list[str]:
    if not diagrams:
        return []
    _node()
    mmdc = NODE_BIN / ("mmdc.cmd" if os.name == "nt" else "mmdc")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "config.json").write_text(json.dumps(MERMAID_CONFIG))
        pp = {"args": ["--no-sandbox", "--disable-gpu"]}
        if _chrome():
            pp["executablePath"] = _chrome()
        (t / "puppeteer.json").write_text(json.dumps(pp))
        faces = "\n".join(
            f'@font-face {{ font-family: "Charis SIL"; src: url("{f.as_uri()}"); '
            f'font-weight: {f.stem.split("-")[3]}; font-style: {f.stem.split("-")[4]}; }}'
            for f in sorted(FONTS.glob("charis-sil-latin-*.woff"))
        )
        (t / "fonts.css").write_text(faces)
        md = "\n\n".join(f"```mermaid\n{apply_direction(d)}\n```" for d in diagrams)
        (t / "in.md").write_text(md, encoding="utf-8")
        proc = subprocess.run(
            [str(mmdc), "-i", "in.md", "-o", "out.md", "-e", "svg", "-b", "transparent",
             "-c", "config.json", "-p", "puppeteer.json", "-C", "fonts.css", "-q"],
            cwd=t, capture_output=True, text=True,
        )
        if proc.returncode:
            raise RenderError("Mermaid failed:\n" + (proc.stderr or proc.stdout)[-2000:])
        out = []
        for i in range(1, len(diagrams) + 1):
            svg = (t / f"out-{i}.svg").read_text(encoding="utf-8")
            vb = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"', svg)
            # Natural size: 1 CSS px = 0.75 pt, so 14 px labels print at 10.5 pt.
            style = f"width:{float(vb.group(1)) * 0.75:.1f}pt" if vb else "width:100%"
            out.append(
                f'<figure class="diagram"><img alt="diagram" style="{style}" '
                f'src="{_data_uri(svg)}"></figure>'
            )
        return out


# --------------------------------------------------------------------------
# Substitution
# --------------------------------------------------------------------------

def substitute(html: str, maths_html: list[str], diagrams_html: list[str]) -> str:
    def block(kind, items):
        nonlocal html
        for i, frag in enumerate(items):
            tok = _token(kind, i)
            html, n = re.subn(rf"<p>\s*{tok}\s*</p>", lambda _: frag, html)
            if not n:
                html = html.replace(tok, frag)

    block("D", diagrams_html)
    block("M", maths_html)
    return html
