#!/usr/bin/env python3
"""Measure a PDF against Practical Typography's body-text rules.

Usage: python check_pdf.py file.pdf [--json]

Checks (FAIL = must fix, WARN = review):
  font        body font is not Times New Roman / Arial / Helvetica / a fallback  FAIL
  fallback    some glyphs rendered in a fallback system font                     WARN
  size        body point size 10–12                                              FAIL
  leading     line spacing 120–145 % of point size                               FAIL
  measure     average characters per full line 45–90                             FAIL
  quotes      straight quotes ' " in body text (should be curly)                 WARN
  dashes      "--" or " - " used as a dash                                       WARN
  ellipsis    "..." instead of …                                                 WARN
  spaces      double spaces                                                      WARN
  exclaim     more than one "!" in a document longer than 3 pages                WARN
Exit code 1 if any FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from collections import Counter

BAD_FONTS = re.compile(r"times|arial|helvetica|liberation|dejavu|freeserif|freesans|nimbus", re.I)
MONO = re.compile(r"mono|courier|code|consol|triplicate", re.I)


def base_font(name: str) -> str:
    return name.split("+", 1)[-1]


def analyse(path: str) -> dict:
    try:
        import pdfplumber
    except ImportError:
        sys.exit("Missing dependency: pip install pdfplumber")

    sizes, fonts = Counter(), Counter()
    lines = []          # (page, top, x0, x1, size, text)
    full_text = []
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            for ch in page.chars:
                if ch["text"].strip():
                    sizes[round(ch["size"], 1)] += 1
                    fonts[base_font(ch["fontname"])] += 1
            for ln in page.extract_text_lines(return_chars=True):
                chars = [c for c in ln["chars"] if not MONO.search(c["fontname"])]
                if not chars:
                    continue
                size = Counter(round(c["size"], 1) for c in chars).most_common(1)[0][0]
                lines.append((i, ln["top"], ln["x0"], ln["x1"], size, ln["text"]))
            full_text.append(page.extract_text() or "")

    body_size = sizes.most_common(1)[0][0] if sizes else 0
    body_fonts = [f for f, _ in fonts.most_common() if not MONO.search(f)]
    body_font = body_fonts[0] if body_fonts else "?"

    body = [l for l in lines if abs(l[4] - body_size) < 0.3]

    # Measure: lines that fill ≥ 90 % of the widest body line (i.e. justified/full lines).
    widths = [l[3] - l[2] for l in body]
    max_w = max(widths) if widths else 0
    full = [l for l in body if (l[3] - l[2]) >= 0.9 * max_w]
    measure = st.mean(len(l[5]) for l in full) if full else 0

    # Leading: distance between consecutive body lines on the same page and left edge.
    gaps = []
    for a, b in zip(body, body[1:]):
        if a[0] == b[0] and abs(a[2] - b[2]) < 30:
            d = b[1] - a[1]
            if 0 < d < 2 * body_size:
                gaps.append(d)
    leading = (st.median(gaps) / body_size) if gaps and body_size else 0

    text = "\n".join(full_text)
    body_text = "\n".join(l[5] for l in body)

    results = []

    def add(check, status, value, rule, raw=None):
        results.append({"check": check, "status": status, "value": value, "rule": rule, "raw": raw})

    add("font", "FAIL" if BAD_FONTS.search(body_font) else "PASS", body_font,
        "No Times New Roman/Arial or fallback fonts")
    stray = sorted({f for f in fonts if BAD_FONTS.search(f) and f != body_font and not MONO.search(f)})
    add("fallback", "WARN" if stray else "PASS", ", ".join(stray) or "none",
        "No glyphs falling back to system fonts")
    add("size","PASS" if 10 <= body_size <= 12 else "FAIL", f"{body_size} pt", "10–12 pt")
    add("leading", "PASS" if 1.18 <= leading <= 1.47 else "FAIL", f"{leading:.0%}", "120–145 %")
    add("measure", "PASS" if 45 <= measure <= 90 else "FAIL", f"{measure:.0f} chars", "45–90 chars/line", measure)

    straight = len(re.findall(r"[\"']", body_text))
    add("quotes", "WARN" if straight else "PASS", straight, "Curly quotes, not straight")
    dashes = len(re.findall(r"--|\s-\s", body_text))
    add("dashes", "WARN" if dashes else "PASS", dashes, "Use – or —, not -- or ' - '")
    ell = text.count("...")
    add("ellipsis", "WARN" if ell else "PASS", ell, "Use the … character")
    dbl = len(re.findall(r"\S  +\S", body_text))
    add("spaces", "WARN" if dbl else "PASS", dbl, "One space between sentences")
    excl = text.count("!")
    add("exclaim", "WARN" if n_pages > 3 and excl > 1 else "PASS", excl,
        "One exclamation point per long document")

    return {"file": path, "pages": n_pages, "fonts": dict(fonts.most_common(6)), "results": results}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    report = analyse(args.pdf)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{report['file']} — {report['pages']} page(s)")
        for r in report["results"]:
            print(f"  [{r['status']:4}] {r['check']:9} {str(r['value']):>18}   ({r['rule']})")
    return 1 if any(r["status"] == "FAIL" for r in report["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())
