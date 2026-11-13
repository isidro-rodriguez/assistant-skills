#!/usr/bin/env python3
"""Build a typographically sound PDF from Markdown or HTML (WeasyPrint).

Examples:
  python build_pdf.py report.md -o report.pdf
  python build_pdf.py report.md -o report.pdf --lang es --paper A4 --size 11
  python build_pdf.py page.html -o page.pdf --css extra.css --font "Equity OT"

Markdown is converted with smart punctuation (curly quotes, en/em dashes from
-- and ---, ellipsis from ...), tables, footnotes, attribute lists and fenced code.

Also:
  * Line length is calibrated on the real document to --measure characters per
    line (default 75) by adjusting the side margins; the point size never changes.
  * Dense tables (too wide for the text block) widen into the margins.
  * LaTeX math ($…$, $$…$$, \\(…\\), \\[…\\]) and ```mermaid diagrams are
    rendered to SVG (needs Node.js and `npm install` in this folder).
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
sys.path.insert(0, str(HERE))

import renderers  # noqa: E402

# Paper → (CSS size, page width mm, top mm, bottom mm, minimum side margin mm).
# Bottom is ~6 mm larger than top so the text block looks optically centred.
# Minimum side margin: 1 inch (Practical Typography), 15 mm on A5.
PAPERS = {
    "A4": ("A4", 210.0, 25.0, 31.0, 25.4),
    "LETTER": ("letter", 215.9, 25.4, 31.75, 25.4),
    "A5": ("A5", 148.0, 18.0, 24.0, 15.0),
}
TABLE_EDGE_MM = 15.0      # wide tables stop this far from the paper edge
CHAR_WIDTH_EM = 0.47      # first guess for average character width (calibrated later)

# Language-specific quotation marks for the smarty extension.
QUOTES = {
    "es": {"left-double-quote": "&laquo;", "right-double-quote": "&raquo;"},
    "fr": {"left-double-quote": "&laquo;&#8239;", "right-double-quote": "&#8239;&raquo;"},
    "de": {"left-double-quote": "&bdquo;", "right-double-quote": "&ldquo;",
           "left-single-quote": "&sbquo;", "right-single-quote": "&lsquo;"},
}


def md_to_html(text: str, lang: str) -> str:
    try:
        import markdown
    except ImportError:
        sys.exit("Missing dependency: pip install markdown")
    smarty_cfg = {"substitutions": QUOTES.get(lang, {})}
    return markdown.markdown(
        text,
        extensions=["extra", "smarty", "sane_lists", "toc"],
        extension_configs={"smarty": smarty_cfg},
        output_format="html",
    )


def clean_html(body: str) -> str:
    # Non-breaking space after section and paragraph marks.
    body = re.sub(r"([§¶])\s+", "\\1\u00a0", body)
    # Collapse runs of spaces in text (outside <pre>, handled loosely).
    parts = re.split(r"(<pre.*?</pre>)", body, flags=re.S)
    parts = [p if p.startswith("<pre") else re.sub(r"[ \t]{2,}", " ", p) for p in parts]
    return "".join(parts)


def first_heading(body: str) -> str | None:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None


def bundled_font_faces() -> str:
    """@font-face rules for the fonts shipped in assets/fonts (absolute file URIs)."""
    rules = []
    for weight in (400, 700):
        for style in ("normal", "italic"):
            f = ASSETS / "fonts" / f"charis-sil-latin-{weight}-{style}.woff"
            if f.exists():
                rules.append(
                    f'@font-face {{ font-family: "Charis SIL"; src: url("{f.as_uri()}") format("woff"); '
                    f"font-weight: {weight}; font-style: {style}; }}"
                )
    return "\n".join(rules) + "\n"


def geometry(args, text_mm: float | None = None) -> dict:
    size, page_w, top, bottom, min_side = PAPERS[args.paper.upper()]
    if text_mm is None:  # first estimate from the target measure
        text_mm = args.measure * CHAR_WIDTH_EM * args.size * 0.3528
    side = (page_w - text_mm) / 2
    clamped = side < min_side
    if clamped:
        side = min_side
        text_mm = page_w - 2 * side
    return {"size": size, "page_w": page_w, "top": top, "bottom": bottom,
            "side": side, "text_mm": text_mm, "clamped": clamped}


def build_css(args, geo: dict) -> str:
    css = bundled_font_faces() + (ASSETS / "base.css").read_text(encoding="utf-8")
    bleed = max(0.0, geo["side"] - TABLE_EDGE_MM)
    overrides = [
        f"@page {{ size: {geo['size']}; margin: {geo['top']}mm {geo['side']:.2f}mm "
        f"{geo['bottom']}mm {geo['side']:.2f}mm; }}",
        f":root {{ --body-size: {args.size}pt; }}",
        f"table.wide {{ width: {geo['text_mm'] + 2 * bleed:.2f}mm; "
        f"margin-left: -{bleed:.2f}mm; margin-right: -{bleed:.2f}mm; }}",
    ]
    if args.leading:
        overrides.append(f":root {{ --leading: {args.leading}; }}")
    if args.font:
        overrides.append(
            f':root {{ --body-font: "{args.font}", "Charis SIL", serif; }}'
        )
    if args.no_page_numbers:
        overrides.append("@page { @bottom-center { content: none; } }")
    css += "\n/* --- build overrides --- */\n" + "\n".join(overrides) + "\n"
    for extra in args.css or []:
        css += f"\n/* --- {extra} --- */\n" + Path(extra).read_text(encoding="utf-8")
    return css


def _cell_text(cell: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()


def mark_wide_tables(body: str, measure: int, mode: str) -> str:
    """Add class="wide" to tables whose natural width exceeds the text block."""
    if mode == "none":
        return body

    def visit(m):
        table = m.group(0)
        if mode == "all":
            wide = True
        else:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
            widths: list[int] = []
            for row in rows:
                cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)
                for i, c in enumerate(cells):
                    # Longest word decides the minimum; full text decides the natural width.
                    n = len(_cell_text(c))
                    if i >= len(widths):
                        widths.append(n)
                    else:
                        widths[i] = max(widths[i], n)
            natural = sum(w + 3 for w in widths)  # + padding per column
            wide = natural > measure * 1.05 or len(widths) >= 7
        if not wide:
            return table
        if re.match(r"<table[^>]*class=", table):
            return re.sub(r'class="', 'class="wide ', table, count=1)
        return table.replace("<table", '<table class="wide"', 1)

    return re.sub(r"<table\b.*?</table>", visit, body, flags=re.S)


def render(doc_html: str, base_url: str):
    from weasyprint import HTML
    return HTML(string=doc_html, base_url=base_url).write_pdf()


def measured_chars(pdf_bytes: bytes) -> float:
    from check_pdf import analyse
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    try:
        rep = analyse(path)
        return next(r["raw"] for r in rep["results"] if r["check"] == "measure")
    finally:
        Path(path).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help=".md or .html source")
    ap.add_argument("-o", "--output", required=True, help="output .pdf path")
    ap.add_argument("--lang", default="en", help="BCP-47 language (drives hyphenation and quotes). Default: en")
    ap.add_argument("--paper", default="A4", choices=["A4", "a4", "letter", "LETTER", "A5", "a5"])
    ap.add_argument("--size", type=float, help="body point size, 10–12 (default 11; 10 for A5)")
    ap.add_argument("--leading", type=float, help="line-height multiple, 1.20–1.45 (default 1.32)")
    ap.add_argument("--measure", type=int, default=75,
                    help="target average characters per line, 45–90 (default 75)")
    ap.add_argument("--wide-tables", default="auto", choices=["auto", "all", "none"],
                    help="widen dense tables into the margins (default auto)")
    ap.add_argument("--font", help="preferred body font family (must be installed or loaded via --css)")
    ap.add_argument("--css", action="append", help="extra stylesheet(s), applied after base.css")
    ap.add_argument("--indent", action="store_true", help="first-line indents instead of paragraph space")
    ap.add_argument("--title", help="PDF title metadata (default: first <h1>)")
    ap.add_argument("--author", default="", help="PDF author metadata")
    ap.add_argument("--no-page-numbers", action="store_true")
    ap.add_argument("--html-out", help="also write the intermediate HTML here (debugging)")
    args = ap.parse_args()

    if args.size is None:
        args.size = 10.0 if args.paper.upper() == "A5" else 11.0
    if not 10 <= args.size <= 12:
        sys.exit("--size must be between 10 and 12 pt (Practical Typography, print).")
    if args.leading is not None and not 1.2 <= args.leading <= 1.45:
        sys.exit("--leading must be between 1.20 and 1.45.")
    if not 45 <= args.measure <= 90:
        sys.exit("--measure must be between 45 and 90 characters per line.")

    try:
        import weasyprint  # noqa: F401
    except ImportError:
        sys.exit("Missing dependency: pip install weasyprint")

    src = Path(args.input)
    text = src.read_text(encoding="utf-8")

    # Math and diagrams are pulled out before Markdown sees them.
    text, maths, diagrams = renderers.extract(text)
    try:
        maths_html = renderers.render_math(maths)
        diagrams_html = renderers.render_mermaid(diagrams)
    except renderers.RenderError as e:
        sys.exit(str(e))

    if src.suffix.lower() in {".md", ".markdown"}:
        body = md_to_html(text, args.lang)
    else:
        m = re.search(r"<body[^>]*>(.*)</body>", text, re.S | re.I)
        body = m.group(1) if m else text
    body = clean_html(body)
    body = renderers.substitute(body, maths_html, diagrams_html)
    body = mark_wide_tables(body, args.measure, args.wide_tables)

    title = args.title or first_heading(body) or src.stem
    template = (ASSETS / "template.html").read_text(encoding="utf-8")

    def assemble(geo):
        return template.format(
            lang=html.escape(args.lang),
            title=html.escape(title),
            author=html.escape(args.author),
            css=build_css(args, geo),
            body_class="indent" if args.indent else "",
            content=body,
        )

    base_url = str(src.parent.resolve())
    geo = geometry(args)
    pdf = render(assemble(geo), base_url)

    # Calibrate the text width on the real document so the average full line
    # hits the target measure. Point size is never touched.
    for _ in range(3):
        got = measured_chars(pdf)
        if not got or abs(got - args.measure) <= 1.5 or geo["clamped"]:
            break
        geo = geometry(args, geo["text_mm"] * args.measure / got)
        pdf = render(assemble(geo), base_url)

    if args.html_out:
        Path(args.html_out).write_text(assemble(geo), encoding="utf-8")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pdf)

    got = measured_chars(pdf)
    note = " (side margins at their minimum; use a larger paper or smaller --measure)" if geo["clamped"] else ""
    print(f"Wrote {out} — text block {geo['text_mm']:.0f} mm, side margins {geo['side']:.1f} mm, "
          f"~{got:.0f} chars/line (target {args.measure}){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
