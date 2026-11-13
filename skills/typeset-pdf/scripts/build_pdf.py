#!/usr/bin/env python3
"""Build a typographically sound PDF from Markdown or HTML (WeasyPrint).

Examples:
  python build_pdf.py report.md -o report.pdf
  python build_pdf.py report.md -o report.pdf --lang es --paper A4 --size 11
  python build_pdf.py page.html -o page.pdf --css extra.css --font "Equity OT"

Markdown is converted with smart punctuation (curly quotes, en/em dashes from
-- and ---, ellipsis from ...), tables, footnotes, attribute lists and fenced code.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"

# Page size → margins (top right bottom left). Side margins give ~60–70 chars
# per line at 11 pt (10 pt for A5); bottom is slightly larger than top.
PAPERS = {
    "A4": ("A4", "25mm 43mm 31mm 43mm"),
    "LETTER": ("letter", "1in 1.7in 1.25in 1.7in"),
    "A5": ("A5", "18mm 22mm 24mm 22mm"),
}

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


def build_css(args) -> str:
    css = bundled_font_faces() + (ASSETS / "base.css").read_text(encoding="utf-8")
    size, margins = PAPERS[args.paper.upper()]
    overrides = [f"@page {{ size: {size}; margin: {margins}; }}"]
    if args.size:
        overrides.append(f":root {{ --body-size: {args.size}pt; }}")
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help=".md or .html source")
    ap.add_argument("-o", "--output", required=True, help="output .pdf path")
    ap.add_argument("--lang", default="en", help="BCP-47 language (drives hyphenation and quotes). Default: en")
    ap.add_argument("--paper", default="A4", choices=["A4", "a4", "letter", "LETTER", "A5", "a5"])
    ap.add_argument("--size", type=float, help="body point size, 10–12 (default 11; 10 for A5)")
    ap.add_argument("--leading", type=float, help="line-height multiple, 1.20–1.45 (default 1.32)")
    ap.add_argument("--font", help="preferred body font family (must be installed or loaded via --css)")
    ap.add_argument("--css", action="append", help="extra stylesheet(s), applied after base.css")
    ap.add_argument("--indent", action="store_true", help="first-line indents instead of paragraph space")
    ap.add_argument("--title", help="PDF title metadata (default: first <h1>)")
    ap.add_argument("--author", default="", help="PDF author metadata")
    ap.add_argument("--no-page-numbers", action="store_true")
    ap.add_argument("--html-out", help="also write the intermediate HTML here (debugging)")
    args = ap.parse_args()

    if args.size is None and args.paper.upper() == "A5":
        args.size = 10
    if args.size is not None and not 10 <= args.size <= 12:
        sys.exit("--size must be between 10 and 12 pt (Practical Typography, print).")
    if args.leading is not None and not 1.2 <= args.leading <= 1.45:
        sys.exit("--leading must be between 1.20 and 1.45.")

    try:
        from weasyprint import HTML
    except ImportError:
        sys.exit("Missing dependency: pip install weasyprint")

    src = Path(args.input)
    text = src.read_text(encoding="utf-8")
    if src.suffix.lower() in {".md", ".markdown"}:
        body = md_to_html(text, args.lang)
    else:
        m = re.search(r"<body[^>]*>(.*)</body>", text, re.S | re.I)
        body = m.group(1) if m else text
    body = clean_html(body)

    title = args.title or first_heading(body) or src.stem
    template = (ASSETS / "template.html").read_text(encoding="utf-8")
    doc = template.format(
        lang=html.escape(args.lang),
        title=html.escape(title),
        author=html.escape(args.author),
        css=build_css(args),
        body_class="indent" if args.indent else "",
        content=body,
    )
    if args.html_out:
        Path(args.html_out).write_text(doc, encoding="utf-8")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=doc, base_url=str(src.parent.resolve())).write_pdf(out)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
