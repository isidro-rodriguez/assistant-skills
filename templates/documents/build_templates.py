#!/usr/bin/env python3
"""Build the LibreOffice Writer templates with the typeset-pdf style.

Translates skills/typeset-pdf/assets/base.css and report.css into Writer styles
and writes, next to this script:

  documento.ott  Charis SIL 11 pt, 132 % leading, A4 with 25/36/31/36 mm
                 margins, page number at the foot except on the first page.
  informe.ott    The same plus the report layout: cover without a number (logo,
                 entity, title, subtitle, author/date/version as fields), table
                 of contents and indexes of figures and tables in roman
                 numerals, body in arabic from 1 with the title in the header,
                 headings numbered 1 / 1.1 / 1.1.1, unnumbered headings and
                 appendices.
  muestra.odt    informe.ott filled with lorem ipsum that uses every style, and
  muestra.pdf    its PDF, to review the templates at a glance.

LibreOffice converts the generated .odt files and embeds Charis SIL, taken from
the skill's own fonts (no need to install it). Needs LibreOffice (soffice) and
fontconfig (Linux, macOS); run it as

  uv run --with odfpy --with fonttools --with pypdf python templates/documents/build_templates.py

The sample's indexes are refreshed through LibreOffice's Python (UNO) with
refresh_sample.py; without it the sample is still written, with empty indexes.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import sample
from fontTools.ttLib import TTFont
from odf import dc, meta
from odf.config import ConfigItem, ConfigItemSet
from odf.draw import Frame, TextBox
from odf.opendocument import OpenDocumentText
from odf.style import (
    DefaultStyle,
    FontFace,
    Footer,
    FooterStyle,
    GraphicProperties,
    Header,
    HeaderFooterProperties,
    HeaderStyle,
    ListLevelLabelAlignment,
    ListLevelProperties,
    MasterPage,
    PageLayout,
    PageLayoutProperties,
    ParagraphProperties,
    Style,
    TabStop,
    TabStops,
    TextProperties,
)
from odf.text import (
    H,
    IllustrationIndex,
    IllustrationIndexEntryTemplate,
    IllustrationIndexSource,
    IndexBody,
    IndexEntryChapter,
    IndexEntryPageNumber,
    IndexEntryTabStop,
    IndexEntryText,
    IndexSourceStyle,
    IndexSourceStyles,
    IndexTitle,
    IndexTitleTemplate,
    ListLevelStyleBullet,
    ListLevelStyleNumber,
    ListStyle,
    OutlineLevelStyle,
    OutlineStyle,
    P,
    PageNumber,
    Placeholder,
    Subject,
    TableIndex,
    TableIndexEntryTemplate,
    TableIndexSource,
    TableOfContent,
    TableOfContentEntryTemplate,
    TableOfContentSource,
    Title,
    UserDefined,
)

BODY = "Charis SIL"
MONO = "DejaVu Sans Mono"
SIZE = 11.0  # pt
INK = "#111111"
GREY = "#444444"
RULE = "#888888"
TEXT_WIDTH = 138  # mm: 210 mm page − 2 × 36 mm margins


def pt(value: float) -> str:
    """Points, with at most two decimals."""
    return f"{round(value, 2):g}pt"


def lead(size: float, ratio: float) -> dict:
    """Minimum line height as in the CSS (size × ratio).

    Writer's proportional spacing multiplies the font's natural line height, which
    for Charis SIL is already ~1.25 em: 132 % would give ~165 %. A minimum in points
    matches the PDF and still lets a line grow for formulas or images.
    """
    return {"lineheightatleast": pt(size * ratio)}


def fixed(size: float, ratio: float) -> dict:
    """Exact line height for headings: a minimum leaves Charis headings too loose."""
    return {"lineheight": pt(size * ratio)}


def em(value: float) -> str:
    """A multiple of the 11 pt body size, in points (Writer has no em unit)."""
    return pt(value * SIZE)


def para_style(
    doc, name, display, parent=None, cls="text", para=None, text=None, **extra
):
    """Add a paragraph style with paragraph and text properties."""
    attrs = {"name": name, "family": "paragraph", "displayname": display}
    if parent:
        attrs["parentstylename"] = parent
    if cls:
        attrs["attributes"] = {"class": cls}
    attrs.update(extra)
    style = Style(**attrs)
    if para:
        style.addElement(ParagraphProperties(**para))
    if text:
        style.addElement(TextProperties(**text))
    doc.styles.addElement(style)
    return style


def build(path: str, report: bool = False, with_sample: bool = False) -> None:
    doc = OpenDocumentText()

    for name, family in ((BODY, "roman"), (MONO, "modern")):
        doc.fontfacedecls.addElement(
            FontFace(
                name=name,
                fontfamily=f"'{name}'",
                fontfamilygeneric=family,
                fontpitch="fixed" if family == "modern" else "variable",
            )
        )

    # Defaults: Spanish, hyphenation, base font.
    default = DefaultStyle(family="paragraph")
    default.addElement(
        ParagraphProperties(
            hyphenationladdercount="2",
            writingmode="lr-tb",
            orphans="2",
            widows="2",
            punctuationwrap="hanging",
            linebreak="strict",
            tabstopdistance="1.25cm",
        )
    )
    default.addElement(
        TextProperties(
            fontname=BODY,
            fontnameasian=BODY,
            fontnamecomplex=BODY,
            fontsize=pt(SIZE),
            language="es",
            country="ES",
            hyphenate="true",
            hyphenationremaincharcount="2",
            hyphenationpushcharcount="2",
            letterkerning="true",
            color=INK,
        )
    )
    doc.styles.addElement(default)

    # ---- Paragraph styles ----
    para_style(
        doc,
        "Standard",
        "Default Paragraph Style",
        cls=None,
        para=lead(SIZE, 1.32),
        text={"fontname": BODY, "fontsize": pt(SIZE)},
    )
    para_style(
        doc,
        "Text_20_body",
        "Body Text",
        parent="Standard",
        para={
            "margintop": "0pt",
            "marginbottom": em(0.6),
            "textalign": "justify",
            "justifysingleword": "false",
        },
    )
    para_style(
        doc,
        "Texto_20_con_20_sangria",
        "Texto con sangría",
        parent="Text_20_body",
        para={"marginbottom": "0pt", "textindent": em(1.5)},
    )
    para_style(
        doc,
        "Heading",
        "Heading",
        parent="Standard",
        para={"keepwithnext": "always", "textalign": "start", **fixed(SIZE, 1.2)},
        text={"fontweight": "bold", "hyphenate": "false"},
        nextstylename="Text_20_body",
    )
    para_style(
        doc,
        "Title",
        "Title",
        parent="Heading",
        cls="chapter",
        para={
            "textalign": "center",
            "margintop": "0pt",
            "marginbottom": em(1.2),
            **fixed(SIZE * 1.5, 1.2),
        },
        text={"fontsize": em(1.5)},
        nextstylename="Subtitle",
    )
    para_style(
        doc,
        "Subtitle",
        "Subtitle",
        parent="Standard",
        cls="chapter",
        para={"textalign": "center", "margintop": "0pt", "marginbottom": em(1.6)},
        text={"fontstyle": "italic"},
        nextstylename="Text_20_body",
    )
    headings = (
        (1, 1.15, em(1.6), em(0.5), {"fontweight": "bold"}),
        (2, 1.0, em(1.3), em(0.4), {"fontweight": "bold"}),
        # In the report the third level is bold, like the other two.
        (
            3,
            1.0,
            em(1.1),
            em(0.3),
            {"fontweight": "bold"}
            if report
            else {"fontweight": "normal", "fontstyle": "italic"},
        ),
    )
    for level, scale, before, after, text in headings:
        para_style(
            doc,
            f"Heading_20_{level}",
            f"Heading {level}",
            parent="Heading",
            para={
                "margintop": before,
                "marginbottom": after,
                **fixed(SIZE * scale, 1.2),
            },
            text={"fontsize": em(scale), **text},
            defaultoutlinelevel=str(level),
            nextstylename="Text_20_body",
        )
    para_style(
        doc,
        "Quotations",
        "Quotations",
        parent="Standard",
        cls="html",
        para={
            "marginleft": em(2),
            "marginright": em(2),
            "margintop": "0pt",
            "marginbottom": em(0.6),
            "textalign": "justify",
            **lead(SIZE * 0.95, 1.32),
        },
        text={"fontsize": pt(SIZE * 0.95)},
    )
    para_style(
        doc,
        "Preformatted_20_Text",
        "Preformatted Text",
        parent="Standard",
        cls="html",
        para={
            **lead(SIZE * 0.85, 1.3),
            "marginbottom": em(0.6),
            "backgroundcolor": "#f4f4f2",
            "padding": em(0.4),
        },
        text={"fontname": MONO, "fontsize": pt(SIZE * 0.85), "hyphenate": "false"},
    )
    para_style(
        doc,
        "Caption",
        "Caption",
        parent="Standard",
        cls="extra",
        para={
            "textalign": "center",
            "margintop": em(0.4),
            "marginbottom": em(1),
            **lead(SIZE * 0.9, 1.32),
        },
        text={"fontsize": pt(SIZE * 0.9), "fontstyle": "italic"},
    )
    para_style(
        doc,
        "Figure",
        "Figure",
        parent="Standard",
        cls="extra",
        para={"textalign": "center", "margintop": em(1), "keepwithnext": "always"},
    )
    para_style(
        doc,
        "Table_20_Contents",
        "Table Contents",
        parent="Standard",
        cls="extra",
        para={**lead(SIZE * 0.95, 1.25), "textalign": "start"},
        text={"fontsize": pt(SIZE * 0.95), "hyphenate": "false"},
    )
    para_style(
        doc,
        "Table_20_Heading",
        "Table Heading",
        parent="Table_20_Contents",
        cls="extra",
        text={"fontweight": "bold"},
    )
    para_style(
        doc,
        "Footnote",
        "Footnote",
        parent="Standard",
        cls="extra",
        para={**lead(SIZE * 0.85, 1.3), "marginleft": em(1), "textindent": em(-1)},
        text={"fontsize": pt(SIZE * 0.85)},
    )
    para_style(
        doc,
        "List_20_Contents",
        "List Contents",
        parent="Standard",
        cls="list",
        para={"marginbottom": em(0.2), "textalign": "start"},
    )
    para_style(
        doc,
        "Header_20_and_20_Footer",
        "Header and Footer",
        parent="Standard",
        cls="extra",
    )
    para_style(
        doc,
        "Footer",
        "Footer",
        parent="Header_20_and_20_Footer",
        cls="extra",
        para={"textalign": "center"},
        text={"fontsize": pt(9), "color": GREY},
    )
    # hr: a 0.5 pt grey rule, 30 % of the text width, centred, 1.5 em above and
    # below. The paragraph is a 1 pt line so only its top border shows.
    side = f"{TEXT_WIDTH * 0.35:g}mm"
    para_style(
        doc,
        "Separador",
        "Separador",
        parent="Standard",
        cls="extra",
        para={
            "marginleft": side,
            "marginright": side,
            "margintop": em(1.5),
            "marginbottom": em(1.5),
            "bordertop": f"0.5pt solid {RULE}",
            "borderbottom": "none",
            "borderleft": "none",
            "borderright": "none",
            "padding": "0pt",
            "lineheight": "1pt",
        },
        text={"fontsize": "1pt"},
        nextstylename="Text_20_body",
    )
    # .math-display: centred, never split across pages.
    para_style(
        doc,
        "Formula",
        "Fórmula",
        parent="Standard",
        cls="extra",
        para={
            "textalign": "center",
            "margintop": em(0.6),
            "marginbottom": em(0.9),
            "keeptogether": "always",
        },
        text={"hyphenate": "false"},
        nextstylename="Text_20_body",
    )
    # td.num: figures flush right (Charis SIL figures are already tabular).
    para_style(
        doc,
        "Tabla_20_cifras",
        "Tabla: cifras",
        parent="Table_20_Contents",
        cls="extra",
        para={"textalign": "end"},
    )
    para_style(
        doc,
        "Tabla_20_cabecera_20_cifras",
        "Tabla: cabecera de cifras",
        parent="Table_20_Heading",
        cls="extra",
        para={"textalign": "end"},
    )
    para_style(
        doc,
        "Bibliography_20_1",
        "Bibliography 1",
        parent="Standard",
        cls="index",
        para={
            "marginleft": em(1.5),
            "textindent": em(-1.5),
            "marginbottom": em(0.3),
            "textalign": "start",
        },
    )
    # Like Heading 1 but outside the outline, so it is never numbered; the
    # report's table of contents still lists it.
    para_style(
        doc,
        "Titulo_20_sin_20_numero",
        "Título sin número",
        parent="Heading",
        para={
            "margintop": em(1.6),
            "marginbottom": em(0.5),
            **fixed(SIZE * 1.15, 1.2),
        },
        text={"fontsize": em(1.15), "fontweight": "bold"},
        nextstylename="Text_20_body",
    )

    # ---- Character styles ----
    # Writer drops letter-spacing in em, so it is given in points of the body size.
    for name, display, text in (
        ("Emphasis", "Emphasis", {"fontstyle": "italic"}),
        ("Strong_20_Emphasis", "Strong Emphasis", {"fontweight": "bold"}),
        (
            "Source_20_Text",
            "Source Text",
            {"fontname": MONO, "fontsize": "85%", "hyphenate": "false"},
        ),
        # In print, links are neither underlined nor coloured.
        (
            "Internet_20_link",
            "Internet Link",
            {"textunderlinestyle": "none", "color": INK},
        ),
        (
            "Versalitas",
            "Versalitas",
            {"fontvariant": "small-caps", "letterspacing": pt(0.06 * SIZE)},
        ),
        # .caps, abbr: 5–12 % extra tracking for runs of capitals.
        (
            "Mayusculas_20_espaciadas",
            "Mayúsculas espaciadas",
            {"letterspacing": pt(0.08 * SIZE)},
        ),
    ):
        style = Style(name=name, family="text", displayname=display)
        style.addElement(TextProperties(**text))
        doc.styles.addElement(style)

    # ---- Lists: 1.4 em indent; bullets from Charis SIL, not OpenSymbol ----
    bullets = ListStyle(name="List_20_1", displayname="List 1")
    numbers = ListStyle(name="Numbering_20_123", displayname="Numbering 123")
    for level in range(1, 4):
        indent = em(1.4 * level)
        for parent, item in (
            (bullets, ListLevelStyleBullet(level=level, bulletchar="••–"[level - 1])),
            (numbers, ListLevelStyleNumber(level=level, numformat="1", numsuffix=".")),
        ):
            props = ListLevelProperties(listlevelpositionandspacemode="label-alignment")
            props.addElement(
                ListLevelLabelAlignment(
                    labelfollowedby="listtab",
                    listtabstopposition=indent,
                    textindent=em(-1.4),
                    marginleft=indent,
                )
            )
            item.addElement(props)
            if parent is bullets:
                item.addElement(TextProperties(fontname=BODY))
            parent.addElement(item)
    doc.styles.addElement(bullets)
    doc.styles.addElement(numbers)

    # Unnumbered headings; the report numbers 1 / 1.1 / 1.1.1 with hanging numbers
    # (text aligned at 2.2 / 2.6 / 3.0 em, like .secnum in report.css).
    outline = OutlineStyle(name="Outline")
    for level in range(1, 11):
        if report and level <= 3:
            width = em((2.2, 2.6, 3.0)[level - 1])
            item = OutlineLevelStyle(
                level=level, numformat="1", displaylevels=str(level)
            )
            props = ListLevelProperties(listlevelpositionandspacemode="label-alignment")
            props.addElement(
                ListLevelLabelAlignment(
                    labelfollowedby="listtab",
                    listtabstopposition=width,
                    textindent=f"-{width}",
                    marginleft=width,
                )
            )
            item.addElement(props)
        else:
            item = OutlineLevelStyle(level=level, numformat="")
        outline.addElement(item)
    doc.styles.addElement(outline)

    # ---- Page: A4, text block slightly above centre ----
    # 31 mm from the page edge to the text; on numbered pages that is an 18 mm
    # margin + 8 mm spacing + a 5 mm footer.
    # Landscape pages (for tables too wide for the 138 mm column, like
    # table.wide in the PDF) keep the vertical margins and use 25 mm at the sides.
    def page_layout(
        name: str,
        bottom: str,
        footer: bool,
        header: bool = False,
        numbers: str = "1",
        landscape: bool = False,
    ) -> PageLayout:
        layout = PageLayout(name=name)
        layout.addElement(
            PageLayoutProperties(
                pagewidth="297mm" if landscape else "210mm",
                pageheight="210mm" if landscape else "297mm",
                printorientation="landscape" if landscape else "portrait",
                margintop="17mm" if header else "25mm",
                marginbottom=bottom,
                marginleft="25mm" if landscape else "36mm",
                marginright="25mm" if landscape else "36mm",
                numformat=numbers,
            )
        )
        if header:
            header_style = HeaderStyle()
            header_style.addElement(
                HeaderFooterProperties(minheight="4mm", marginbottom="4mm")
            )
            layout.addElement(header_style)
        if footer:
            footer_style = FooterStyle()
            footer_style.addElement(
                HeaderFooterProperties(minheight="5mm", margintop="8mm")
            )
            layout.addElement(footer_style)
        doc.automaticstyles.addElement(layout)
        return layout

    def page_footer(master: MasterPage) -> None:
        footer = Footer()
        number = P(stylename="Footer")
        number.addElement(PageNumber(selectpage="current"))
        footer.addElement(number)
        master.addElement(footer)

    if report:
        build_report_pages(doc, page_layout, page_footer)
        if with_sample:
            sample.add(doc)
        else:
            doc.text.addElement(P(stylename="Text_20_body", text=""))
    else:
        first = MasterPage(
            name="First_20_Page",
            displayname="First Page",
            pagelayoutname=page_layout("pm1", "31mm", False),
            nextstylename="Standard",
        )
        doc.masterstyles.addElement(first)
        standard = MasterPage(
            name="Standard", pagelayoutname=page_layout("pm2", "18mm", True)
        )
        page_footer(standard)
        doc.masterstyles.addElement(standard)
        landscape = MasterPage(
            name="Apaisada",
            displayname="Apaisada",
            pagelayoutname=page_layout("pm3", "18mm", True, landscape=True),
        )
        page_footer(landscape)
        doc.masterstyles.addElement(landscape)
        # The first paragraph starts on "First Page": no page number, as in the PDF.
        start = Style(
            name="P1",
            family="paragraph",
            parentstylename="Title",
            masterpagename="First_20_Page",
        )
        doc.automaticstyles.addElement(start)
        doc.text.addElement(P(stylename=start, text="Título del documento"))
        doc.text.addElement(P(stylename="Text_20_body", text=""))

    # Embed the fonts on save, so the template looks the same without Charis SIL
    # installed.
    settings = ConfigItemSet(name="ooo:configuration-settings")
    for name in ("EmbedFonts", "EmbedOnlyUsedFonts"):
        item = ConfigItem(name=name, type="boolean")
        item.addText("true")
        settings.addElement(item)
    doc.settings.addElement(settings)

    doc.save(path)


def build_report_pages(doc, page_layout, page_footer) -> None:
    """Report cover, front matter and body, with their page and paragraph styles."""
    cover = MasterPage(
        name="Portada",
        displayname="Portada",
        pagelayoutname=page_layout("pm1", "31mm", False),
    )
    front = MasterPage(
        name="Preliminares",
        displayname="Preliminares",
        pagelayoutname=page_layout("pm2", "18mm", True, numbers="i"),
    )
    page_footer(front)
    masters = [cover, front]
    # Body and landscape pages carry the document title (File > Properties >
    # Title) in the running header.
    for name, layout in (
        ("Cuerpo", page_layout("pm3", "18mm", True, header=True)),
        ("Apaisada", page_layout("pm4", "18mm", True, header=True, landscape=True)),
    ):
        master = MasterPage(name=name, displayname=name, pagelayoutname=layout)
        header = Header()
        running = P(stylename="Header")
        running.addElement(Title())
        header.addElement(running)
        master.addElement(header)
        page_footer(master)
        masters.append(master)
    for master in masters:
        doc.masterstyles.addElement(master)

    para_style(
        doc,
        "Header",
        "Header",
        parent="Header_20_and_20_Footer",
        cls="extra",
        para={"textalign": "end"},
        text={"fontsize": pt(9), "fontstyle": "italic", "color": GREY},
    )
    # .cover-logo: up to 22 mm high, 8 mm above the entity.
    para_style(
        doc,
        "Portada_20_logo",
        "Portada: logotipo",
        parent="Standard",
        cls="chapter",
        para={"marginbottom": "8mm"},
    )
    para_style(
        doc,
        "Portada_20_entidad",
        "Portada: entidad",
        parent="Standard",
        cls="chapter",
        para={"marginbottom": "30mm"},
    )
    para_style(
        doc,
        "Portada_20_titulo",
        "Portada: título",
        parent="Heading",
        cls="chapter",
        para={"marginbottom": em(0.4), **fixed(SIZE * 2.2, 1.15)},
        text={"fontsize": em(2.2)},
        nextstylename="Portada_20_subtitulo",
    )
    para_style(
        doc,
        "Portada_20_subtitulo",
        "Portada: subtítulo",
        parent="Standard",
        cls="chapter",
        text={"fontsize": em(1.25), "fontstyle": "italic"},
    )
    para_style(
        doc,
        "Portada_20_autor",
        "Portada: autor",
        parent="Standard",
        cls="chapter",
        para={"marginbottom": em(0.2)},
        text={"fontweight": "bold"},
        nextstylename="Portada_20_datos",
    )
    para_style(
        doc,
        "Portada_20_datos",
        "Portada: datos",
        parent="Standard",
        cls="chapter",
        para={"marginbottom": em(0.2)},
    )
    para_style(
        doc,
        "Contents_20_Heading",
        "Contents Heading",
        parent="Heading",
        cls="index",
        para={"margintop": "0pt", "marginbottom": em(0.5), **fixed(SIZE * 1.15, 1.2)},
        text={"fontsize": em(1.15)},
    )
    # Titles of the indexes that follow the table of contents on its page.
    para_style(
        doc,
        "Titulo_20_de_20_indice",
        "Título de índice",
        parent="Contents_20_Heading",
        cls="index",
        para={"margintop": em(2.2)},
    )
    # Appendix heading: unnumbered (write "Anexo A. …"), on a new page, listed
    # in the table of contents at level 1.
    para_style(
        doc,
        "Anexo",
        "Anexo",
        parent="Titulo_20_sin_20_numero",
        para={"breakbefore": "page", "margintop": "0pt"},
        nextstylename="Text_20_body",
    )
    # Table of contents: number in a 2.2 em column, page number flush right.
    text_width = f"{TEXT_WIDTH}mm"
    for level, indent, bold in ((1, "0pt", True), (2, em(2.2), False)):
        style = Style(
            name=f"Contents_20_{level}",
            family="paragraph",
            displayname=f"Contents {level}",
            parentstylename="Standard",
            attributes={"class": "index"},
        )
        props = ParagraphProperties(
            marginleft=indent, margintop=em(0.55) if level == 1 else "0pt"
        )
        tabs = TabStops()
        tabs.addElement(TabStop(position=em(2.2 if level == 1 else 2.6)))
        tabs.addElement(TabStop(position=text_width, type="right", leaderstyle="none"))
        props.addElement(tabs)
        style.addElement(props)
        style.addElement(TextProperties(fontweight="bold" if bold else "normal"))
        doc.styles.addElement(style)
    # Indexes of figures and tables: caption text, page number flush right.
    for name, display in (
        ("Illustration_20_Index_20_1", "Illustration Index 1"),
        ("Table_20_index_20_1", "Table index 1"),
    ):
        style = Style(
            name=name,
            family="paragraph",
            displayname=display,
            parentstylename="Standard",
            attributes={"class": "index"},
        )
        props = ParagraphProperties(marginbottom=em(0.2))
        tabs = TabStops()
        tabs.addElement(TabStop(position=text_width, type="right", leaderstyle="none"))
        props.addElement(tabs)
        style.addElement(props)
        doc.styles.addElement(style)

    # Frame at the foot of the cover for author, date and version.
    frame_style = Style(name="fr1", family="graphic", parentstylename="Frame")
    frame_style.addElement(
        GraphicProperties(
            verticalpos="bottom",
            verticalrel="page-content",
            horizontalpos="left",
            horizontalrel="page-content",
            wrap="none",
            border="none",
            padding="0cm",
            fill="none",
            backgroundcolor="transparent",
            shadow="none",
            marginleft="0cm",
            marginright="0cm",
            margintop="0cm",
            marginbottom="0cm",
        )
    )
    doc.automaticstyles.addElement(frame_style)

    def starts(name: str, parent: str, master: str, page: str | None) -> Style:
        style = Style(
            name=name, family="paragraph", parentstylename=parent, masterpagename=master
        )
        if page:
            style.addElement(ParagraphProperties(pagenumber=page))
        doc.automaticstyles.addElement(style)
        return style

    # Cover data lives in File > Properties: Title and Subject (Description tab)
    # and the custom properties below; the cover shows them as fields.
    doc.meta.addElement(dc.Title(text="Título del informe"))
    doc.meta.addElement(dc.Subject(text="Subtítulo del informe"))
    fields = {
        "Entidad": "Entidad o empresa",
        "Autor": "Autor",
        "Fecha": "Fecha",
        "Versión": "1.0",
    }
    for name, value in fields.items():
        doc.meta.addElement(meta.UserDefined(name=name, valuetype="string", text=value))

    def field(style: str, name: str, prefix: str = "") -> P:
        paragraph = P(stylename=style, text=prefix)
        paragraph.addElement(UserDefined(name=name, text=fields[name]))
        return paragraph

    body = doc.text
    # Logo: click the placeholder to insert the image; delete the paragraph if
    # there is none.
    logo = P(stylename=starts("P1", "Portada_20_logo", "Portada", None))
    logo.addElement(
        Placeholder(placeholdertype="image", description="Logotipo", text="<Logotipo>")
    )
    body.addElement(logo)
    entity = field("Portada_20_entidad", "Entidad")
    frame = Frame(
        stylename=frame_style,
        anchortype="paragraph",
        width=text_width,
        name="Datos de portada",
    )
    box = TextBox(minheight="2cm")
    box.addElement(field("Portada_20_autor", "Autor"))
    box.addElement(field("Portada_20_datos", "Fecha"))
    box.addElement(field("Portada_20_datos", "Versión", "Versión "))
    frame.addElement(box)
    entity.addElement(frame)
    body.addElement(entity)
    cover_title = P(stylename="Portada_20_titulo")
    cover_title.addElement(Title(text="Título del informe"))
    body.addElement(cover_title)
    subtitle = P(stylename="Portada_20_subtitulo")
    subtitle.addElement(Subject(text="Subtítulo del informe"))
    body.addElement(subtitle)

    hint = "Actualiza el índice: clic derecho > Actualizar índice"
    toc = TableOfContent(name="Índice", protected="true")
    source = TableOfContentSource(
        outlinelevel="2", useoutlinelevel="true", useindexsourcestyles="true"
    )
    title_template = IndexTitleTemplate(stylename="Contents_20_Heading")
    title_template.addText("Índice")
    source.addElement(title_template)
    for level in (1, 2):
        entry = TableOfContentEntryTemplate(
            outlinelevel=str(level), stylename=f"Contents_20_{level}"
        )
        entry.addElement(IndexEntryChapter())
        entry.addElement(
            IndexEntryTabStop(position=em(2.2 if level == 1 else 2.6), type="left")
        )
        entry.addElement(IndexEntryText())
        entry.addElement(IndexEntryTabStop(type="right", leaderchar=" "))
        entry.addElement(IndexEntryPageNumber())
        source.addElement(entry)
    extra = IndexSourceStyles(outlinelevel="1")
    for name in ("Titulo_20_sin_20_numero", "Anexo"):
        extra.addElement(IndexSourceStyle(stylename=name))
    source.addElement(extra)
    toc.addElement(source)
    index_body = IndexBody()
    index_title = IndexTitle(name="Índice_Head")
    index_title.addElement(
        P(
            stylename=starts("P2", "Contents_20_Heading", "Preliminares", "1"),
            text="Índice",
        )
    )
    index_body.addElement(index_title)
    index_body.addElement(P(stylename="Contents_20_1", text=hint))
    toc.addElement(index_body)
    body.addElement(toc)

    # Indexes of figures and tables, from the captions (Insert > Caption with
    # the Figura and Tabla categories). Delete the one a report does not need.
    for kind, title, sequence, entry_style, cls in (
        (
            "figuras",
            "Índice de figuras",
            "Figure",
            "Illustration_20_Index_20_1",
            (
                IllustrationIndex,
                IllustrationIndexSource,
                IllustrationIndexEntryTemplate,
            ),
        ),
        (
            "tablas",
            "Índice de tablas",
            "Table",
            "Table_20_index_20_1",
            (TableIndex, TableIndexSource, TableIndexEntryTemplate),
        ),
    ):
        index_cls, source_cls, entry_cls = cls
        index = index_cls(name=title, protected="true")
        source = source_cls(
            captionsequencename=sequence,
            captionsequenceformat="text",
            usecaption="true",
        )
        title_template = IndexTitleTemplate(stylename="Titulo_20_de_20_indice")
        title_template.addText(title)
        source.addElement(title_template)
        entry = entry_cls(stylename=entry_style)
        entry.addElement(IndexEntryText())
        entry.addElement(IndexEntryTabStop(type="right", leaderchar=" "))
        entry.addElement(IndexEntryPageNumber())
        source.addElement(entry)
        index.addElement(source)
        index_body = IndexBody()
        index_title = IndexTitle(name=f"{title}_Head")
        index_title.addElement(P(stylename="Titulo_20_de_20_indice", text=title))
        index_body.addElement(index_title)
        index_body.addElement(P(stylename=entry_style, text=hint))
        index.addElement(index_body)
        body.addElement(index)

    body.addElement(
        H(
            outlinelevel=1,
            stylename=starts("P3", "Heading_20_1", "Cuerpo", "1"),
            text="Introducción",
        )
    )


ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "skills/typeset-pdf/assets/fonts"
REFRESH = Path(__file__).resolve().parent / "refresh_sample.py"
# name: (report layout, lorem ipsum sample, LibreOffice export filter)
TARGETS = {
    "documento": (False, False, "ott:writer8_template"),
    "informe": (True, False, "ott:writer8_template"),
    "muestra": (True, True, "odt:writer8"),
}
ALLOWED_FONTS = ("CharisSIL", "Charis SIL", "DejaVuSansMono", "DejaVu Sans Mono")
FONTCONFIG = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>{fonts}</dir>
  <cachedir>{cache}</cachedir>
</fontconfig>
"""


def _prepare_fonts(work: Path) -> Path:
    """Convert the bundled Charis SIL WOFF files to TTF and point fontconfig at them."""
    fonts = work / "fonts"
    fonts.mkdir()
    woffs = sorted(FONTS.glob("charis-sil-*.woff"))
    if len(woffs) != 4:
        raise SystemExit(f"Expected 4 Charis SIL files in {FONTS}, found {len(woffs)}.")
    for woff in woffs:
        font = TTFont(woff)
        font.flavor = None
        font.save(fonts / f"{woff.stem}.ttf")
    config = work / "fonts.conf"
    config.write_text(
        FONTCONFIG.format(fonts=fonts, cache=work / "cache"), encoding="utf-8"
    )
    return config


def _soffice(soffice: str, work: Path, config: Path, *args: str) -> None:
    """Run headless LibreOffice with an isolated profile (works with it open)."""
    env = {**os.environ, "FONTCONFIG_FILE": str(config)}
    profile = (work / "profile").as_uri()
    command = [soffice, f"-env:UserInstallation={profile}", "--headless", *args]
    result = subprocess.run(
        command, check=False, env=env, capture_output=True, text=True, timeout=300
    )
    if result.returncode:
        raise SystemExit(f"soffice failed:\n{result.stderr}")


def _uno_python(soffice: str) -> str | None:
    """A Python that can import uno: LibreOffice's own, or the system one."""
    program = Path(shutil.which(soffice) or soffice).resolve().parent
    candidates = [
        program / "python",  # Windows
        program.parent / "Resources/python",  # macOS app bundle
        Path("/usr/bin/python3"),  # Linux packages (python3-uno)
    ]
    for candidate in candidates:
        if candidate.is_file():
            probe = subprocess.run(
                [str(candidate), "-c", "import uno"], capture_output=True, check=False
            )
            if probe.returncode == 0:
                return str(candidate)
    return None


def _render_sample(soffice: str, work: Path, config: Path) -> tuple[Path, Path]:
    """Refresh the sample's indexes and export it to PDF."""
    odt = work / "out" / "muestra.odt"
    pdf = work / "out" / "muestra.pdf"
    python = _uno_python(soffice)
    if python is None:
        print(
            "warning: no Python with LibreOffice's uno module; "
            "the sample's indexes are left empty",
            file=sys.stderr,
        )
        _soffice(
            soffice,
            work,
            config,
            "--convert-to",
            "pdf",
            "--outdir",
            str(work / "out"),
            str(odt),
        )
        return odt, pdf
    env = {**os.environ, "FONTCONFIG_FILE": str(config)}
    result = subprocess.run(
        [
            python,
            str(REFRESH),
            "--soffice",
            soffice,
            "--profile",
            str(work / "uno-profile"),
            str(odt),
            str(pdf),
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode:
        raise SystemExit(f"refresh_sample.py failed:\n{result.stderr}")
    return odt, pdf


def _check_template(template: Path) -> None:
    """Fail unless the file embeds the four Charis SIL styles and the new styles."""
    with zipfile.ZipFile(template) as archive:
        embedded = [
            n for n in archive.namelist() if n.startswith("Fonts/Font_Charis_SIL")
        ]
        styles = archive.read("styles.xml").decode("utf-8")
    if len(embedded) != 4:
        raise SystemExit(
            f"{template.name}: {len(embedded)} Charis SIL fonts embedded, expected 4."
        )
    for needed in (
        'style:name="Text_20_body"',
        'style:name="Mayúsculas_20_espaciadas"',
        'style:name="Apaisada"',
    ):
        if needed not in styles:
            raise SystemExit(f"{template.name}: {needed} missing from styles.xml.")
    if 'fo:font-variant="small-caps" fo:letter-spacing=' not in styles:
        raise SystemExit(f"{template.name}: small caps lost their letter-spacing.")


def _check_pdf(pdf: Path) -> None:
    """The sample PDF: A4 pages (one landscape) set only in Charis SIL and the mono."""
    from pypdf import PdfReader

    reader = PdfReader(pdf)
    sizes = {
        (round(float(p.mediabox.width)), round(float(p.mediabox.height)))
        for p in reader.pages
    }
    if not {(595, 842), (842, 595)} <= sizes:
        raise SystemExit(
            f"{pdf.name}: page sizes {sizes}, expected A4 portrait and landscape."
        )
    fonts = set()
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        for font in (resources.get("/Font") or {}).values():
            fonts.add(str(font.get_object().get("/BaseFont", "")).split("+")[-1])
    stray = {f for f in fonts if not f.lstrip("/").startswith(ALLOWED_FONTS)}
    if stray:
        raise SystemExit(f"{pdf.name}: unexpected fonts {sorted(stray)}.")
    print(f"checked {pdf.name}: {len(reader.pages)} pages, fonts {sorted(fonts)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="output folder (default: this script's folder)",
    )
    parser.add_argument(
        "--soffice",
        default=shutil.which("soffice") or "soffice",
        help="LibreOffice executable",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="templates-") as tmp:
        work = Path(tmp)
        config = _prepare_fonts(work)
        by_filter: dict[str, list[Path]] = {}
        for name, (report, with_sample, export) in TARGETS.items():
            source = work / f"{name}.odt"
            if export.startswith("odt"):  # same name as the output: keep apart
                source = work / "src" / f"{name}.odt"
                source.parent.mkdir(exist_ok=True)
            build(str(source), report=report, with_sample=with_sample)
            by_filter.setdefault(export, []).append(source)
        for export, sources in by_filter.items():
            _soffice(
                args.soffice,
                work,
                config,
                "--convert-to",
                export,
                "--outdir",
                str(work / "out"),
                *map(str, sources),
            )
        outputs = []
        for name, (_, with_sample, export) in TARGETS.items():
            produced = work / "out" / f"{name}.{export[:3]}"
            _check_template(produced)
            outputs.append(produced)
            if with_sample:
                _, pdf = _render_sample(args.soffice, work, config)
                _check_template(produced)
                _check_pdf(pdf)
                outputs.append(pdf)
        args.out.mkdir(parents=True, exist_ok=True)
        for produced in outputs:
            shutil.copy2(produced, args.out / produced.name)
            print(f"wrote {args.out / produced.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
