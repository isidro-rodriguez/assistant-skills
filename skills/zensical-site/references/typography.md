# Web typography (typography.css)

Source: Matthew Butterick, *Practical Typography*,
<https://practicaltypography.com> — "summary of key rules", "point size",
"line length", "line spacing", "font recommendations". The same author's rules
drive `typeset-pdf`, so the site and the PDFs look like one family.

| Rule (Butterick) | Value in `typography.css` | Note |
|---|---|---|
| Body text 15–25 px on the web | `clamp(15px, 0.9rem, 22px)`: 18 px on most screens | the theme defaults to 15 px |
| Line spacing 120–145 % | `line-height: 1.4` | the theme uses 1.8 |
| 45–90 characters per line | `max-width: 66ch` on paragraphs, lists, quotes, admonitions | `ch` is the width of "0", wider than the average Charis SIL letter: 66ch ≈ 75 characters, the same measure as `typeset-pdf` |
| A good font; avoid system and most free fonts | Charis SIL for text (Charter's design, as in the PDFs) | self-hosted, OFL |
| Sans for headings and interface, serif for text (the user's own rule) | Source Sans 3 (600) for headings, admonition titles, table headers, navigation | through the theme's `--md-text-font` |
| Code in a monospaced font | Source Code Pro at 0.85 em | through `--md-code-font` |
| Don't shrink secondary text below the body range | admonitions 0.9 em, tables 0.85 em (≥ 15 px) | the theme sets about 13 px |
| Bold and italic with restraint; real italics | Charis SIL and Source Sans 3 include true italics | no synthesised styles |
| Wide content needs room | tables, code blocks, diagrams and images keep the full content width | like `--wide-tables` in `typeset-pdf` |

Self-hosting (`theme.font = false` plus `@font-face` rules pointing to
`docs/assets/fonts/`) also keeps the site working offline and avoids sending
every visitor's IP address to Google Fonts.

Fonts come from the Fontsource packages (`@fontsource/charis-sil`,
`@fontsource/source-sans-3`, `@fontsource/source-code-pro`), latin subset, which
covers Spanish (á, ñ, ü, ¿, ¡, «, »). To update them, replace the files in
`assets/site/docs/assets/fonts/` and run `site.py sync` in each project.

A project may override any of this in its own stylesheet (it loads after
`typography.css`), for instance a different body size for a dense reference.
