"""Lorem ipsum body for muestra.odt: one use of every style of informe.ott.

build_templates.py calls add() on the report document, after the "Introducción"
heading. Only the structure is meaningful; the words are filler.
"""

from __future__ import annotations

from odf import teletype
from odf.draw import Frame, Image
from odf.style import (
    Style,
    TableCellProperties,
    TableColumnProperties,
    TableProperties,
)
from odf.table import Table, TableCell, TableColumn, TableHeaderRows, TableRow
from odf.text import (
    A,
    H,
    List,
    ListItem,
    Note,
    NoteBody,
    NoteCitation,
    P,
    Sequence,
    SequenceDecl,
    SequenceDecls,
    Span,
)

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo "
    "consequat."
)
DUIS = (
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore "
    "eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt "
    "in culpa qui officia deserunt mollit anim id est laborum."
)
SED = (
    "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium "
    "doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore "
    "veritatis et quasi architecto beatae vitae dicta sunt explicabo."
)
NEMO = (
    "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, "
    "sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt."
)

CHAR_STYLES = {
    "em": "Emphasis",
    "strong": "Strong_20_Emphasis",
    "sc": "Versalitas",
    "caps": "Mayusculas_20_espaciadas",
    "code": "Source_20_Text",
}

# Grey bars, no text: a stand-in for a chart.
FIGURE_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="180"
 viewBox="0 0 400 180"><g fill="#999999">
<rect x="40" y="100" width="40" height="70"/><rect x="110" y="60" width="40" height="110"/>
<rect x="180" y="80" width="40" height="90"/><rect x="250" y="30" width="40" height="140"/>
<rect x="320" y="70" width="40" height="100"/></g>
<line x1="20" y1="170" x2="380" y2="170" stroke="#111111" stroke-width="1"/></svg>"""


class Sample:
    def __init__(self, doc):
        self.doc = doc
        self.body = doc.text
        self.notes = 0
        self.counters = {"Figure": 0, "Table": 0}

    # ---- helpers ----
    def auto(self, name: str, family: str, parent: str | None = None, **attrs):
        style = Style(name=name, family=family, **attrs)
        if parent:
            style.setAttribute("parentstylename", parent)
        self.doc.automaticstyles.addElement(style)
        return style

    def para(self, style, *parts) -> P:
        """A paragraph from strings and (kind, text) runs: em, strong, sc, caps,
        code, link or note."""
        paragraph = P(stylename=style)
        for part in parts:
            if isinstance(part, str):
                paragraph.addText(part)
                continue
            kind, text = part
            if kind == "link":
                paragraph.addElement(
                    A(
                        type="simple",
                        href="https://example.com",
                        stylename="Internet_20_link",
                        text=text,
                    )
                )
            elif kind == "note":
                self.notes += 1
                note = Note(id=f"ftn{self.notes}", noteclass="footnote")
                note.addElement(NoteCitation(text=str(self.notes)))
                note_body = NoteBody()
                note_body.addElement(P(stylename="Footnote", text=text))
                note.addElement(note_body)
                paragraph.addElement(note)
            else:
                paragraph.addElement(Span(stylename=CHAR_STYLES[kind], text=text))
        self.body.addElement(paragraph)
        return paragraph

    def heading(self, level: int, text: str) -> None:
        self.body.addElement(
            H(outlinelevel=level, stylename=f"Heading_20_{level}", text=text)
        )

    def bullets(self, style: str, items: list[str]) -> None:
        listing = List(stylename=style)
        for item in items:
            entry = ListItem()
            entry.addElement(P(stylename="List_20_Contents", text=item))
            listing.addElement(entry)
        self.body.addElement(listing)

    def caption(self, sequence: str, label: str, text: str, style="Caption") -> None:
        self.counters[sequence] += 1
        number = self.counters[sequence]
        paragraph = P(stylename=style, text=f"{label} ")
        paragraph.addElement(
            Sequence(
                name=sequence,
                formula=f"ooow:{sequence}+1",
                numformat="1",
                text=str(number),
            )
        )
        paragraph.addText(f": {text}")
        self.body.addElement(paragraph)

    def table(self, name: str, width: str, rows: list[list[str]], numeric: set[int]):
        """A table with the PDF's rules: under the header row and the last row."""
        cells = {}
        for key, rule in (
            ("head", "0.75pt solid #111111"),
            ("body", None),
            ("last", "0.5pt solid #111111"),
        ):
            style = self.auto(f"{name}.{key}", "table-cell")
            borders = {"border": "none"} if rule is None else {"borderbottom": rule}
            style.addElement(
                TableCellProperties(
                    paddingtop="3.3pt",
                    paddingbottom="3.3pt",
                    paddingleft="0pt",
                    paddingright="6.6pt",
                    verticalalign="top",
                    **borders,
                )
            )
            cells[key] = style
        table_style = self.auto(name, "table")
        table_style.addElement(
            TableProperties(
                width=width, align="margins", margintop="4.4pt", marginbottom="0pt"
            )
        )
        column = self.auto(f"{name}.col", "table-column")
        column.addElement(TableColumnProperties(relcolumnwidth="1000*"))
        table = Table(name=name, stylename=table_style)
        table.addElement(
            TableColumn(stylename=column, numbercolumnsrepeated=len(rows[0]))
        )
        header = TableHeaderRows()
        for r, values in enumerate(rows):
            row = TableRow()
            kind = "head" if r == 0 else "last" if r == len(rows) - 1 else "body"
            for c, value in enumerate(values):
                cell = TableCell(stylename=cells[kind], valuetype="string")
                if r == 0:
                    style = (
                        "Tabla_20_cabecera_20_cifras"
                        if c in numeric
                        else "Table_20_Heading"
                    )
                else:
                    style = "Tabla_20_cifras" if c in numeric else "Table_20_Contents"
                cell.addElement(P(stylename=style, text=value))
                row.addElement(cell)
            (header if r == 0 else table).addElement(row)
            if r == 0:
                table.addElement(header)
        self.body.addElement(table)

    # ---- content ----
    def build(self) -> None:
        doc = self.doc
        decls = SequenceDecls()
        for name in ("Illustration", "Table", "Text", "Drawing", "Figure"):
            decls.addElement(SequenceDecl(name=name, displayoutlinelevel="0"))
        self.body.insertBefore(decls, self.body.childNodes[0])

        self.para(
            "Text_20_body",
            LOREM,
            " ",
            ("em", "Ut enim ad minim veniam"),
            ", quis nostrud ",
            ("strong", "exercitation ullamco"),
            " laboris nisi ut aliquip.",
            ("note", DUIS),
        )
        self.para(
            "Text_20_body",
            "Lorem ",
            ("sc", "Ipsum Dolor"),
            " sit amet, ",
            ("caps", "LOREM IPSUM"),
            " consectetur ",
            ("code", "lorem_ipsum()"),
            " adipiscing elit, sed do ",
            ("link", "eiusmod tempor"),
            ". ",
            SED,
        )

        self.heading(2, "Lorem ipsum dolor")
        self.para("Text_20_body", DUIS)
        self.bullets(
            "List_20_1",
            [
                "Lorem ipsum dolor sit amet, consectetur adipiscing.",
                "Nemo enim ipsam voluptatem quia voluptas.",
                "Sed ut perspiciatis unde omnis iste natus.",
            ],
        )
        self.para("Text_20_body", NEMO)
        self.bullets(
            "Numbering_20_123",
            [
                "Duis aute irure dolor in reprehenderit.",
                "Excepteur sint occaecat cupidatat.",
            ],
        )

        self.heading(3, "Consectetur adipiscing")
        self.para("Text_20_body", SED)
        self.para("Quotations", LOREM + " " + NEMO)
        code = P(stylename="Preformatted_20_Text")
        teletype.addTextToElement(code, "def lorem(ipsum):\n    return ipsum * 2")
        self.body.addElement(code)
        self.para("Text_20_body", NEMO)
        self.para("Formula", "a² + b² = c²")
        self.para("Text_20_body", DUIS)

        self.heading(1, "Sed ut perspiciatis")
        self.para("Text_20_body", LOREM + " " + SED)
        self.table(
            "Tabla1",
            "138mm",
            [
                ["Lorem", "Ipsum", "Dolor"],
                ["Sit amet", "1.250", "12,5"],
                ["Consectetur", "980", "9,8"],
                ["Adipiscing elit", "11.020", "110,2"],
                ["Total", "13.250", "132,5"],
            ],
            numeric={1, 2},
        )
        self.caption("Table", "Tabla", "Lorem ipsum dolor sit amet")
        self.para("Text_20_body", NEMO)

        self.heading(2, "Nemo enim ipsam")
        figure = P(stylename="Figure")
        href = doc.addPicture("Pictures/figura.svg", "image/svg+xml", FIGURE_SVG)
        frame = Frame(width="90mm", height="40.5mm", anchortype="as-char")
        frame.addElement(Image(href=href))
        figure.addElement(frame)
        self.body.addElement(figure)
        self.caption("Figure", "Figura", "Consectetur adipiscing elit")
        self.para("Text_20_body", DUIS)
        self.body.addElement(P(stylename="Separador"))
        self.para("Texto_20_con_20_sangria", LOREM + " " + NEMO)
        self.para("Texto_20_con_20_sangria", SED + " " + DUIS)

        # A wide table on a landscape page, then back to portrait.
        landscape = self.auto(
            "S1", "paragraph", "Text_20_body", masterpagename="Apaisada"
        )
        self.para(landscape, NEMO)
        header = ["Lorem", "Ipsum", "Dolor", "Sit", "Amet", "Consectetur", "Elit"]
        rows = [header] + [
            [f"Lorem {i}", *(f"{(i * 37 + j * 113) % 1000},{j}" for j in range(6))]
            for i in range(1, 7)
        ]
        self.table("Tabla2", "247mm", rows, numeric=set(range(1, 7)))
        self.caption("Table", "Tabla", "Sed do eiusmod tempor incididunt")

        portrait = self.auto(
            "S2", "paragraph", "Titulo_20_sin_20_numero", masterpagename="Cuerpo"
        )
        self.para(portrait, "Bibliografía")
        for author, title in (
            ("Lorem, I.", "Dolor sit amet"),
            ("Ipsum, D. y Amet, S.", "Consectetur adipiscing elit"),
            ("Tempor, E.", "Ut labore et dolore magna aliqua"),
        ):
            self.para(
                "Bibliography_20_1",
                f"{author} (2020). ",
                ("em", title),
                ". Nemo enim ipsam voluptatem.",
            )

        self.para("Anexo", "Anexo A. Lorem ipsum dolor")
        self.para("Text_20_body", LOREM)
        self.para("Text_20_body", SED)


def add(doc) -> None:
    Sample(doc).build()
