# Reports (`--doc report`)

Use this layout for formal documents: reports, technical studies, project
documentation and anything that needs a cover, a table of contents and
numbered sections. Body typography is identical to `note`.

## Source structure

```markdown
---
title: Quarterly Site Safety Report        # cover title and running head
subtitle: North Harbour Housing Block      # optional
author: Isidro Rodríguez González          # optional
organization: Example Construction Ltd.    # optional, top of cover
date: 13 November 2026                     # optional, write it as it should print
version: "1.0"                             # optional; quote it so YAML keeps it text
logo: images/logo.svg                      # optional, relative to the .md file
---

## Summary            → 1
### Scope             → 1.1   (in the contents)
#### Exclusions       → 1.1.1 (not in the contents)
```

- Only these seven fields are accepted. An unknown field stops the build with a
  message, so typos don't go unnoticed.
- If `title` is missing, the first `# heading` becomes the title, and a
  `<p class="subtitle">` straight after it becomes the subtitle. Both are
  removed from the body.
- Don't type numbers in headings: they are generated, and typed numbers would
  appear twice.

## Numbering (Practical Typography, *hierarchical headings*)

- Tiered numbers only: `1`, `1.1`, `1.1.1`. No roman numerals or letters,
  because each label should show its parent levels.
- At most three numbered levels (`##`, `###`, `####`). If you need a fourth,
  restructure the section instead.
- The contents lists levels 1 and 2 (`##`, `###`).

## Pages

| Part | Layout | Number |
|---|---|---|
| Cover | Organisation at the top, then title and subtitle; author, date and version at the foot | none (still counts as page i) |
| Contents | Title "Contents" (localised by `--lang`: Índice, Sommaire, Inhalt…) | roman: ii, iii… |
| Body | Running head: report title, italic 9 pt, top right | arabic, restarts at 1 |

Each part starts on a new page. Sections don't start new pages by default; put
`<div class="page-break"></div>` before a heading to force one.

## Checks

`python scripts/check_pdf.py report.pdf --report` adds:

- `cover`: page 1 has no page number.
- `toc`: the contents page exists, and each entry's page number is the page
  where that numbered heading prints.
- `numbering`: numbered headings run in sequence without gaps or skipped levels.
