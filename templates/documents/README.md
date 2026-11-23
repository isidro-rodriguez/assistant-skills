# Document templates

LibreOffice Writer templates with the same typography as the PDFs of the
[`typeset-pdf`](../../skills/typeset-pdf/SKILL.md) skill (`assets/base.css` and
`assets/report.css`), for documents written by hand. The style names and sample
texts are in Spanish.

| File | Contents |
|---|---|
| `documento.ott` | Charis SIL 11 pt, 132 % leading (14.5 pt minimum), A4 with 25/36/31/36 mm margins, justified text with hyphenation, page number at the foot except on the first page. Title, subtitle, three heading levels, quotations, code, formulas, captions, footnotes, lists, table, bibliography and separator styles, plus "Texto con sangría" (first-line indents instead of paragraph space) and an "Apaisada" landscape page. |
| `informe.ott` | The same plus the report layout: cover without a number (logo, entity, title, subtitle, author/date/version), table of contents and indexes of figures and tables in roman numerals, body in arabic numerals from 1 with the title in the header, headings numbered 1 / 1.1 / 1.1.1 with hanging numbers, unnumbered headings and appendices. |
| `muestra.odt`, `muestra.pdf` | `informe.ott` filled with lorem ipsum that uses every style: open the PDF to see what the templates produce. |

Charis SIL is embedded, so the templates look the same where it is not
installed.

## Styles beyond the defaults

| Style | Kind | Use |
|---|---|---|
| Texto con sangría | paragraph | Body text with a 1.5 em first-line indent and no space between paragraphs. Use it for a whole document, not mixed with Body Text. |
| Título sin número | paragraph | Heading 1 look without a number (Bibliografía, Glosario). Listed in the report's table of contents. |
| Anexo | paragraph | Appendix heading on a new page, written as "Anexo A. …". Listed in the table of contents. |
| Fórmula | paragraph | Display formula, centred, never split across pages. |
| Separador | paragraph | Section break: a short centred rule (leave the paragraph empty). |
| Tabla: cifras, Tabla: cabecera de cifras | paragraph | Number columns and their header, flush right. |
| Bibliography 1 | paragraph | Reference list entry with a hanging indent. |
| Mayúsculas espaciadas | character | Runs of capitals and acronyms, with 8 % extra tracking. |
| Versalitas | character | Small caps with 6 % extra tracking. The bundled Charis SIL subset has no real small caps, so Writer synthesises them: use sparingly. |
| Apaisada | page | Landscape A4 for wide tables: insert a manual break with this page style before the table and one back to "Cuerpo" (report) or "Default Page Style" (document) after it. |

## Using them

1. Open the `.ott` in Writer and save it with *File > Templates > Save as
   Template* (optionally *Set as Default* in the template manager).
2. In `informe.ott`, fill in *File > Properties*: *Description > Title* and
   *Subject* are the cover title and subtitle (the title also goes in the
   running header); *Custom Properties* holds Entidad, Autor, Fecha and Versión.
   Fields show them on the cover; press F9 if they do not refresh. Click the
   `<Logotipo>` placeholder to insert the logo (at most 22 mm high), or delete
   that paragraph.
3. Keep the first body heading ("1 Introducción"): it starts the "Cuerpo" page
   style and restarts page numbers at 1.
4. Number figures and tables with *Insert > Caption* (categories *Figura* and
   *Tabla*): the indexes of figures and tables collect them. Delete an index the
   report does not need. When you finish, update all indexes with *Tools >
   Update > Update All*.
5. Tables: apply "Table Heading" to the first row and, as in the PDF, a rule
   under the header row (0.75 pt) and under the last row (0.5 pt), with no
   other borders. Writer drops table styles nobody uses when it saves, so the
   templates cannot carry one: copy a table from `muestra.odt`, or format one
   once and save it with *Table > AutoFormat Styles > Add* to reuse it in every
   document.

## Outside the templates

Some settings belong to LibreOffice, not to the file, so a template cannot
carry them. Set them once:

- *Tools > AutoCorrect Options > Localized Options*: double quotes « » for
  Spanish, single quotes " ".
- *Tools > AutoCorrect Options > Options*: keep "Replace dashes" (– and —) and
  "Ignore double spaces" (one space between sentences) on. The *Replace* tab's
  default list turns `...` into `…`.
- *File > Export as PDF*: tick *Archive (PDF/A)* or *Universal Accessibility
  (PDF/UA)* for documents that must be archived or accessible; *Export outlines*
  gives the PDF bookmarks from the headings.

## Rebuilding

`build_templates.py` writes the templates and the sample from the styles
defined in it (the sample's text is in `sample.py`). Change the styles there,
never by editing the `.ott` files, and keep them in step with `typeset-pdf`'s
stylesheets.

```bash
uv run --with odfpy --with fonttools --with pypdf python templates/documents/build_templates.py
```

It needs LibreOffice (`soffice`) and fontconfig (Linux, macOS). Charis SIL comes
from `skills/typeset-pdf/assets/fonts/`, converted to TTF in a temporary folder;
LibreOffice runs with its own temporary profile, so an open LibreOffice is not
affected. `refresh_sample.py` updates the sample's indexes through UNO, with
LibreOffice's Python or the system one with `python3-uno`; without either the
sample is written with empty indexes and a warning.

The script fails unless every file embeds the four Charis SIL styles and keeps
the added styles, and unless the sample PDF has portrait and landscape A4 pages
set only in Charis SIL and DejaVu Sans Mono.
