#!/usr/bin/env python3
"""Build the LibreOffice Writer templates with the typeset-pdf style.

Translates skills/typeset-pdf/assets/base.css and report.css into Writer styles
and writes two templates next to this script:

  documento.ott  Charis SIL 11 pt, 132 % leading, A4 with 25/36/31/36 mm
                 margins, page number at the foot except on the first page.
  informe.ott    The same plus the report layout: cover without a number, table
                 of contents in roman numerals, body in arabic from 1 with the
                 title in the header, headings numbered 1 / 1.1 / 1.1.1.

LibreOffice converts the generated .odt files to .ott and embeds Charis SIL,
taken from the skill's own fonts (no need to install it). Needs LibreOffice
(soffice) and fontconfig (Linux, macOS); run it as

  uv run --with odfpy --with fonttools python templates/documents/build_templates.py
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

from fontTools.ttLib import TTFont
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
    IndexBody,
    IndexEntryChapter,
    IndexEntryPageNumber,
    IndexEntryTabStop,
    IndexEntryText,
    IndexTitle,
    IndexTitleTemplate,
    ListLevelStyleBullet,
    ListLevelStyleNumber,
    ListStyle,
    OutlineLevelStyle,
    OutlineStyle,
    P,
    PageNumber,
    TableOfContent,
    TableOfContentEntryTemplate,
    TableOfContentSource,
    Title,
)

BODY = "Charis SIL"
MONO = "DejaVu Sans Mono"
SIZE = 11.0  # pt
INK = "#111111"
GREY = "#444444"


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


def build(path: str, report: bool = False) -> None:
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

    # ---- Character styles ----
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
            {"fontvariant": "small-caps", "letterspacing": "0.06em"},
        ),
    ):
        style = Style(name=name, family="text", displayname=display)
        style.addElement(TextProperties(**text))
        doc.styles.addElement(style)

    # ---- Lists: 1.4 em indent ----
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
    def page_layout(
        name: str, bottom: str, footer: bool, header: bool = False, numbers: str = "1"
    ) -> PageLayout:
        layout = PageLayout(name=name)
        layout.addElement(
            PageLayoutProperties(
                pagewidth="210mm",
                pageheight="297mm",
                printorientation="portrait",
                margintop="17mm" if header else "25mm",
                marginbottom=bottom,
                marginleft="36mm",
                marginright="36mm",
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
    """Report cover, table of contents and body, with their page and paragraph styles."""
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
    main = MasterPage(
        name="Cuerpo",
        displayname="Cuerpo",
        pagelayoutname=page_layout("pm3", "18mm", True, header=True),
    )
    header = Header()
    # The document title (File > Properties > Title) in the running header.
    running = P(stylename="Header")
    running.addElement(Title())
    header.addElement(running)
    main.addElement(header)
    page_footer(main)
    for master in (cover, front, main):
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
    # Table of contents: number in a 2.2 em column, page number flush right.
    text_width = "138mm"
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

    body = doc.text
    first = P(
        stylename=starts("P1", "Portada_20_entidad", "Portada", None),
        text="Entidad o empresa",
    )
    frame = Frame(
        stylename=frame_style,
        anchortype="paragraph",
        width="138mm",
        name="Datos de portada",
    )
    box = TextBox(minheight="2cm")
    box.addElement(P(stylename="Portada_20_autor", text="Autor"))
    box.addElement(P(stylename="Portada_20_datos", text="Fecha"))
    box.addElement(P(stylename="Portada_20_datos", text="Versión 1.0"))
    frame.addElement(box)
    first.addElement(frame)
    body.addElement(first)
    cover_title = P(stylename="Portada_20_titulo")
    cover_title.addElement(Title())
    body.addElement(cover_title)
    body.addElement(P(stylename="Portada_20_subtitulo", text="Subtítulo del informe"))

    toc = TableOfContent(name="Índice", protected="true")
    source = TableOfContentSource(outlinelevel="2", useoutlinelevel="true")
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
    index_body.addElement(
        P(
            stylename="Contents_20_1",
            text="Actualiza el índice: clic derecho > Actualizar índice",
        )
    )
    toc.addElement(index_body)
    body.addElement(toc)

    body.addElement(
        H(
            outlinelevel=1,
            stylename=starts("P3", "Heading_20_1", "Cuerpo", "1"),
            text="Introducción",
        )
    )
    body.addElement(P(stylename="Text_20_body", text=""))


ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "skills/typeset-pdf/assets/fonts"
TEMPLATES = {"documento": False, "informe": True}
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


def _convert(soffice: str, sources: list[Path], work: Path, config: Path) -> None:
    """Save the .odt files as .ott with LibreOffice, which embeds the fonts."""
    env = {**os.environ, "FONTCONFIG_FILE": str(config)}
    profile = (
        work / "profile"
    ).as_uri()  # isolated profile: works with LibreOffice open
    command = [
        soffice,
        f"-env:UserInstallation={profile}",
        "--headless",
        "--convert-to",
        "ott:writer8_template",
        "--outdir",
        str(work / "out"),
        *map(str, sources),
    ]
    result = subprocess.run(
        command, check=False, env=env, capture_output=True, text=True, timeout=300
    )
    if result.returncode:
        raise SystemExit(f"soffice failed:\n{result.stderr}")


def _check(template: Path) -> None:
    """Fail unless the template embeds the four Charis SIL styles."""
    with zipfile.ZipFile(template) as archive:
        embedded = [
            n for n in archive.namelist() if n.startswith("Fonts/Font_Charis_SIL")
        ]
        styles = archive.read("styles.xml").decode("utf-8")
    if len(embedded) != 4:
        raise SystemExit(
            f"{template.name}: {len(embedded)} Charis SIL fonts embedded, expected 4."
        )
    if 'style:name="Text_20_body"' not in styles:
        raise SystemExit(f"{template.name}: Body Text style missing.")


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
        sources = []
        for name, report in TEMPLATES.items():
            source = work / f"{name}.odt"
            build(str(source), report=report)
            sources.append(source)
        _convert(args.soffice, sources, work, config)
        args.out.mkdir(parents=True, exist_ok=True)
        for name in TEMPLATES:
            template = work / "out" / f"{name}.ott"
            _check(template)
            shutil.copy2(template, args.out / template.name)
            print(f"wrote {args.out / template.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
