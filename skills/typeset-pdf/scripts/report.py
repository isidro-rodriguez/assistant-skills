"""Report layout for build_pdf.py (--doc report): cover, table of contents,
numbered headings, front matter in roman numerals and body from page 1.

Front matter: an optional YAML block at the top of the Markdown file:

    ---
    title: Quarterly Site Safety Report
    subtitle: North Harbour Housing Block
    author: Isidro Rodríguez
    organization: Example Construction Ltd.
    date: 13 November 2026
    version: "1.0"
    logo: images/logo.svg        # relative to the Markdown file
    ---

Heading levels (Practical Typography: tiered numbers, at most three levels):
    #     report title (used for the cover if `title` is missing; removed from the body)
    ##    1        numbered, in the table of contents
    ###   1.1      numbered, in the table of contents
    ####  1.1.1    numbered, not in the table of contents
"""
from __future__ import annotations

import html
import re

FIELDS = ("title", "subtitle", "author", "organization", "date", "version", "logo")

TOC_TITLE = {"es": "Índice", "en": "Contents", "fr": "Sommaire", "de": "Inhalt",
             "pt": "Índice", "it": "Indice", "ca": "Índex"}
VERSION_LABEL = {"es": "Versión", "en": "Version", "fr": "Version", "de": "Version",
                 "pt": "Versão", "it": "Versione", "ca": "Versió"}


def split_front_matter(text: str) -> tuple[dict, str]:
    """Return (metadata, markdown_without_front_matter)."""
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", text, re.S)
    if not m:
        return {}, text
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except ImportError:  # minimal "key: value" fallback
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip("\"'")
    if not isinstance(meta, dict):
        return {}, text
    unknown = set(meta) - set(FIELDS)
    if unknown:
        raise ValueError(f"Unknown front-matter fields: {sorted(unknown)}. Allowed: {', '.join(FIELDS)}")
    return {k: str(v) for k, v in meta.items() if v is not None}, text[m.end():]


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _slug(text: str, used: set) -> str:
    base = re.sub(r"[^\w]+", "-", _strip_tags(text).lower(), flags=re.U).strip("-") or "section"
    slug, n = base, 1
    while slug in used:
        n += 1
        slug = f"{base}-{n}"
    used.add(slug)
    return slug


def number_headings(body: str) -> tuple[str, list[tuple[int, str, str, str]]]:
    """Number h2–h4 as 1 / 1.1 / 1.1.1. Return (html, toc_entries)."""
    counters = [0, 0, 0]
    used = set(re.findall(r'\sid="([^"]+)"', body))
    toc = []

    def visit(m):
        level = int(m.group(1)) - 2          # h2 → 0, h3 → 1, h4 → 2
        attrs, inner = m.group(2), m.group(3)
        counters[level] += 1
        for i in range(level + 1, 3):
            counters[i] = 0
        num = ".".join(str(c) for c in counters[: level + 1])
        idm = re.search(r'\sid="([^"]+)"', attrs)
        if idm:
            hid = idm.group(1)
        else:
            hid = _slug(inner, used)
            attrs += f' id="{hid}"'
        if level < 2:
            toc.append((level, num, inner, hid))
        return (f'<h{level + 2}{attrs}><span class="secnum">{num}</span>'
                f'<span class="sectitle">{inner}</span></h{level + 2}>')

    body = re.sub(r"<h([234])([^>]*)>(.*?)</h\1>", visit, body, flags=re.S)
    return body, toc


def build(body: str, meta: dict, lang: str, base_title: str | None) -> tuple[str, str]:
    """Return (full_body_html, title)."""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    title = meta.get("title") or (_strip_tags(h1.group(1)).strip() if h1 else None) or base_title or "Report"
    if h1:
        body = body[: h1.start()] + body[h1.end():]
    # A subtitle paragraph right after the h1 moves to the cover too.
    sub = re.match(r'\s*<p class="subtitle">(.*?)</p>', body, re.S)
    subtitle = meta.get("subtitle")
    if sub:
        subtitle = subtitle or _strip_tags(sub.group(1)).strip()
        body = body[sub.end():]

    body, toc = number_headings(body)
    lang2 = lang.split("-")[0].lower()

    e = html.escape
    cover = ['<section class="cover">']
    if meta.get("logo"):
        cover.append(f'<img class="cover-logo" src="{e(meta["logo"])}" alt="">')
    if meta.get("organization"):
        cover.append(f'<p class="cover-org">{e(meta["organization"])}</p>')
    cover.append(f'<h1 class="cover-title">{e(title)}</h1>')
    if subtitle:
        cover.append(f'<p class="cover-subtitle">{e(subtitle)}</p>')
    details = []
    if meta.get("author"):
        details.append(f'<p class="cover-author">{e(meta["author"])}</p>')
    line = " · ".join(x for x in (
        e(meta["date"]) if meta.get("date") else "",
        f'{VERSION_LABEL.get(lang2, "Version")} {e(meta["version"])}' if meta.get("version") else "",
    ) if x)
    if line:
        details.append(f'<p class="cover-meta">{line}</p>')
    if details:
        cover.append('<div class="cover-details">' + "".join(details) + "</div>")
    cover.append("</section>")

    items = []
    for level, num, inner, hid in toc:
        items.append(
            f'<li class="toc-l{level + 1}"><a href="#{hid}">'
            f'<span class="toc-num">{num}</span><span class="toc-text">{_strip_tags(inner)}</span></a></li>'
        )
    front = (
        '<section class="front"><nav class="toc">'
        f'<h2 class="toc-title">{TOC_TITLE.get(lang2, "Contents")}</h2>'
        f'<ol>{"".join(items)}</ol></nav></section>'
    )
    return "".join(cover) + front + f'<div class="main">{body}</div>', title
