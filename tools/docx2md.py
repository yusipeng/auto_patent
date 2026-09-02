# -*- coding: utf-8 -*-
"""docx2md.py — 已有交底书 docx -> 流水线 md 源（导入工具）
用法: .venv_patent/Scripts/python.exe tools/docx2md.py <in.docx> <out.md> [media_dir]
- 按模板结构提取: 封面字段、零~六章节、表格、内嵌图片(存到 media_dir)
- 模板说明性文字(【...】占位提示)默认剥离, --keep-hints 保留
"""
import sys, os, re
import docx
from docx.oxml.ns import qn

SECTION_RE = re.compile(r'^(零|一|二|三|四|五|六|七|八)、')
HINT_RE = re.compile(r'^[【（(]?[【]|^【')  # 模板提示段落

def iter_block_items(doc):
    """按 body 顺序产出 ('p', paragraph) / ('tbl', table)"""
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split('}')[1]
        if tag == 'p':
            yield ('p', child)
        elif tag == 'tbl':
            yield ('tbl', child)

def para_text(p_el):
    return ''.join(t.text or '' for t in p_el.iter(qn('w:t')))

def is_hint(text):
    return bool(re.match(r'^【[^】]*】$', text.strip())) or text.strip().startswith('【')

def extract_images_from_para(doc, p_el, media_dir, counter):
    """提取段落内的内嵌图片, 返回 md 图片行列表"""
    lines = []
    blips = p_el.findall('.//' + qn('a:blip'))
    for blip in blips:
        rid = blip.get(qn('r:embed'))
        if not rid:
            continue
        try:
            part = doc.part.related_parts[rid]
        except KeyError:
            continue
        counter[0] += 1
        fname = f'img_{counter[0]:02d}.png'
        os.makedirs(media_dir, exist_ok=True)
        with open(os.path.join(media_dir, fname), 'wb') as f:
            f.write(part.blob)
        lines.append(f'![原图{counter[0]}]({os.path.join(media_dir, fname).replace(os.sep, "/")})')
    return lines

def tbl_to_md(t_el):
    rows = t_el.findall(qn('w:tr'))
    if not rows:
        return []
    def row_cells(tr):
        return [''.join(t.text or '' for t in tc.iter(qn('w:t'))).strip()
                for tc in tr.findall(qn('w:tc'))]
    md = []
    first = row_cells(rows[0])
    md.append('| ' + ' | '.join(first) + ' |')
    md.append('|' + '---|' * len(first))
    for tr in rows[1:]:
        cells = row_cells(tr)
        # 对齐列数
        while len(cells) < len(first):
            cells.append('')
        md.append('| ' + ' | '.join(cells[:len(first)]) + ' |')
    return md

def convert(docx_path, out_md, keep_hints=False):
    doc = docx.Document(docx_path)
    media_dir = os.path.join(os.path.dirname(out_md) or '.', 'media')
    counter = [0]
    out = []
    # 封面发明名称: 记录备用, 写入正文「一、发明名称」标题处 (md2docx 回填封面时从那里读取)
    cover_name = None
    if doc.tables:
        cover = doc.tables[0]
        for row in cover.rows:
            cells = [c.text.strip() for c in row.cells]
            if len(cells) >= 2 and cells[0] == '发明名称':
                cover_name = cells[1]
                break
    name_emitted = False
    seen_headings = {'一、发明名称'}  # 封面已写入, 正文重复标题跳过
    in_hint = False  # 跨段 【...】 提示区
    tbl_idx = -1
    for kind, el in iter_block_items(doc):
        if kind == 'p':
            text = para_text(el).strip()
            img_lines = extract_images_from_para(doc, el, media_dir, counter)
            if img_lines:
                out.append('')
                out.extend(img_lines)
                out.append('')
            if not text:
                continue
            # 封面杂项行跳过
            if text in ('公司专利申请', '技术交底书', '〔集团名称〕', '〔集团名称〕'):
                continue
            m = SECTION_RE.match(text)
            if m and len(text) < 40:
                if text in seen_headings:
                    # 已见过的标题: 若是发明名称且尚未写入内容, 补入封面名称
                    if text == '一、发明名称' and not name_emitted and cover_name:
                        out.append('')
                        out.append(f'# 一、发明名称')
                        out.append('')
                        out.append(cover_name)
                        out.append('')
                        name_emitted = True
                    continue
                seen_headings.add(text)
                out.append('')
                out.append(f'# {text}')
                out.append('')
                continue
            if not keep_hints:
                # 跨段提示区: 【开区(可在段中), 】收区
                if in_hint:
                    if '】' in text:
                        in_hint = False
                        tail = text.split('】', 1)[1].strip()
                        if tail:
                            out.append(tail)
                            out.append('')
                    continue
                # 单段完整提示 / 段中混合
                stripped = re.sub(r'【[^】]*】', '', text).strip()
                if not stripped:
                    continue
                if '【' in stripped and '】' not in stripped:
                    # 提示区从段中开始: 保留【前的前缀, 进入提示区
                    prefix = stripped.split('【', 1)[0].strip()
                    if prefix:
                        out.append(prefix)
                        out.append('')
                    in_hint = True
                    continue
                text = stripped
            out.append(text)
            out.append('')
        else:  # tbl
            tbl_idx += 1
            # 跳过封面表(含 发明名称 行)与注意事项表(含 注意事项)
            first_row = ''.join(t.text or '' for t in el.iter(qn('w:t')))[:30]
            if '发明名称' in first_row and tbl_idx == 0:
                continue
            if '注意事项' in first_row:
                continue
            md_rows = tbl_to_md(el)
            if md_rows:
                out.extend(md_rows)
                out.append('')
    md = '\n'.join(out)
    md = re.sub(r'\n{3,}', '\n\n', md).strip() + '\n'
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write(md)
    return out_md, len(md)

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print('用法: docx2md.py <in.docx> <out.md> [--keep-hints]')
        sys.exit(1)
    keep = '--keep-hints' in args
    src, dst = args[0], args[1]
    out, n = convert(src, dst, keep)
    print(f'OK -> {out} ({n} chars)')

if __name__ == '__main__':
    main()
