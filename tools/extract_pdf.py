# -*- coding: utf-8 -*-
"""extract_pdf.py — 提取 PDF 全文文本为 .txt
用法: .venv_patent/Scripts/python.exe tools/extract_pdf.py <in.pdf> [out.txt]
"""
import sys, os
import pymupdf

def extract(pdf_path, out_txt=None):
    doc = pymupdf.open(pdf_path)
    parts = []
    for page in doc:
        parts.append(page.get_text('text'))
    text = '\n\n'.join(parts)
    if out_txt is None:
        out_txt = os.path.splitext(pdf_path)[0] + '.txt'
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(text)
    return out_txt, len(text)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: extract_pdf.py <in.pdf> [out.txt]')
        sys.exit(1)
    out, n = extract(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f'OK {out} ({n} chars)')
