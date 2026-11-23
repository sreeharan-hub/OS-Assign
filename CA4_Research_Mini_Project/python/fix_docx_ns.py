"""Repair a .docx whose XML namespace prefixes were renamed (ns1, ns2, ...) so Word calls it corrupt.

usage: python fix_docx_ns.py REFERENCE.docx BROKEN.docx
REFERENCE is an intact copy of the same document (its root namespace declarations are copied).
Also removes duplicate w14:paraId / w14:textId values created by cloning paragraphs.
"""
import re, shutil, sys, zipfile

ref, bad = sys.argv[1], sys.argv[2]
rz = zipfile.ZipFile(ref)
ref_root = re.search(r"<w:document[^>]*>", rz.read("word/document.xml").decode("utf-8")).group(0)
ref_decl = dict((u, p) for p, u in re.findall(r'xmlns:(\w+)="([^"]+)"', ref_root))   # uri -> prefix
ignorable = re.search(r'mc:Ignorable="[^"]*"', ref_root).group(0)

zin = zipfile.ZipFile(bad)
tmp = bad + ".fixed"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            s = data.decode("utf-8")
            root = re.search(r"<w:document[^>]*>", s).group(0)
            extra = []
            uris = dict(re.findall(r'xmlns:(ns\d+)="([^"]+)"', root))
            for nsp, uri in uris.items():
                if uri not in ref_decl:      # declared lower in the reference: keep the prefix, declare it on the root
                    extra.append(f' xmlns:{nsp}="{uri}"')
                    continue
                s = s.replace(nsp + ":", ref_decl[uri] + ":")
            new_root = re.search(r"<w:document[^>]*>", ref_root + "").group(0)
            s = re.sub(r"<w:document[^>]*>", lambda m: ref_root[:-1] + "".join(extra) + ">", s, count=1)
            seen = set()

            def dedupe(m):
                if m.group(2) in seen:
                    return ""
                seen.add(m.group(2))
                return m.group(0)

            s = re.sub(r'( w14:paraId="([0-9A-F]+)")', dedupe, s)
            data = s.encode("utf-8")
        zout.writestr(item, data)
shutil.move(tmp, bad)
print("fixed", bad)
