"""Build paper/os_assig.docx: the course template (Template_Research-Writeup-1.docx) filled with the paper's content.

usage: python make_os_assig.py
Keeps the template's page setup, header and heading look; copies text, tables and figures from the final paper.
"""
import copy, io, re, subprocess
import docx
from docx.oxml.ns import qn

TPL = r"C:\Users\SREEHARAN\Downloads\Template_Research-Writeup-1.docx"
SRC = r"S:\Works\Projects\os-process-vs-thread\paper\Process_vs_Thread_Research_Paper_CA4_final.docx"
OUT = r"S:\Works\Projects\os-process-vs-thread\paper\os_assig.docx"
FIX = r"S:\Works\Projects\os-process-vs-thread\python\fix_docx_ns.py"

tpl = docx.Document(TPL)
src = docx.Document(SRC)
ref = docx.Document(TPL)
head_tpl = copy.deepcopy(ref.paragraphs[0]._p)    # bold, underlined heading of the template
blank_tpl = copy.deepcopy(ref.paragraphs[2]._p)   # empty line of the template

body = tpl.element.body
sect = body.find(qn("w:sectPr"))
for el in list(body):
    if el is not sect:
        body.remove(el)


def add(el):
    sect.addprevious(el)


def heading(text):
    p = copy.deepcopy(head_tpl)
    runs = p.findall(qn("w:r"))
    for r in runs[1:]:
        p.remove(r)
    runs[0].find(qn("w:t")).text = text
    add(p)


def clone(el):
    new = copy.deepcopy(el)
    for blip in new.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
        part = src.part.related_parts[blip.get(qn("r:embed"))]
        rid, _ = tpl.part.get_or_add_image(io.BytesIO(part.blob))
        blip.set(qn("r:embed"), rid)
    for t in new.iter(qn("w:t")):
        if t.text:
            t.text = t.text.replace("Section 9", "the Interpretation section").replace("Section 10", "the Conclusion section")
    return new


skip = True   # title block and Abstract are not in the template
for el in list(src.element.body):
    if el.tag == qn("w:sectPr"):
        continue
    if el.tag == qn("w:p"):
        p = docx.text.paragraph.Paragraph(el, src._body)
        txt = p.text.strip()
        if p.style.name == "Heading 1":
            name = re.sub(r"^\d+\.\s+", "", txt)
            if name == "Problem Identification":
                skip = False
            if skip:
                continue
            if name != "Problem Identification":
                add(copy.deepcopy(blank_tpl))
            heading(name)
            continue
        if skip:
            continue
        if p.style.name == "Heading 2":
            heading(txt)
            continue
    elif el.tag != qn("w:tbl") or skip:
        continue
    add(clone(el))

add(copy.deepcopy(blank_tpl))
tpl.save(OUT)
subprocess.run(["python", FIX, TPL, OUT], check=True)
print("saved", OUT)
