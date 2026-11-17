# Typography

Source: Matthew Butterick, *Practical Typography*,
<https://practicaltypography.com> — "summary of key rules", "point size",
"line length", "line spacing". The same rules drive `typeset-pdf`.

## What every site must meet (`site.py measure`)

| Rule (Butterick) | Range | How it is measured |
|---|---|---|
| Body text 15–25 px on the web | 15–25 px | computed `font-size` of article paragraphs |
| Line spacing 120–145 % of the point size | 1.20–1.45 | computed `line-height` ÷ `font-size` |
| Average line length 45–90 characters | 45–90 | paragraph width ÷ average character width of that paragraph's own text in its own font |

`measure` serves `site/`, opens the home page and the largest pages at 1280 and
1920 px wide (the theme enlarges `rem` on wide screens), takes article paragraphs
of at least 120 characters, and compares the median per page. Any font passes; it
only warns about system fonts Butterick advises against (Arial, Times New Roman,
Helvetica, Calibri…).

Typical fixes in an existing site, in the project's stylesheet:

- `line-height`: Zensical's theme uses 1.6 (classic) to 1.8 (modern); set
  `.md-typeset { line-height: 1.4; }`.
- line length: put `max-width` in `ch` on `.md-typeset > :is(p, ul, ol, dl,
  blockquote, .admonition, details)` (and the same under `.md-typeset
  .doc-contents >` for mkdocstrings API pages) and tune it until `measure` reports about 75
  characters (`ch` is the width of "0", wider than the average character, so
  about 60ch gives 75 characters in most fonts). Tables, code and figures keep
  the full width.
- size: the theme's default 15 px is at the lower edge; 16–20 px reads better.

## Starting typography (new sites)

`assets/site/docs/assets/stylesheets/typography.css`, which a project may then
change freely:

| Choice | Value |
|---|---|
| Text | Charis SIL (Charter's design, as in the PDFs), 18 px (15–22 px with `clamp`), line height 1.4, 60ch ≈ 75 characters |
| Headings and interface | Source Sans 3, weight 600 (the user's rule: serif text, sans headings) |
| Code | Source Code Pro, 0.85 em |
| Admonitions and tables | 0.9 em and 0.85 em, so they stay at or above 15 px |
| Fonts | self-hosted (`theme.font = false`, `@font-face` to `docs/assets/fonts/`): no Google Fonts, works offline |

Fonts come from the Fontsource packages (`@fontsource/charis-sil`,
`@fontsource/source-sans-3`, `@fontsource/source-code-pro`), latin subset, which
covers Spanish (á, ñ, ü, ¿, ¡, «, »).
