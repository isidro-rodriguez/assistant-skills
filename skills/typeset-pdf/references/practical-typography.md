# Practical Typography — rules and how this skill applies them

Source: Matthew Butterick, *Butterick's Practical Typography*
(<https://practicaltypography.com>). Rules are paraphrased here; read the
original for the reasoning. Key pages:
[typography in ten minutes](https://practicaltypography.com/typography-in-ten-minutes.html),
[summary of key rules](https://practicaltypography.com/summary-of-key-rules.html),
[page margins](https://practicaltypography.com/page-margins.html),
[headings](https://practicaltypography.com/headings.html),
[line spacing](https://practicaltypography.com/line-spacing.html),
[line length](https://practicaltypography.com/line-length.html).

## Body text (the four choices that matter most)

| Rule | Value | Implemented by |
|---|---|---|
| Point size (print) | 10–12 pt | `--body-size: 11pt`; `build_pdf.py --size` rejects values outside 10–12; `check_pdf.py size` |
| Line spacing | 120–145 % of the point size | `--leading: 1.32`; `--leading` limited to 1.20–1.45; `check_pdf.py leading` |
| Line length | 45–90 characters on average, spaces included | `--measure` (default 75); `build_pdf.py` calibrates the side margins on the document itself; `check_pdf.py measure` |
| Font | A professional font; never Times New Roman or Arial; avoid system and most free fonts | Bundled Charis SIL (Charter design); `--font` for licensed fonts; `check_pdf.py font` and `fallback` |

## Page layout

| Rule | Implemented by |
|---|---|
| Margins wider than 1″. Smaller type needs wider margins; aim for the character count, not a fixed width | Margins come from the target measure, with a minimum of 1″ (15 mm on A5) |
| Bottom margin about 0.25″ larger than the top, so the block looks centred | A4 25 mm top and 31 mm bottom; letter 1″ and 1.25″ |
| If left and right margins differ, make the difference at least 1″ | Symmetric margins by default |
| Leave a binding gutter for two-sided documents | Not by default. Add `@page :left/:right` margins through `--css` |

## Paragraphs and alignment

| Rule | Implemented by |
|---|---|
| Use a first-line indent of 1–4× the point size **or** 4–10 pt between paragraphs, never both | Default 0.6em ≈ 6.6 pt of space; `--indent` switches to a 1.5em indent with no space |
| Always hyphenate justified text | `text-align: justify` with `hyphens: auto`; `--lang` selects the dictionary |
| Use centred text sparingly | Only `h1` and `.subtitle` |
| Kerning always on | `font-kerning: normal`, with common ligatures enabled |
| Avoid widows and orphans | `orphans: 2; widows: 2` |

## Headings

| Rule | Implemented by |
|---|---|
| No more than three levels; two is better | Authoring rule; reports number `##`/`###`/`####` as three levels |
| Emphasise with space above and below first | Generous top and bottom margins |
| Bold rather than italic; smallest visible size increase | h2 is 1.15em bold; h3 is the same size and bold |
| Keep with the next paragraph; no hyphenation in headings | `break-after: avoid; hyphens: manual` |
| No all caps and no title case for long headings | Authoring rule: sentence case |

## Character-level rules

| Rule | Implemented by |
|---|---|
| Curly quotes; apostrophes point downward | Markdown `smarty` extension; `check_pdf.py quotes` |
| Feet and inch marks stay straight | Write them as `′` and `″`, or accept the `quotes` warning |
| Hyphen, en dash and em dash are different; never `--` as a dash | `smarty`: `--` becomes an en dash and `---` an em dash; `check_pdf.py dashes` |
| Ellipsis is one character | `smarty`: `...` becomes `…`; `check_pdf.py ellipsis` |
| One space between sentences; no runs of whitespace | `clean_html()` collapses spaces; `check_pdf.py spaces` |
| Bold or italic sparingly, never together | CSS forces `strong em` to plain bold |
| Never underline (except possibly web links) | `a`, `u` → no underline |
| All caps for less than one line, with 5–12 % letterspacing | `.caps { letter-spacing: 0.08em }` |
| Small caps only if the font has real ones | `.smallcaps` uses `font-variant-caps` (real small caps from OpenType) |
| Real ©, ™ and ® symbols | Authoring rule |
| Non-breaking space after § and ¶ | `clean_html()` |
| Ampersands sparingly | Authoring rule |
| One exclamation point in documents longer than three pages | `check_pdf.py exclaim` |
| Avoid monospaced fonts except for code | Monospace only in `code` and `pre` |

## Additions beyond the book

These are the maintainer's own choices, not Butterick's rules.

| Choice | Implemented by |
|---|---|
| Default measure of 75 characters, inside the 45–90 range | `--measure 75` |
| Dense tables may leave the text block, up to 15 mm from the paper edge | `mark_wide_tables()` adds `table.wide`; `--wide-tables` |
| LaTeX math as vector SVG | `renderers.py` with `render_math.cjs` (MathJax 4) |
| Mermaid flowcharts: orthogonal edges; horizontal for one chain of ≤ 4 nodes, vertical otherwise | `renderers.py` (`flowchart_direction`, ELK layout) |
| Reports: cover, contents with page numbers, headings numbered 1 / 1.1 / 1.1.1 (Butterick's *hierarchical headings*: tiered numbers, no roman numerals or letters) | `--doc report`: `report.py`, `assets/report.css`; `check_pdf.py --report` |
