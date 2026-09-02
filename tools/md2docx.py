# -*- coding: utf-8 -*-
"""
md2docx.py — 专利交底书 Markdown -> 模板化 docx 转写脚本
用法:
    .venv_patent/Scripts/python.exe tools/md2docx.py <input.md> <output.docx>
依赖: python-docx, matplotlib(mathtext), node/npx + @mermaid-js/mermaid-cli (复用本机 Edge)
mermaid 渲染失败时: 该代码块转为等宽文本段落 + [图渲染失败] 标注, 不静默丢弃
公式渲染失败时: 转为文本段落 + [公式渲染失败, 见代码块] 标注
"""
import re
import sys
import os
import subprocess
import tempfile
import shutil

import docx
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(BASE, '..', 'templates', '技术交底书模板-发明新型.docx')
VENV_PY = os.path.join(BASE, '..', '.venv_patent', 'Scripts', 'python.exe')
PUPPETEER_CFG = os.path.join(BASE, 'puppeteer-edge.json')
MMDC = 'npx.cmd' if os.name == 'nt' else 'npx'

# 模板章节标题 (2026-09 新版模板: 零~八 + 3 个无编号节)
SECTION_TITLES = [
    '零、术语定义和解释', '一、发明名称', '二、技术领域',
    '三、现有技术的技术方案', '四、现有技术的缺点及本申请提案要解决的技术问题',
    '五、本申请提案的技术方案的详细阐述', '六、本申请提案的关键点和欲保护点',
    '七、与第三条中最接近的现有技术相比，本申请提案有何技术优点',
    '八、发散思维以及规避方案思考',
    '本申请提案的商业价值',
    '本申请提案的侵权证据可获得性/标准进展情况',
    '其他有助于理解本申请提案的技术资料',
]


# ---------------- Markdown 解析 ----------------

class Block:
    def __init__(self, kind, content, meta=None):
        self.kind = kind      # h2/h3/p/ul/ol/table/mermaid/formula/image/caption
        self.content = content
        self.meta = meta or {}


def parse_markdown(md_text):
    """按行解析, 识别章节标题(##/###)与代码块(mermaid/latex), 产出 Block 列表"""
    lines = md_text.splitlines()
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        # 章节标题 (支持 # / ## 作章节级, ### 作模块级)
        m = re.match(r'^(#{1,3})\s+(.*)$', stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            blocks.append(Block('h2' if level <= 2 else 'h3', title, {'level': level}))
            i += 1
            continue
        # 代码块
        if stripped.startswith('```'):
            lang = stripped[3:].strip().lower()
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing
            code = '\n'.join(buf).strip()
            if lang in ('mermaid', 'mmd'):
                blocks.append(Block('mermaid', code))
            elif lang in ('latex', 'tex', 'math', 'formula'):
                blocks.append(Block('formula', code))
            else:
                blocks.append(Block('code', code, {'lang': lang}))
            continue
        # 表格
        if stripped.startswith('|') and i + 1 < n and re.match(r'^\|[\s:|-]+\|$', lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip('|').split('|')]
            rows = []
            i += 2
            while i < n and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            blocks.append(Block('table', rows, {'header': header}))
            continue
        # 图片
        m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
        if m:
            blocks.append(Block('image', m.group(2), {'caption': m.group(1)}))
            i += 1
            continue
        # 列表
        if re.match(r'^[-*]\s+', stripped):
            buf = []
            while i < n and re.match(r'^[-*]\s+', lines[i].strip()):
                buf.append(re.sub(r'^[-*]\s+', '', lines[i].strip()))
                i += 1
            blocks.append(Block('ul', buf))
            continue
        if re.match(r'^\d+[.、]\s+', stripped):
            buf = []
            while i < n and re.match(r'^\d+[.、]\s+', lines[i].strip()):
                buf.append(re.sub(r'^\d+[.、]\s+', '', lines[i].strip()))
                i += 1
            blocks.append(Block('ol', buf))
            continue
        # 普通段落(合并连续行)
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not lines[i].strip().startswith('```') \
                and not re.match(r'^(#{2,3}|[-*]|\d+[.、]|\|)', lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(Block('p', ' '.join(buf)))
    return blocks


# ---------------- Mermaid 渲染 ----------------

def render_mermaid(code, out_png, workdir):
    """用 mermaid-cli + Edge 渲染 mermaid 代码为 PNG; 返回 (ok, error_msg)"""
    mmd = os.path.join(workdir, 'chart.mmd')
    with open(mmd, 'w', encoding='utf-8') as f:
        f.write(code)
    env = dict(os.environ)
    env['PUPPETEER_EXECUTABLE_PATH'] = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    cmd = [MMDC, '-y', '@mermaid-js/mermaid-cli', '-p', PUPPETEER_CFG,
           '-i', mmd, '-o', out_png, '-b', 'white', '-s', '2']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, shell=(os.name == 'nt'))
        if r.returncode == 0 and os.path.exists(out_png) and os.path.getsize(out_png) > 0:
            return True, ''
        return False, (r.stderr or r.stdout or '')[-800:]
    except Exception as e:
        return False, str(e)[-800:]


# ---------------- LaTeX 渲染 (matplotlib mathtext) ----------------

def render_formula(formula, out_png):
    """用 matplotlib mathtext 渲染 LaTeX 公式为 PNG; 返回 (ok, error_msg)"""
    code = r'''
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
f = r"""%s"""
fig = plt.figure(figsize=(0.01, 0.01))
try:
    t = fig.text(0, 0, f, fontsize=16)
    fig.canvas.draw()
    bbox = t.get_window_extent()
    w, h = bbox.width, bbox.height
    plt.close(fig)
    fig = plt.figure(figsize=(w/100 + 0.2, h/100 + 0.2))
    t = fig.text(0.5, 0.5, f, fontsize=16, ha='center', va='center')
    fig.savefig(r"%s", dpi=200, transparent=True, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    print("OK")
except Exception as e:
    print("ERR:", e)
''' % (formula.replace('\\', '\\\\').replace('"""', '\\"\\"\\"'), out_png)
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    try:
        r = subprocess.run([VENV_PY, '-c', code], capture_output=True, text=True, timeout=60, env=env)
        out = (r.stdout or '') + (r.stderr or '')
        if 'OK' in out and os.path.exists(out_png) and os.path.getsize(out_png) > 0:
            return True, ''
        return False, out[-600:]
    except Exception as e:
        return False, str(e)[-600:]


# ---------------- docx 构建 ----------------

def set_run_font(run, size=None, bold=None, name='宋体'):
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    run.font.name = name
    r = run._element.rPr.rFonts if run._element.rPr is not None else None
    if r is not None:
        r.set(qn('w:eastAsia'), name)


def add_para(doc, text, size=11, bold=False, indent=None, style=None):
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    if indent is not None:
        p.paragraph_format.first_line_indent = Pt(indent)
    return p


def add_heading_para(doc, text, level=2):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, size=14 if level == 2 else 12, bold=True)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_table(doc, header, rows):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
    try:
        tbl.style = 'Table Grid'
    except KeyError:
        # 模板无 Table Grid 样式: 手动加边框
        from docx.oxml import OxmlElement
        tblPr = tbl._tbl.tblPr
        borders = OxmlElement('w:tblBorders')
        for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement(f'w:{edge}')
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), '4')
            el.set(qn('w:color'), '000000')
            borders.append(el)
        tblPr.append(borders)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(header):
        cell = tbl.rows[0].cells[j]
        cell.text = ''
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, size=10, bold=True)
    for ri, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = tbl.rows[ri].cells[j]
            cell.text = ''
            run = cell.paragraphs[0].add_run(val)
            set_run_font(run, size=10)
    return tbl


def build_docx(md_text, out_path, template_path=DEFAULT_TEMPLATE, workdir=None, md_dir=None):
    doc = Document(template_path)
    blocks = parse_markdown(md_text)
    md_dir = md_dir or os.path.dirname(os.path.abspath(out_path))

    def resolve_img(src):
        if os.path.isabs(src):
            return src
        cand = os.path.join(md_dir, src)
        if os.path.exists(cand):
            return cand
        return src  # 让上层报 [图片缺失]

    # 封面发明名称回填 (模板封面表格第2行: 发明名称)
    inv_name = None
    for b in blocks:
        if b.kind == 'h2' and b.content.startswith('一、'):
            # 发明名称是下一段
            break
    idx = next((i for i, b in enumerate(blocks) if b.kind == 'h2' and b.content.startswith('一、')), None)
    if idx is not None and idx + 1 < len(blocks) and blocks[idx + 1].kind in ('p',):
        inv_name = blocks[idx + 1].content.strip()
    if inv_name and doc.tables:
        cover = doc.tables[0]
        if len(cover.rows) > 1:
            cell = cover.rows[1].cells[1]
            cell.text = ''
            run = cell.paragraphs[0].add_run(inv_name)
            set_run_font(run, size=11, bold=False)

    # 按模板骨架段落定位: 删除模板 body 中"附件3-"标题行及从"零、术语定义和解释"开始的所有骨架段, 重新写入
    body = doc.element.body
    to_remove = []
    seen_zero = False
    for child in body.iterchildren():
        tag = child.tag.split('}')[1]
        if tag == 'p':
            txt = ''.join(t.text or '' for t in child.iter(qn('w:t')))
            if txt.strip().startswith('附件3-'):
                to_remove.append(child)
                continue
            if txt.strip().startswith('零、术语定义和解释'):
                seen_zero = True
            if seen_zero:
                to_remove.append(child)
        elif tag == 'tbl' and seen_zero:
            to_remove.append(child)
    for child in to_remove:
        body.remove(child)

    # 追加内容
    pending_caption = None
    for b in blocks:
        if b.kind == 'h2':
            add_heading_para(doc, b.content, 2)
        elif b.kind == 'h3':
            add_heading_para(doc, b.content, 3)
        elif b.kind == 'p':
            add_para(doc, b.content, size=11)
        elif b.kind == 'ul':
            for item in b.content:
                add_para(doc, '• ' + item, size=11, indent=21)
        elif b.kind == 'ol':
            for j, item in enumerate(b.content, 1):
                add_para(doc, f'{j}. {item}', size=11, indent=21)
        elif b.kind == 'table':
            add_table(doc, b.meta['header'], b.content)
        elif b.kind == 'mermaid':
            wd = workdir or tempfile.mkdtemp(prefix='mermaid_')
            png = os.path.join(wd, f'fig_{len(doc.inline_shapes) + 1}.png')
            ok, err = render_mermaid(b.content, png, wd)
            if ok:
                try:
                    doc.add_picture(png, width=Inches(5.5))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception as e:
                    add_para(doc, f'[图渲染失败: {e}]', size=9)
                    add_para(doc, b.content, size=9)
            else:
                add_para(doc, f'[Mermaid 渲染失败, 原图代码: {err[:100]}]', size=9)
                add_para(doc, b.content, size=9)
        elif b.kind == 'formula':
            wd = workdir or tempfile.mkdtemp(prefix='latex_')
            png = os.path.join(wd, f'eq_{len(doc.inline_shapes) + 1}.png')
            ok, err = render_formula(b.content, png)
            if ok:
                try:
                    doc.add_picture(png, width=Inches(3.5))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception as e:
                    add_para(doc, f'[公式渲染失败: {e}]', size=9)
                    add_para(doc, b.content, size=9)
            else:
                add_para(doc, f'[公式渲染失败, 原公式: {err[:100]}]', size=9)
                add_para(doc, b.content, size=9)
        elif b.kind == 'code':
            add_para(doc, b.content, size=9)
        elif b.kind == 'image':
            src = resolve_img(b.content)
            if os.path.exists(src):
                try:
                    doc.add_picture(src, width=Inches(5.0))
                except Exception:
                    add_para(doc, f'[图片无法嵌入: {src}]', size=9)
            else:
                add_para(doc, f'[图片缺失: {src}]', size=9)
        elif b.kind == 'caption':
            p = add_para(doc, b.content, size=9)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.save(out_path)
    return out_path


def main():
    if len(sys.argv) < 3:
        print('用法: md2docx.py <input.md> <output.docx>')
        sys.exit(1)
    md_path, out_path = sys.argv[1], sys.argv[2]
    with open(md_path, encoding='utf-8') as f:
        md_text = f.read()
    build_docx(md_text, out_path)
    print(f'OK -> {out_path}')


if __name__ == '__main__':
    main()
