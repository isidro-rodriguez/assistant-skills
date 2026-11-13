---
name: typeset-pdf
description: Produce a well-typeset PDF (report, memo, letter, handout, article) from Markdown or HTML, following Matthew Butterick's Practical Typography rules — 10–12 pt body, 120–145 % line spacing, 45–90 characters per line, good font, curly quotes, real dashes — and verify the result automatically. Use when the user asks to create, generate, export, typeset or "make a nice PDF" of a document, or to convert Markdown/HTML/text into a print-ready PDF. Not for filling, merging or editing existing PDFs.
license: MIT
compatibility: Python 3.9+ with weasyprint, markdown, pdfplumber (pip install weasyprint markdown pdfplumber). Optional pdftoppm (poppler-utils) for the visual check. Works in any agent that can run shell commands.
metadata:
  version: "0.1.0"
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
| Title / author metadata | no | First `# heading` / empty |

Ask only if the content itself is missing. Everything else has a default.

## Procedure

1. **Install dependencies** if needed:
   `pip install weasyprint markdown pdfplumber` (add `--break-system-packages` on managed Pythons).
2. **Write the source as Markdown** (`<name>.md`). Follow the authoring rules
   below; they cover what CSS can't fix.
3. **Build:**
   ```bash
   python scripts/build_pdf.py <name>.md -o <name>.pdf --lang <lang> --paper <A4|letter|A5>
   ```
   Options: `--size 10–12`, `--leading 1.20–1.45`, `--font "Family"`,
   `--css extra.css`, `--indent`, `--title`, `--author`, `--no-page-numbers`.
   The script refuses out-of-range size or leading.
4. **Measure:**
   ```bash
   python scripts/check_pdf.py <name>.pdf
   ```
   Every `FAIL` must be fixed (change options or CSS, rebuild). Resolve each
   `WARN` in the source, or tell the user why it stays.
5. **Look at it:** `pdftoppm -r 80 -png <name>.pdf page` and view page 1, plus
   any page with a table or figure. Check for headings stranded at the bottom
   of a page, overflowing tables and awkward breaks.
6. **Deliver** the PDF. Keep the `.md` source next to it so it can be rebuilt.

### Authoring rules (apply while writing the Markdown)

- **Headings:** no more than three levels (`#` title, `##`, `###`); two is better.
  Use sentence case, never all caps, and no bold or italic inside headings.
- **Emphasis:** bold *or* italic, used sparingly, never both together. Never underline.
- **Punctuation:** type plain `"` and `'`; the build turns them into curly
  quotes (« » for `es`/`fr`, „ “ for `de`). Use `--` for an en dash (ranges,
  2019–2026) and `---` for an em dash (a break in a sentence). Use `...` for an ellipsis.
  Write `©`, `™` and `®` as the real characters.
- **Spacing:** one space between sentences. Use no blank lines or spaces to
  create layout; use CSS classes instead (`{: .page-break }` on a block, or HTML).
- **Exclamation points:** at most one in any document longer than three pages.
- **Caps:** all caps only for less than one line. Wrap acronym runs in `<span class="caps">` to get letterspacing.
- **Centered text:** title and subtitle only (`<p class="subtitle">…</p>`).
- **Tables:** keep them simple. Right-align numeric columns (`---:` in Markdown).
- **Lists:** use them for genuine series, not to break up prose.

## Output

- `<name>.pdf`: A4 by default, body in Charis SIL 11 pt at 132 % line spacing,
  about 65–72 characters per line, justified with hyphenation, page numbers
  from page 2, and title and author metadata set.
- `<name>.md`: the source, kept for rebuilds.
- A one-line report to the user with the `check_pdf.py` result (size, leading, measure).

## Verification

- [ ] `check_pdf.py` exits 0 (no `FAIL`): body 10–12 pt, line spacing 120–145 %, 45–90 characters per line, no Times New Roman, Arial or fallback body font.
- [ ] Every `WARN` is resolved or explained (straight quotes, `--`, `...`, double spaces, fallback glyphs, too many exclamation points).
- [ ] Page images reviewed: no orphaned headings, no table overflow, no text running into the margins.
- [ ] Language passed with `--lang` matches the text, so hyphenation and quotes are correct.
- [ ] No bold and italic together, no underlining, no more than three heading levels.

## References

- `references/practical-typography.md` lists every rule and shows how this skill
  implements it. Read it when you customise the CSS or a check fails.
- `assets/base.css` is the stylesheet. Override it with `--css` rather than
  editing it for a single document.
- `assets/fonts/OFL-CharisSIL.txt` is the font licence.
