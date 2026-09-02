# -*- coding: utf-8 -*-
"""extract_comments.py — 提取 docx 中的 Word 批注(comments)
用法: .venv_patent/Scripts/python.exe tools/extract_comments.py <in.docx>
输出: 每条批注 = 批注文本 + 锚定段落文本, 打印到 stdout
"""
import sys, zipfile, re
from xml.etree import ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def extract(docx_path):
    z = zipfile.ZipFile(docx_path)
    if 'word/comments.xml' not in z.namelist():
        return []
    root = ET.fromstring(z.read('word/comments.xml'))
    doc_xml = z.read('word/document.xml').decode('utf-8')
    comments = []
    for c in root.findall('w:comment', NS):
        cid = c.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id')
        author = c.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author')
        text = ''.join(t.text or '' for t in c.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        # 找锚定段落: commentRangeStart 前的段落文本
        anchor = ''
        m = re.search(r'<w:commentRangeStart w:id="%s"/>.*?</w:p>|<w:commentRangeStart w:id="%s"/>.{0,2000}?<w:t>([^<]+)</w:t>' % (cid, cid), doc_xml, re.S)
        if m:
            anchor = re.sub(r'<[^>]+>', '', m.group(0))[:300]
        comments.append({'id': cid, 'author': author, 'text': text, 'anchor': anchor.strip()})
    return comments

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: extract_comments.py <in.docx>')
        sys.exit(1)
    for c in extract(sys.argv[1]):
        print(f"[{c['id']}] {c['author']}: {c['text']}")
        if c['anchor']:
            print(f"   锚定: {c['anchor'][:200]}")
