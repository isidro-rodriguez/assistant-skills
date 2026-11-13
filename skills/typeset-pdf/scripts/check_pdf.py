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
With --report also:
  cover       page 1 has no page number                                          FAIL
  toc         table of contents present; every entry points to the page where
              its numbered heading actually is                                   FAIL
  numbering   headings numbered 1 / 1.1 / 1.1.1 in sequence, ≤ 3 levels           FAIL
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

    # Measure: lines that fill ≥ 90 % of the widest body line (i.e. justified/full lines),
    # ignoring sparse lines such as table-of-contents entries with leaders.
    widths = [l[3] - l[2] for l in body]
    max_w = max(widths) if widths else 0
    full = [l for l in body if (l[3] - l[2]) >= 0.9 * max_w]
    if full:
        dens = sorted(len(l[5]) / (l[3] - l[2]) for l in full)
        med = dens[len(dens) // 2]
        full = [l for l in full if len(l[5]) / (l[3] - l[2]) >= 0.75 * med]
    measure = st.mean(len(l[5]) for l in full) if full else 0

    # Leading: distance between consecutive body lines on the same page and left edge.
    gaps = []
    for a, b in zip(body, body[1:]):
        if a[0] == b[0] and abs(a[2] - b[2]) < 30:
            d = b[1] - a[1]
            if 0 < d < 2 * body_size:
                gaps.append(d)
    # Most common gap (robust against paragraph and list spacing).
    leading = (Counter(round(g, 1) for g in gaps).most_common(1)[0][0] / body_size) if gaps and body_size else 0

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
    if len(gaps) < 5:
        add("leading", "WARN", "n/a (too little text)", "120–145 %")
    else:
        add("leading", "PASS" if 1.18 <= leading <= 1.47 else "FAIL", f"{leading:.0%}", "120–145 %")
    if len(full) < 3:
        add("measure", "WARN", "n/a (too little text)", "45–90 chars/line", None)
    else:
        add("measure", "PASS" if 45 <= measure <= 90 else "FAIL", f"{measure:.0f} chars",
            "45–90 chars/line", measure)

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

    return {"file": path, "pages": n_pages, "fonts": dict(fonts.most_common(6)), "results": results,
            "_lines": lines, "_body_size": body_size}


ROMAN = re.compile(r"^[ivxlcdm]+$")
NUM_HEAD = re.compile(r"^(\d+(?:\.\d+){0,2})\s+(\S.*)$")
TOC_ENTRY = re.compile(r"^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)$")


def report_checks(path: str, rep: dict) -> None:
    import pdfplumber

    labels, page_lines = [], []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text_lines()
            page_lines.append(lines)
            foot = [l for l in lines if l["top"] > page.height * 0.88]
            labels.append(foot[-1]["text"].strip() if foot else "")
    results = rep["results"]

    def add(check, ok, value, rule):
        results.append({"check": check, "status": "PASS" if ok else "FAIL", "value": value,
                        "rule": rule, "raw": None})

    add("cover", labels[0] == "" or not (labels[0].isdigit() or ROMAN.match(labels[0])),
        labels[0] or "no number", "Cover page carries no page number")

    # Pages of the body: footer label is an arabic number.
    by_label = {lab: i for i, lab in enumerate(labels) if lab.isdigit()}
    front = [i for i, lab in enumerate(labels) if ROMAN.match(lab)]

    entries = []
    for i in front:
        for l in page_lines[i]:
            m = TOC_ENTRY.match(l["text"].strip())
            if m:
                entries.append(m.groups())
    if not entries:
        add("toc", False, "not found", "Table of contents with page numbers")
    else:
        bad = []
        for num, text, pg in entries:
            idx = by_label.get(pg)
            words = " ".join(text.split()[:3])
            hit = idx is not None and any(
                l["text"].strip().startswith(num + " ") and words in " ".join(l["text"].split())
                for l in page_lines[idx])
            if not hit:
                bad.append(f"{num}→p.{pg}")
        add("toc", not bad, f"{len(entries)} entries" + (f", wrong: {', '.join(bad[:5])}" if bad else ""),
            "Every contents entry points to its heading's page")

    # Numbering: bold numbered headings in the body, in sequence.
    nums = []
    with pdfplumber.open(path) as pdf:
        for i in sorted(by_label.values()):
            for l in pdf.pages[i].extract_text_lines(return_chars=True):
                m = NUM_HEAD.match(l["text"].strip())
                if m and all("Bold" in c["fontname"] for c in l["chars"][: len(m.group(1))]):
                    nums.append(m.group(1))
    expected, seq_ok = [0, 0, 0], True
    for n in nums:
        parts = [int(x) for x in n.split(".")]
        lvl = len(parts) - 1
        expected[lvl] += 1
        for j in range(lvl + 1, 3):
            expected[j] = 0
        if parts != expected[: lvl + 1]:
            seq_ok = False
            break
    add("numbering", bool(nums) and seq_ok, f"{len(nums)} headings" + ("" if seq_ok else f", break at {n}"),
        "Headings numbered 1 / 1.1 / 1.1.1 in sequence")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--report", action="store_true", help="also check cover, contents and numbering")
    args = ap.parse_args()

    report = analyse(args.pdf)
    if args.report:
        report_checks(args.pdf, report)
    report.pop("_lines", None)
    report.pop("_body_size", None)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{report['file']} — {report['pages']} page(s)")
        for r in report["results"]:
            print(f"  [{r['status']:4}] {r['check']:9} {str(r['value']):>18}   ({r['rule']})")
    return 1 if any(r["status"] == "FAIL" for r in report["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())
