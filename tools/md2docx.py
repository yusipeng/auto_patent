# -*- coding: utf-8 -*-
"""
md2docx.py — 专利交底书 Markdown -> 模板化 docx 转写脚本
用法:
    .venv_patent/Scripts/python.exe tools/md2docx.py <input.md> <output.docx>
输出格式: 按"用户定稿格式"模板(templates/技术交底书模板-发明新型-用户定稿.docx):
    Heading 1~4 黑体 16/15/15/14pt; Body Text 宋体/Times 小四(12pt) 1.25 倍行距 首行缩进 2 字符;
    标题 Word 自动编号(一级 一、~八、自动; 子节 N.M 自动; "零、"为文字); 表格宋体 10pt。
依赖: python-docx, pandoc(LaTeX->OMML 原生可编辑公式, 需在 PATH), node/npx + @mermaid-js/mermaid-cli (复用本机 Edge)
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
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.abspath(__file__))
# 2026-09 起: 以"用户定稿格式"模板为输出基准(黑体标题16/15/15/14pt、宋体正文小四1.25倍行距、
# 首行缩进2字符、Word 自动编号一、~八、与子节 N.M)。
# 旧官方模板 '技术交底书模板-发明新型.docx' 保留留档, 不再用于输出。
DEFAULT_TEMPLATE = os.path.join(BASE, '..', 'templates', '技术交底书模板-发明新型-用户定稿.docx')
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
        # 章节标题 (支持 #~#### : # 文档名 / ## 章节 / ### 小节 / #### 子节)
        m = re.match(r'^(#{1,4})\s+(.*)$', stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            blocks.append(Block(f'h{level}', title, {'level': level}))
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

def _mathtext_preprocess(formula):
    """把 LaTeX 公式转成 matplotlib mathtext 兼容语法:
    - text{X} -> mathrm{X} (mathtext 不支持 text)
    - argmax 运算符处理
    - 保持其余命令, mathtext 支持 frac/sum/cdot/vec 等"""
    import re
    f = formula
    f = re.sub(r'\\text\{([^}]*)\}', r'\\mathrm{\1}', f)
    f = f.replace('\\arg\\max', '\\mathrm{arg\\,max}')
    f = f.replace('\\max', '\\mathrm{max}')
    return f


def render_formula(formula, out_png, fontsize=16):
    """用 matplotlib mathtext 渲染 LaTeX 公式为 PNG (必须包 $ 触发数学模式);
    超宽公式自动在 = 或 + 处断为两行(multline 效果);
    返回 (ok, error_msg)"""
    f = _mathtext_preprocess(formula)
    code = r'''
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
f = r"""%s"""
fs = %d
MAXW_IN = 5.9   # A4 可用行宽(英寸), 200dpi => 1180px

def split_lines(s):
    """超宽时断行: 优先在 ' = ' 之后, 其次在最后的 ' + '/'- '/'+ ' 处"""
    # 先测单行宽度
    fig0 = plt.figure(figsize=(0.01, 0.01))
    t0 = fig0.text(0, 0, "$" + s + "$", fontsize=fs)
    fig0.canvas.draw()
    w0 = t0.get_window_extent().width
    plt.close(fig0)
    if w0 <= MAXW_IN * 100:
        return [s]
    # 找断点: 最后一个 ' + ' 或 ' - ' (优先外层, 不切断 \left[ \right] 配对)
    cands = []
    for sep in (" + ", " - "):
        idx = s.rfind(sep)
        if idx > 0:
            # 断点后的文本必须完整: 不含未配对的 \left 或 \right
            tail = s[idx + len(sep):]
            if tail.count('\\left') == tail.count('\\right') and '\\right]' not in tail:
                cands.append(idx)
    if cands:
        idx = max(cands)
        line1 = s[:idx]
        line2 = s[idx + 3:].lstrip()
        # 校验两行都不超宽
        def w_of(x):
            fig1 = plt.figure(figsize=(0.01, 0.01))
            tt = fig1.text(0, 0, "$" + x + "$", fontsize=fs)
            fig1.canvas.draw()
            ww = tt.get_window_extent().width
            plt.close(fig1)
            return ww
        if w_of(line1) <= MAXW_IN * 100 and w_of(line2) <= MAXW_IN * 100:
            return [line1, line2]
        # 断点不佳, 按字符比例从中间尝试
    half = len(s) // 2
    # 从中间向外找最近的 ' + ' 或 ' = '
    best = None
    for delta in range(0, half, 5):
        for idx in (half - delta, half + delta):
            if 0 < idx < len(s) and (s[idx:idx+3] in (" + ", " - ") or s[idx:idx+2] == "= "):
                best = idx
                break
        if best:
            break
    if best:
        line1 = s[:best].rstrip()
        line2 = s[best:].lstrip(" +-")
        return [line1, line2]
    return [s]

lines = split_lines(f)
fig = plt.figure()
try:
    if len(lines) == 1:
        t = fig.text(0.5, 0.5, "$" + lines[0] + "$", fontsize=fs, ha='center', va='center')
    else:
        t1 = fig.text(0.5, 0.65, "$" + lines[0] + "$", fontsize=fs, ha='center', va='center')
        t2 = fig.text(0.5, 0.35, "$" + lines[1] + "$", fontsize=fs, ha='center', va='center')
        fig.canvas.draw()
        bb1 = t1.get_window_extent(); bb2 = t2.get_window_extent()
        import numpy as np
        w = max(bb1.width, bb2.width); h = bb1.height + bb2.height
        plt.close(fig)
        fig = plt.figure(figsize=(w/100 + 0.2, h/100 + 0.4))
        fig.text(0.5, 0.68, "$" + lines[0] + "$", fontsize=fs, ha='center', va='center')
        fig.text(0.5, 0.32, "$" + lines[1] + "$", fontsize=fs, ha='center', va='center')
    fig.savefig(r"%s", dpi=200, transparent=True, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    print("OK")
except Exception as e:
    print("ERR:", e)
''' % (f.replace('"""', '\\"\\"\\"'), fontsize, out_png)
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


# ---------------- LaTeX -> OMML (Word 原生可编辑公式, pandoc 转换) ----------------

# OMML 与 WordprocessingML 命名空间
NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS_M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'

# 过宽公式按顶层 \quad / 分号断行, 防止溢出页宽(断点后括号/前缀已闭合)
def _split_long_latex(formula, max_len=180):
    if len(formula) <= max_len:
        return [formula]
    # 找顶层断点: \quad(含 \; ) 与逗号/分号, 但排除 \frac{...}{...} / \left...\right 内层
    depth = 0
    in_frac = 0
    breaks = []
    i = 0
    n = len(formula)
    while i < n - 1:
        c2 = formula[i:i + 2]
        if c2 == '\\{':
            depth += 1
            i += 2
            continue
        if c2 == '\\}':
            depth = max(0, depth - 1)
            i += 2
            continue
        if c2 == '\\l':
            depth += 1
            i += 2
            continue
        if c2 == '\\r':
            depth = max(0, depth - 1)
            i += 2
            continue
        if formula[i] == '{':
            depth += 1
            i += 1
            continue
        if formula[i] == '}':
            depth = max(0, depth - 1)
            i += 1
            continue
        if c2 == '\\q' and depth == 0:  # \quad
            breaks.append(i)
            i += 2
            continue
        if formula[i] in ',;' and depth == 0:
            breaks.append(i + 1)
            i += 1
            continue
        i += 1
    if not breaks:
        return [formula]
    # 取最接近中点的若干断点, 保证每段 <= max_len
    parts = []
    prev = 0
    target = max_len
    while prev < n:
        cands = [b for b in breaks if prev < b <= prev + target]
        if not cands:
            # 无合适断点: 硬切中点半
            cut = min(prev + max_len, n)
            parts.append(formula[prev:cut].rstrip())
            prev = cut
            continue
        cut = max(cands)  # 最接近但不超过 prev+target 的断点
        parts.append(formula[prev:cut].rstrip())
        prev = cut
    tail = formula[prev:].strip()
    if tail and tail != parts[-1]:
        parts.append(tail)
    return [p for p in parts if p]


def add_formula_omml(doc, latex_code):
    """把 latex 公式以 Word 原生公式(OMML, 可双击编辑)插入 doc 末尾段落; 成功返回 True.
    内部: pandoc latex reader 渲染 -> 提取 oMathPara -> 注入段落 XML"""
    latex_code = _normalize_latex_escapes(latex_code)
    import zipfile, re as _re, tempfile as _tf, uuid
    wd = os.path.join(_tf.gettempdir(), 'omml_' + uuid.uuid4().hex)
    os.makedirs(wd, exist_ok=True)
    try:
        md_path = os.path.join(wd, 'eq.md')
        dx_path = os.path.join(wd, 'eq.docx')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('$$\n' + latex_code + '\n$$\n')
        r = subprocess.run(['pandoc', md_path, '-f', 'latex', '-t', 'docx', '-o', dx_path],
                           capture_output=True, text=True, timeout=90)
        if r.returncode != 0 or not os.path.exists(dx_path):
            return False
        with zipfile.ZipFile(dx_path) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        m = _re.search(r'<m:oMathPara>.*?</m:oMathPara>', xml, _re.S)
        if not m:
            m = _re.search(r'<m:oMath>.*?</m:oMath>', xml, _re.S)
        if not m:
            return False
        frag = m.group(0)
        # 片段不含命名空间声明, 包一层带声明的根再解析, 取其中的 oMathPara 元素
        wrapped = f'<w:root xmlns:w="{NS_W}" xmlns:m="{NS_M}">{frag}</w:root>'
        from docx.oxml import parse_xml
        root = parse_xml(wrapped)
        omath_el = root[0]  # m:oMathPara 或 m:oMath
        # 独立段落承载公式(套用 Body Text 样式, 与用户定稿一致)
        try:
            p = doc.add_paragraph(style='Body Text')
        except KeyError:
            p = doc.add_paragraph()
        p._p.append(omath_el)
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(wd, ignore_errors=True)





def png_size(png_path):
    """读取 PNG 像素尺寸 (w, h)"""
    import struct
    with open(png_path, 'rb') as fh:
        data = fh.read(33)
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', data[16:24])


# ---------------- docx 构建 ----------------

def set_run_font(run, size=None, bold=None, name=None):
    """设置 run 字体。name=None 时继承段落样式字体(正文=宋体/Times New Roman 12pt,
    标题=黑体), 不写死字体名; 仅显式传 name(表格宋体/代码 Consolas)时覆盖。"""
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if name is not None:
        run.font.name = name
        r = run._element.rPr.rFonts if run._element.rPr is not None else None
        if r is not None:
            r.set(qn('w:eastAsia'), name)


import re as _re
# 行内 latex -> OMML 元素 (带缓存, 避免同一公式重复调 pandoc)
_inline_omml_cache = {}

# 行内 md 转义星号占位: 防 `\*` 被加粗/斜体正则误判为强调标记(案件4 Engine\* 缺陷)
# 所有文本出口(add_run)还原为字面 '*', 代码 span 内还原为原样 '\*'
_ESC_STAR = '\ue000'
# 案件4 V6 修复: 不提供 *斜体* 解析(语料仅用 **粗体** 与裸孤星记号 Engine* / argmax* 等)。
# 旧 italic 分支 `\*[^*\n]+\*` 会把孤星与远端 '*' 配对, 导致 Engine*(t_i)...**粗体** 同段时
# 星号错位/大段误斜体/粗体丢失(净化稿已把 Engine\* 规范化为裸 Engine*)。移除 italic 后,
# 非 **粗体** 的裸星一律按字面 '*' 保留(Engine* 正确显示), 满足交底书无 *斜体* 用语的语料现状。


def _normalize_latex_escapes(latex):
    """历史遗留修复: 连续反斜杠+字母/下划线(如 \\times) 规约为单反斜杠(\times),
    否则 pandoc latex reader 无法解析, 行内公式以字面 $...$ 残留(案件2 67 处缺陷)"""
    return re.sub(r'\\{2,}(?=[A-Za-z_])', lambda m: '\\', latex)



def _inline_latex_to_omml(latex):
    """行内 $...$ LaTeX -> m:oMath XML; 失败返回 None (结果缓存)
    用 pandoc latex reader 直解析, 规避 markdown 层 \\t 等转义吞噬"""
    latex = _normalize_latex_escapes(latex)
    key = latex
    if key in _inline_omml_cache:
        return _inline_omml_cache[key]
    import zipfile, tempfile as _tf, uuid
    wd = os.path.join(_tf.gettempdir(), 'inl_' + uuid.uuid4().hex)
    os.makedirs(wd, exist_ok=True)
    try:
        md_path = os.path.join(wd, 'eq.md')
        dx_path = os.path.join(wd, 'eq.docx')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('$' + latex + '$\n')
        r = subprocess.run(['pandoc', md_path, '-f', 'latex', '-t', 'docx', '-o', dx_path],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or not os.path.exists(dx_path):
            _inline_omml_cache[key] = None
            return None
        with zipfile.ZipFile(dx_path) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        m = _re.search(r'<m:oMath>.*?</m:oMath>', xml, _re.S)
        if not m:
            _inline_omml_cache[key] = None
            return None
        frag = m.group(0)
        wrapped = f'<w:root xmlns:w="{NS_W}" xmlns:m="{NS_M}">{frag}</w:root>'
        from docx.oxml import parse_xml
        root = parse_xml(wrapped)
        el = root[0]
        _inline_omml_cache[key] = el
        return el
    except Exception:
        _inline_omml_cache[key] = None
        return None
    finally:
        shutil.rmtree(wd, ignore_errors=True)


def _emit_runs(p, text, size=None, bold=False, italic=False, font_name=None):
    """把纯文本片段(可含 $...$ 行内公式)按公式/普通文本拆成 run; 返回是否插入了公式
    入口统一还原 _ESC_STAR 占位(由 _add_inline_runs 对 \\* 转义保护产生)为字面 '*'"""
    text = text.replace(_ESC_STAR, '*')
    parts = re.split(r'(\$[^\$\n]+\$)', text)
    for part in parts:
        if not part:
            continue
        if part.startswith('$') and part.endswith('$') and len(part) > 2:
            el = _inline_latex_to_omml(part[1:-1])
            if el is not None:
                # 缓存复用同一元素, 重复公式必须深拷贝, 否则 lxml append 会把
                # 该节点从上一段落移走(重复公式丢失, 只留最后一次)
                import copy
                p._p.append(copy.deepcopy(el))
            else:
                run = p.add_run(part)
                set_run_font(run, size=size, bold=bold, name=font_name)
                run.italic = True
        else:
            run = p.add_run(part)
            set_run_font(run, size=size, bold=bold, name=font_name)
            if italic:
                run.italic = True


def _add_inline_runs(p, text, size=None, bold=False, font_name=None):
    """解析行内 md 标记: **粗体** *斜体* `代码` $行内公式$, 生成多个 run / 行内公式。
    两级解析: 先识别 **/*/`/`$ 粗粒度片段, 粗体等片段内容再递归展开 $...$,
    从而支持 '**中文 $公式$ 中文**' 混排
    入口先做转义星号保护: \\* -> _ESC_STAR, 防止转义星号被误判为强调边界(如 Engine\\* 缺陷);
    普通文本/公式出口由 _emit_runs 还原为 '*', 代码 span 出口还原为字面 '\\*'
    size=None 时继承段落样式字号; font_name 仅表格等需固定字体时传入。"""
    text = text.replace('\\*', _ESC_STAR)
    # 仅解析 **粗体**、`代码`、$行内公式$; 无 *斜体* 分支(见 _ESC_STAR 注释, 案件4 V6 孤星缺陷修复)
    pattern = re.compile(r'(\*\*[^*]+\*\*|`[^`\n]+`|\$[^\$\n]+\$)')
    for seg in pattern.split(text):
        if not seg:
            continue
        if seg.startswith('**') and seg.endswith('**') and len(seg) > 4:
            _emit_runs(p, seg[2:-2], size=size, bold=True, font_name=font_name)
        elif seg.startswith('`') and seg.endswith('`') and len(seg) > 2:
            run = p.add_run(seg[1:-1].replace(_ESC_STAR, '\\*'))
            set_run_font(run, size=(size - 1 if size else None), bold=bold, name='Consolas')
        elif seg.startswith('$') and seg.endswith('$') and len(seg) > 2:
            _emit_runs(p, seg, size=size, bold=bold, font_name=font_name)
        else:
            _emit_runs(p, seg, size=size, bold=bold, font_name=font_name)


def add_picture_fit(doc, img_path, max_w_in=5.9, max_h_in=8.0, max_scale=1.0):
    """插入图片并自适应: 宽高都不超限, 整体缩放下限 max_scale(相对原始渲染尺寸), 保持比例"""
    from docx.shared import Inches as _In
    size = png_size(img_path)
    if not size:
        doc.add_picture(img_path, width=_In(min(max_w_in, 5.0)))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        return True
    wpx, hpx = size
    w_in = wpx / 200.0   # 渲染 dpi 200
    h_in = hpx / 200.0
    # 宽高双重缩放 + 整体缩放下限, 取小者
    scale = min(max_w_in / w_in, max_h_in / h_in, max_scale, 1.0)
    disp_w = w_in * scale
    if disp_w < 0.3:   # 极小图也放大到可读下限
        disp_w = 0.3
    doc.add_picture(img_path, width=_In(disp_w))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    return True


# ---------------- Word 自动编号 (标题编号, 复刻用户定稿格式) ----------------
# 一级标题: chineseCounting "一、二、…" 自动生成 ("零、"保留文字不编号);
# 子节标题: "N.M" 单层编号(lvlText "N.%1"), 优先复用模板内已有定义, 缺失时动态创建。

class _NumState:
    """一次生成过程内的 Word 编号状态(一级中文编号 + 各节 "N.%1" 子编号)"""

    def __init__(self, doc):
        self.doc = doc
        self.h1_numid = None       # 一级标题中文编号 numId
        self._sub = {}             # 数字前缀 -> numId (如 '3' -> 复用模板 "3.%1")
        self._lvl_index = {}       # lvlText -> numId
        self._abs_seq = 0
        self._num_seq = 0
        self._scan()

    def _numbering(self):
        return self.doc.part.numbering_part.element

    def _scan(self):
        el = self._numbering()
        abs_map = {}
        for a in el.findall(qn('w:abstractNum')):
            aid = int(a.get(qn('w:abstractNumId')))
            self._abs_seq = max(self._abs_seq, aid + 1)
            lvl = a.find(qn('w:lvl'))
            if lvl is None:
                continue
            lt = lvl.find(qn('w:lvlText'))
            nf = lvl.find(qn('w:numFmt'))
            abs_map[aid] = (lt.get(qn('w:val')) if lt is not None else '',
                            nf.get(qn('w:val')) if nf is not None else '')
        for n in el.findall(qn('w:num')):
            nid = int(n.get(qn('w:numId')))
            self._num_seq = max(self._num_seq, nid + 1)
            ref = n.find(qn('w:abstractNumId'))
            if ref is None:
                continue
            lvl_text, num_fmt = abs_map.get(int(ref.get(qn('w:val'))), ('', ''))
            if lvl_text:
                self._lvl_index.setdefault(lvl_text, nid)
            if num_fmt == 'chineseCounting' and self.h1_numid is None:
                self.h1_numid = nid

    def section_numid(self, parent):
        """取得(或创建) "parent.%1" 编号定义的 numId, 例: parent='5' -> 复用模板 "5.%1" """
        if parent in self._sub:
            return self._sub[parent]
        want = parent + '.%1'
        if want in self._lvl_index:
            self._sub[parent] = self._lvl_index[want]
            return self._sub[parent]
        aid = self._abs_seq
        self._abs_seq += 1
        nid = self._num_seq
        self._num_seq += 1
        abs_xml = (
            '<w:abstractNum xmlns:w="%s" w:abstractNumId="%d">'
            '<w:multiLevelType w:val="singleLevel"/>'
            '<w:lvl w:ilvl="0" w:tentative="0">'
            '<w:start w:val="1"/>'
            '<w:numFmt w:val="decimal"/>'
            '<w:suff w:val="space"/>'
            '<w:lvlText w:val="%s.%%1"/>'
            '<w:lvlJc w:val="left"/>'
            '<w:pPr><w:ind w:left="0" w:firstLine="0"/></w:pPr>'
            '</w:lvl></w:abstractNum>' % (NS_W, aid, parent)
        )
        el = self._numbering()
        new_abs = parse_xml(abs_xml)
        abs_list = el.findall(qn('w:abstractNum'))
        if abs_list:
            abs_list[-1].addnext(new_abs)
        else:
            el.insert(0, new_abs)
        num_xml = ('<w:num xmlns:w="%s" w:numId="%d"><w:abstractNumId w:val="%d"/></w:num>'
                   % (NS_W, nid, aid))
        new_num = parse_xml(num_xml)
        cleanup = el.find(qn('w:numIdMacAtCleanup'))
        if cleanup is not None:
            cleanup.addprevious(new_num)
        else:
            el.append(new_num)
        self._sub[parent] = nid
        return nid

    @staticmethod
    def attach(p, numid, ilvl=0):
        """给段落挂 numPr(Word 自动编号); numPr 须插在 pPr 内 pStyle 之后(OOXML 顺序)"""
        pPr = p._p.get_or_add_pPr()
        numPr = pPr.find(qn('w:numPr'))
        if numPr is None:
            numPr = OxmlElement('w:numPr')
            pStyle = pPr.find(qn('w:pStyle'))
            if pStyle is not None:
                pStyle.addnext(numPr)
            else:
                pPr.insert(0, numPr)
        for tag, val in (('w:ilvl', ilvl), ('w:numId', numid)):
            cell = numPr.find(qn(tag))
            if cell is None:
                cell = OxmlElement(tag)
                numPr.append(cell)
            cell.set(qn('w:val'), str(val))


def add_para(doc, text, size=None, bold=False, indent=None, style='Body Text'):
    """正文段落: 默认套用模板 "Body Text" 样式(宋体/Times New Roman 12pt=小四,
    行距 1.25, 段前后各 5 磅, 首行缩进 2 字符, 两端对齐) —— 与用户定稿格式一致。
    size 仅在需显式字号(诊断标注等)时传入; indent 为显式首行缩进(pt)。"""
    try:
        p = doc.add_paragraph(style=style)
    except KeyError:
        p = doc.add_paragraph()
    _add_inline_runs(p, text, size=size, bold=bold)
    if indent is not None:
        p.paragraph_format.first_line_indent = Pt(indent)
    return p


def add_heading_para(doc, text, level=1, numstate=None):
    """标题: 套用模板 Heading 1~4 样式(黑体 16/15/15/14pt, 段前 16/14/12/10 磅),
    自动带 Word 大纲级别(样式含 outlineLvl, 导航窗格可见)。
    Word 自动编号(复刻用户定稿): 一级 "一、~八、" 自动生成("零、"保留文字);
    子节 "3.1/5.1/6.1" 自动生成 —— 编号前缀自标题文字剥离, 由 Word 域生成,
    增删章节时编号自动重排。"""
    style_map = {1: 'Heading 1', 2: 'Heading 2', 3: 'Heading 3', 4: 'Heading 4'}
    try:
        p = doc.add_paragraph(style=style_map.get(level, 'Heading 4'))
    except KeyError:
        p = doc.add_paragraph()
    txt = text.replace(_ESC_STAR, '*').replace('\\*', '*').strip()
    numid = None
    if numstate is not None:
        if level == 1:
            m = re.match(r'^[一二三四五六七八九十]+、\s*(.+)$', txt)
            if m and numstate.h1_numid is not None and m.group(1).strip():
                numid = numstate.h1_numid
                txt = m.group(1).strip()
        if numid is None and level >= 2:
            m = re.match(r'^(\d{1,2}(?:\.\d{1,2})+)\s+(.+)$', txt)
            if m and m.group(2).strip():
                parent = '.'.join(m.group(1).split('.')[:-1])
                numid = numstate.section_numid(parent)
                txt = m.group(2).strip()
    p.add_run(txt)
    if numid is not None:
        _NumState.attach(p, numid)
    return p


def add_table(doc, header, rows):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
    tblPr = tbl._tbl.tblPr
    try:
        tbl.style = 'Table Grid'
    except KeyError:
        # 模板无 Table Grid 样式: 手动加六边单线边框(与用户定稿一致: single sz=4 黑色)
        borders = OxmlElement('w:tblBorders')
        for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement(f'w:{edge}')
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), '4')
            el.set(qn('w:color'), '000000')
            borders.append(el)
        tblPr.append(borders)
    # 表格宽度 ~100% 居中 (参考格式: tblW=4998 pct + jc=center)
    tblW = tblPr.find(qn('w:tblW'))
    if tblW is None:
        tblW = OxmlElement('w:tblW')
        tblPr.insert(0, tblW)
    tblW.set(qn('w:w'), '4998')
    tblW.set(qn('w:type'), 'pct')
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(header):
        cell = tbl.rows[0].cells[j]
        cell.text = ''
        _add_inline_runs(cell.paragraphs[0], h, size=10, bold=True, font_name='宋体')
    for ri, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = tbl.rows[ri].cells[j]
            cell.text = ''
            _add_inline_runs(cell.paragraphs[0], val, size=10, font_name='宋体')
    return tbl


def build_docx(md_text, out_path, template_path=DEFAULT_TEMPLATE, workdir=None, md_dir=None):
    doc = Document(template_path)
    try:
        numstate = _NumState(doc)   # Word 自动编号状态(标题编号)
    except Exception:
        numstate = None
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
    idx = next((i for i, b in enumerate(blocks) if b.kind.startswith('h') and b.content.startswith('一、')), None)
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
        if b.kind.startswith('h'):
            add_heading_para(doc, b.content, int(b.kind[1]), numstate)
        elif b.kind == 'p':
            add_para(doc, b.content)
        elif b.kind == 'ul':
            # 与用户定稿一致: 列表项为无符号缩进段(同正文 2 字符首行缩进)
            for item in b.content:
                add_para(doc, item)
        elif b.kind == 'ol':
            for j, item in enumerate(b.content, 1):
                add_para(doc, f'{j}. {item}')
        elif b.kind == 'table':
            add_table(doc, b.meta['header'], b.content)
        elif b.kind == 'mermaid':
            wd = workdir or tempfile.mkdtemp(prefix='mermaid_')
            png = os.path.join(wd, f'fig_{len(doc.inline_shapes) + 1}.png')
            ok, err = render_mermaid(b.content, png, wd)
            if ok:
                try:
                    add_picture_fit(doc, png, max_w_in=5.76, max_h_in=7.5)
                except Exception as e:
                    add_para(doc, f'[图渲染失败: {e}]', size=9)
                    add_para(doc, b.content, size=9)
            else:
                add_para(doc, f'[Mermaid 渲染失败, 原图代码: {err[:100]}]', size=9)
                add_para(doc, b.content, size=9)
        elif b.kind == 'formula':
            ok = add_formula_omml(doc, b.content)
            if not ok:
                # pandoc/OMML 失败时降级 matplotlib 位图 (旧链路保留)
                wd = workdir or tempfile.mkdtemp(prefix='latex_')
                png = os.path.join(wd, f'eq_{len(doc.inline_shapes) + 1}.png')
                ok2, err2 = render_formula(b.content, png)
                if ok2:
                    try:
                        add_picture_fit(doc, png, max_w_in=5.76, max_h_in=2.0, max_scale=0.69)
                    except Exception as e:
                        add_para(doc, f'[公式渲染失败: {e}]', size=9)
                        add_para(doc, b.content, size=9)
                else:
                    add_para(doc, f'[公式渲染失败, 原公式: {err2[:100]}]', size=9)
                    add_para(doc, b.content, size=9)
        elif b.kind == 'code':
            add_para(doc, b.content)
        elif b.kind == 'image':
            src = resolve_img(b.content)
            if os.path.exists(src):
                try:
                    add_picture_fit(doc, src, max_w_in=5.76, max_h_in=7.5)
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
    # md_dir: md 文件所在目录(解析图片相对路径); md 文本首行保密标注自动补
    build_docx(md_text, out_path, md_dir=os.path.dirname(os.path.abspath(md_path)))
    print(f'OK -> {out_path}')


if __name__ == '__main__':
    main()
