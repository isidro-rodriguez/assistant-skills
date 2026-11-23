---
name: typeset-pdf
description: Produce a well-typeset PDF (memo, letter, handout, article, or a formal report with cover, table of contents and numbered headings) from Markdown or HTML, following Matthew Butterick's Practical Typography rules — 10–12 pt body, 120–145 % line spacing, 75 characters per line, good font, curly quotes, real dashes — with LaTeX formulas, Mermaid flowcharts and wide tables, and verify the result automatically. Use when the user asks to create, generate, export, typeset or "make a nice PDF" of a document, or to convert Markdown/HTML/text into a print-ready PDF. Not for filling, merging or editing existing PDFs.
license: MIT
compatibility: Python 3.13+ with weasyprint, markdown, pdfplumber. For LaTeX math and Mermaid diagrams, Node.js 18+ plus `npm install` in scripts/ and Chrome/Chromium (mermaid-cli). Optional pdftoppm (poppler-utils) for the visual check. Works in any agent that can run shell commands.
metadata:
  version: "0.3.3"
  author: isidro-rodriguez
  source: https://practicaltypography.com
---

# Typeset PDF

Turns content into a PDF whose body text meets Practical Typography's key
rules, and proves it with a measurement script before delivery.

## Inputs

| Input | Required | Default if missing |
|---|---|---|
| Content (text, Markdown, HTML, notes to write up) | yes | Ask for it |
| Language of the text | no | Infer from the content; `en` if unclear |
| Paper size | no | `A4` (`letter` if the user is in the US/Canada) |
| Body font | no | Bundled **Charis SIL** (Charter-derived, OFL). Use a licensed font only if the user names one that is installed or supplies the files |
| Paragraph style | no | Space between paragraphs (`--indent` for first-line indents) |
| Document type | no | `note` for casual documents (memo, letter, handout). Use `report` when the user asks for a report/informe, or wants a cover, contents or numbered sections |
| Title / author metadata | no | YAML front matter, else first `# heading` / empty |
| Report cover data | report only | Whatever the user gave: `title`, `subtitle`, `author`, `organization`, `date`, `version`, `logo` |

Ask only if the content itself is missing. Everything else has a default.

When the user asks for example, sample or test sections ("escribe unos apartados de
ejemplo", "a test report"), fill them with lorem ipsum, not with invented subject matter:
made-up incidents, faults or findings read as real and distract from the layout being
reviewed.

### Document types

| | `--doc note` (default) | `--doc report` |
|---|---|---|
| First page | Title (`#`) at the top of the text | Cover page, unnumbered |
| Contents | none | Separate page: `##` and `###` entries with page numbers |
| Headings | Unnumbered | Numbered: `##` 1, `###` 1.1, `####` 1.1.1 |
| Page numbers | Arabic from page 2 | Roman for front matter, arabic from 1 in the body; title in the running head |

For reports, read `references/report.md` before writing the source.

## Procedure

1. **Install dependencies** if needed:
   `pip install weasyprint markdown pdfplumber` (add `--break-system-packages` on managed Pythons).
   Only if the document has math or diagrams, run `npm install` in `scripts/` once.
   Mermaid uses an installed Chrome/Chromium; set `PUPPETEER_EXECUTABLE_PATH` if it isn't found.
2. **Write the source as Markdown** (`<name>.md`). Follow the authoring rules
   below; they cover what CSS can't fix.
3. **Build:**
   ```bash
   python scripts/build_pdf.py <name>.md -o <name>.pdf --doc <note|report> --lang <lang> --paper <A4|letter|A5>
   ```
   Options: `--measure 45–90` (default 75), `--size 10–12`, `--leading 1.20–1.45`,
   `--wide-tables auto|all|none`, `--font "Family"`, `--css extra.css`, `--indent`,
   `--title`, `--author`, `--no-page-numbers`. The script refuses out-of-range values.
   It calibrates the side margins on the real document until full lines average
   `--measure` characters; the point size never changes. On A5 the margins hit
   their 15 mm minimum first, so the line comes out slightly shorter, and the
   script says so.
4. **Measure:**
   ```bash
   python scripts/check_pdf.py <name>.pdf            # add --report for reports
   ```
   With `--report`, the script also checks that the cover has no page number,
   that every contents entry points to the right page, and that the numbering
   runs 1 / 1.1 / 1.1.1 in sequence. In a very short text, `leading` and
   `measure` show `n/a` as a `WARN`, which is fine.
   Every `FAIL` must be fixed (change options or CSS, rebuild). Resolve each
   `WARN` in the source, or tell the user why it stays.
5. **Look at it:** `pdftoppm -r 80 -png <name>.pdf page` and view every page
   (or page 1 plus every page with a table, figure or diagram in long
   documents). Check for headings stranded at the bottom of a page,
   overflowing tables and awkward breaks.
   **Large blank gaps:** a diagram, display formula or table that doesn't fit
   the space left on a page moves whole to the next one, leaving a gap. This
   can't be fixed in CSS, so fix it in the source and rebuild. Move the block
   one or two paragraphs later (or earlier), so the prose fills the gap; the
   text should still say "the diagram below/above". If moving it would break
   the argument, simplify the diagram, for example by splitting it in two. A
   gap of more than about a third of a page is worth fixing; a smaller one
   isn't.
6. **Deliver** the PDF. Keep the `.md` source next to it so it can be rebuilt.

### Authoring rules (apply while writing the Markdown)

The stylesheet fixes most typography on its own. These rules cover what only
the writer can decide, with the reason for each so you can judge edge cases.

- **Headings:** at most three levels (`#` title, `##`, `###`; `####` only in
  reports). Each extra level is harder to tell apart in print, and readers stop
  following the hierarchy. Use sentence case: all caps and title case are
  slower to read. Don't add bold or italic inside headings, because they are
  already bold.
- **Emphasis:** bold *or* italic, sparingly, never both. Emphasis only works
  by contrast, and every extra mark weakens the others. Never underline,
  because underlining is a typewriter substitute for italic and cuts through
  descenders.
- **Punctuation:** type plain `"`, `'`, `--` (en dash, for ranges such as
  2019--2026), `---` (em dash, for a break in a sentence) and `...`. The build
  converts them for `--lang` (« » for Spanish and French, „ “ for German).
  Typing them plainly keeps the source portable and the conversion consistent.
  Write `©`, `™` and `®` as the real characters.
- **Spacing:** one space between sentences. Don't use blank lines or spaces
  for layout: HTML collapses them, so the result is unpredictable. Use
  `<div class="page-break"></div>` or CSS instead.
- **Exclamation points and caps:** at most one exclamation point in a long
  document, and all caps for less than a line. Both read as shouting; a run
  of caps also loses word shapes. Put acronym runs in `<span class="caps">`
  to get the letterspacing caps need.
- **Centred text:** only the title and subtitle (`<p class="subtitle">…</p>`).
  Ragged left edges make longer text hard to scan.
- **Tables:** keep them simple and right-align numeric columns (`---:`) so
  digits line up. A dense table (7+ columns, or naturally wider than the line)
  widens into the margins automatically, up to 15 mm from the paper edge, so
  its text stays legible instead of shrinking. Body text keeps its measure.
- **Math:** LaTeX in `$…$` or `\(…\)` for inline formulas, `$$…$$` or
  `\[…\]` for display formulas (amsmath available). Write `\$` for a literal
  dollar. A LaTeX error stops the build and names the formula, so a broken
  formula never reaches the PDF unnoticed.
- **Diagrams:** put flowcharts in fenced ```` ```mermaid ```` blocks. Edges are
  orthogonal (ELK layout), and the build sets the direction so diagrams read
  the same way across documents: **horizontal (LR)** for a single chain of at
  most 4 nodes, **vertical (TD)** for anything else (branches, joins, loops,
  subgraphs, 5+ nodes). Use `%% direction: keep` only if the user asks for a
  specific direction. Other Mermaid types (sequence, Gantt…) render as
  written. Keep labels short: diagrams print at natural size (labels ≈ 10.5 pt)
  and shrink only to fit the text width.
- **Lists:** only for genuine series. Bulleted fragments in place of prose
  hide how the ideas connect.

## Output

- `<name>.pdf`: A4 by default, body in Charis SIL 11 pt at 132 % line spacing,
  75 ± 2 characters per line, justified with hyphenation, page numbers from
  page 2, and title and author metadata set. Formulas and diagrams are vector
  SVG, and dense tables span the page.
- Reports also get a cover, a contents page (roman numbering) and numbered
  headings, with the body starting at page 1.
- `<name>.md`: the source, kept for rebuilds.
- A one-line report to the user with the `check_pdf.py` result (size, leading, measure).

## Verification

- [ ] `check_pdf.py` exits 0 (no `FAIL`): body 10–12 pt, line spacing 120–145 %, 45–90 characters per line, no Times New Roman, Arial or fallback body font.
- [ ] Every `WARN` is resolved or explained (straight quotes, `--`, `...`, double spaces, fallback glyphs, too many exclamation points).
- [ ] Page images reviewed: no orphaned headings, no table overflow, no text running into the margins.
- [ ] Reports: `check_pdf.py --report` passes `cover`, `toc` and `numbering`; the cover shows the title and any metadata provided.
- [ ] Every formula is rendered (no raw LaTeX visible) and every diagram follows the direction rule (single chain of ≤ 4 nodes horizontal, otherwise vertical).
- [ ] Language passed with `--lang` matches the text, so hyphenation and quotes are correct.
- [ ] No bold and italic together, no underlining, no more than three heading levels.

## References

- `references/report.md` covers front matter fields, heading levels and what
  goes on the cover. Read it for any report.
- `references/practical-typography.md` lists every rule and shows how this skill
  implements it. Read it when you customise the CSS or a check fails.
- `assets/base.css` is the stylesheet. Override it with `--css` rather than
  editing it for a single document.
- `assets/fonts/OFL-CharisSIL.txt` is the font licence.
