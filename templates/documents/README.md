# Document templates

LibreOffice Writer templates with the same typography as the PDFs of the
[`typeset-pdf`](../../skills/typeset-pdf/SKILL.md) skill (`assets/base.css` and
`assets/report.css`), for documents written by hand. The style names and sample
texts are in Spanish.

| Template | Contents |
|---|---|
| `documento.ott` | Charis SIL 11 pt, 132 % leading (14.5 pt minimum), A4 with 25/36/31/36 mm margins, justified text with hyphenation, page number at the foot except on the first page. Title, subtitle, three heading levels, quotations, code, captions, footnotes, lists and table styles, plus "Texto con sangría" (first-line indents instead of paragraph space). |
| `informe.ott` | The same plus the report layout: cover without a number (entity, title, subtitle, author/date/version at the foot), table of contents in roman numerals, body in arabic numerals from 1 with the title in the header, headings numbered 1 / 1.1 / 1.1.1 with hanging numbers. |

Charis SIL is embedded, so the templates look the same where it is not
installed.

## Using them

1. Open the `.ott` in Writer and save it with *File > Templates > Save as
   Template* (optionally *Set as Default* in the template manager).
2. In `informe.ott`, set the title in *File > Properties > Description > Title*:
   the cover and the running header show it. Keep the first body heading
   ("1 Introducción"): it starts the "Cuerpo" page style and restarts page
   numbers at 1. Update the table of contents when you finish (right click >
   *Update Index*).
3. Writer styles cannot carry table borders: for the PDF look, add a rule
   under the header row and under the last row.

## Rebuilding

`build_templates.py` writes both templates from the styles defined in it.
Change the styles there, never by editing the `.ott` files, and keep them in
step with `typeset-pdf`'s stylesheets.

```bash
uv run --with odfpy --with fonttools python templates/documents/build_templates.py
```

It needs LibreOffice (`soffice`) and fontconfig (Linux, macOS). Charis SIL comes
from `skills/typeset-pdf/assets/fonts/`, converted to TTF in a temporary folder;
LibreOffice runs with its own temporary profile, so an open LibreOffice is not
affected. The script fails unless both templates embed the four Charis SIL
styles.
