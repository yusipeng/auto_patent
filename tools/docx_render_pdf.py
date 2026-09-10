# -*- coding: utf-8 -*-
"""docx_render_pdf.py — 用本机 Word 把 docx 渲染为 PDF（排版验证用）

用法:
    .venv_patent/Scripts/python.exe tools/docx_render_pdf.py <in.docx> <out.pdf>

依赖: 本机安装 Word(2016+) 与 pywin32（.venv_patent 已装）。
用于核对 md2docx 输出与"用户定稿格式"的渲染一致性（页数/字体/编号），
也可作为交付前的人工抽查手段（渲染件供肉眼检查）。
"""
import sys
import os
import win32com.client as wc


def render(src, dst):
    if os.path.exists(dst):
        os.remove(dst)
    word = wc.DispatchEx('Word.Application')
    try:
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(os.path.abspath(src), ReadOnly=True, AddToRecentFiles=False)
        doc.SaveAs2(os.path.abspath(dst), FileFormat=17)  # wdFormatPDF
        doc.Close(SaveChanges=False)
        return True
    finally:
        try:
            word.Quit()
        except Exception:
            pass


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: docx_render_pdf.py <in.docx> <out.pdf>')
        sys.exit(1)
    ok = render(sys.argv[1], sys.argv[2])
    print('OK' if ok else 'FAIL', '->', sys.argv[2],
          os.path.getsize(sys.argv[2]) if os.path.exists(sys.argv[2]) else '')
