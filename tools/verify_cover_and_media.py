# -*- coding: utf-8 -*-
"""verify_cover_and_media.py — 校验封面发明名称、图片内嵌(非链接)、页数"""
import os, re, sys, zipfile, subprocess
from docx import Document

path = sys.argv[1]
doc = Document(path)

print('=== 封面表格第2行 (发明名称回填) ===')
tbl = doc.tables[0]
for ri, row in enumerate(tbl.rows[:3]):
    cells = [c.text.strip().replace('\n', ' / ') for c in row.cells]
    print(f'  row{ri}: {cells}')

with zipfile.ZipFile(path) as z:
    names = z.namelist()
    media = sorted(n for n in names if n.startswith('word/media/'))
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
    ext = re.findall(r'TargetMode="External"[^>]*Target="([^"]+)"', rels)
    doc_xml = z.read('word/document.xml').decode('utf-8')
    n_blip = doc_xml.count('<a:blip')

print(f'\n=== 内嵌媒体 ===')
print(f'包内 word/media/ 文件数: {len(media)}')
for m in media:
    print(f'  {m}  {z.getinfo(m).file_size} bytes')
print(f'document.xml 中 blip 引用数: {n_blip}')
print(f'外部链接关系(非内嵌): {ext if ext else "NONE"}')

# 页数: 优先 Word COM (本机 Office), 其次 LibreOffice
print('\n=== 页数 ===')
n_pages = None
try:
    import win32com.client as wc
    word = wc.Dispatch('Word.Application')
    word.Visible = False
    try:
        d = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
        try:
            n_pages = d.ComputeStatistics(2)  # wdStatisticPages
        finally:
            d.Close(False)
    finally:
        word.Quit()
except Exception as e:
    print('Word COM 不可用:', str(e)[:120])

if n_pages is not None:
    print(f'WORD_PAGES={n_pages}')
else:
    soffice = None
    for cand in (r'C:\Program Files\LibreOffice\program\soffice.exe',
                 r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'):
        if os.path.exists(cand):
            soffice = cand
            break
    if soffice:
        tmp = os.path.join(os.environ.get('TEMP', r'C:\Users\<user>\AppData\Local\Temp'), 'v9_pdf_check')
        os.makedirs(tmp, exist_ok=True)
        pdf = os.path.join(tmp, 'out.pdf')
        r = subprocess.run([soffice, '--headless', '--convert-to', 'pdf', '--outdir', tmp, path],
                           capture_output=True, text=True, timeout=180)
        if os.path.exists(pdf):
            with open(pdf, 'rb') as f:
                data = f.read()
            m = re.findall(rb'/Count\s+(\d+)', data)
            n_pages = max(int(x) for x in m) if m else None
            print(f'PDF /Count: {m} -> 总页数 {n_pages}')
        else:
            print('PDF 转换失败:', r.stderr[-300:])
    else:
        print('未找到 Word/pywin32 与 LibreOffice, 跳过页数统计')
