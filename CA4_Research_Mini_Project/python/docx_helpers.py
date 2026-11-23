"""Small helpers that build a document in the template's look (Calibri, navy headings)."""
import os
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = "1F3A5F"
d = None
FIG = None


def start(template, fig_dir):
    """open the template, drop its body, keep page setup, styles, header and footer"""
    global d, FIG
    FIG = fig_dir
    if template and os.path.exists(template):
        d = docx.Document(template)
        body = d.element.body
        for el in list(body):
            if el.tag != qn("w:sectPr"):
                body.remove(el)
    else:
        d = docx.Document()
    return d


def runs(p, text, size=None, italic=None, color=None):
    """add text to p; **x** marks bold, __x__ marks italic"""
    for i, part in enumerate(text.split("**")):
        if not part:
            continue
        bold = (i % 2 == 1) or None
        for j, sub in enumerate(part.split("__")):
            if not sub:
                continue
            r = p.add_run(sub)
            r.bold = bold
            if j % 2 == 1 or italic:
                r.italic = True
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = RGBColor.from_string(color)
    return p


def para(text, align=None, after=6, **kw):
    p = d.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return runs(p, text, **kw)


def h1(t):
    d.add_paragraph(t, style="Heading 1")


def h2(t):
    d.add_paragraph(t, style="Heading 2")


def bullet(text):
    p = d.add_paragraph(style="List Paragraph")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Cm(0.76)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    return runs(p, "•  " + text)


def caption(text):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9.5)


def figure(name, width_cm, cap):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(os.path.join(FIG, name), width=Cm(width_cm))
    caption(cap)


def code(text):
    """monospace block"""
    for line in text.strip("\n").split("\n"):
        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.6)
        r = p.add_run(line if line else " ")
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(8.5)
    d.add_paragraph().paragraph_format.space_after = Pt(4)


def table(title, header, rows, widths=None, first_left=True, size=9):
    cap = d.add_paragraph()
    cap.paragraph_format.keep_with_next = True
    cap.paragraph_format.space_after = Pt(3)
    r = cap.add_run(title)
    r.italic = True
    r.font.size = Pt(9.5)
    t = d.add_table(rows=1 + len(rows), cols=len(header))
    tblPr = t._tbl.tblPr
    jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center"); tblPr.append(jc)
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "999999")
        b.append(e)
    tblPr.append(b)
    for ri, row in enumerate([header] + rows):
        tr = t.rows[ri]
        trPr = tr._tr.get_or_add_trPr()
        if ri == 0:
            th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        trPr.append(OxmlElement("w:cantSplit"))
        for ci, val in enumerate(row):
            c = tr.cells[ci]
            if widths:
                c.width = Cm(widths[ci])
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            if not (first_left and ci == 0):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if ri < len(rows):  # keep the whole table on one page
                p.paragraph_format.keep_with_next = True
            run = p.add_run(str(val))
            run.font.size = Pt(size)
            if ri == 0:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), NAVY)
                c._tc.get_or_add_tcPr().append(shd)
    sp = d.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)


def page_break():
    d.add_page_break()


def save(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d.save(path)
