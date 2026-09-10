# 可用代码片段：mathtext 公式渲染 + docx 图片适配

**⚠ 降级路径专用（2026-09 起主链路为 pandoc -f latex → OMML 可编辑公式，见 SKILL.md）**：仅当 OMML 转换失败时回退 matplotlib mathtext 位图。以下代码摘自 `D:\auto_patent\tools\md2docx.py`（实测可用，python-docx 1.2.0 + matplotlib 3.11）。

## render_formula（mathtext，含自动断行）

要点：
- `fig.text` 的字符串拼 `"$" + f + "$"` 强制数学模式（不加 $ 就静默渲染字面代码）。
- 公式转义：`\text{X}` → `\mathrm{X}`；`\arg\max` → `\mathrm{arg\,max}`；`\max` → `\mathrm{max}`。
- 嵌入 python -c 子进程代码串时**不要** replace 反斜杠翻倍（r-string 已保留单反斜杠；翻倍变 `\\frac`=换行+frac → ParseException）。
- 超宽（>5.9in≈1180px@200dpi）自动断两行：优先在 ` + `/` - ` 处断，断点后片段必须 `\left` 与 `\right` 数量相等且不含残缺 `\right]`。

```python
def _mathtext_preprocess(formula):
    import re
    f = formula
    f = re.sub(r'\\text\{([^}]*)\}', r'\\mathrm{\1}', f)
    f = f.replace('\\arg\\max', '\\mathrm{arg\\,max}')
    f = f.replace('\\max', '\\mathrm{max}')
    return f
```

核心渲染骨架（子进程内执行，避免污染主进程 matplotlib）：

```python
# 在子进程 code 里:
# fig.text(0, 0, "$" + f + "$", fontsize=fs)   # 测宽(先 draw)
# 超宽则 split_lines() 拆两行后:
#   t1 = fig.text(0.5, 0.65, "$" + lines[0] + "$", fontsize=fs, ha='center')
#   t2 = fig.text(0.5, 0.35, "$" + lines[1] + "$", fontsize=fs, ha='center')
# fig.savefig(png, dpi=200, transparent=True, bbox_inches='tight', pad_inches=0.05)
```

## add_picture_fit（宽高双约束，防纵向图超高 / 长公式过窄）

```python
def png_size(png_path):
    import struct
    with open(png_path, 'rb') as fh:
        data = fh.read(33)
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', data[16:24])  # (w, h) px

def add_picture_fit(doc, img_path, max_w_in=5.9, max_h_in=8.0, max_scale=1.0):
    from docx.shared import Inches
    size = png_size(img_path)
    if not size:
        doc.add_picture(img_path, width=Inches(min(max_w_in, 5.0)))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        return True
    wpx, hpx = size
    w_in, h_in = wpx / 200.0, hpx / 200.0   # 渲染 dpi=200
    scale = min(max_w_in / w_in, max_h_in / h_in, max_scale, 1.0)
    disp_w = max(w_in * scale, 0.3)
    doc.add_picture(img_path, width=Inches(disp_w))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    return True
```

调用参数经验值：
- 架构/流程图：`max_w_in=5.9, max_h_in=7.5`（竖版图不会被压超高）
- 公式：`max_w_in=5.9, max_h_in=2.0, max_scale=0.69`（渲染 16pt → 视觉 ~11pt 与正文匹配；长公式已在渲染端断行）

## 行内 md 标记 → 多 run

```python
import re
INLINE_RE = re.compile(r'(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)')
# split 后: **x** -> run(bold=True); *x* -> run(italic=True); `x` -> run(name='Consolas', size-1)
```

## 模板表格无 Table Grid 样式

`tbl.style = 'Table Grid'` 抛 KeyError 时手动加边框：

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
borders = OxmlElement('w:tblBorders')
for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
    el = OxmlElement(f'w:{edge}')
    el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), '4'); el.set(qn('w:color'), '000000')
    borders.append(el)
tblPr.append(borders)
```

## 验收清单

- 段落无字面 `**` / 反引号残留（说明行内解析生效）
- 图片嵌入数 = 预期（架构图 + 公式数），media 文件存在
- 每张图宽 ≤5.9in、高 ≤7.5in（纵向图未被压超高）
- 公式 PNG 宽度随内容长度变化（固定宽度 = 未适配）
- 被 Word 占用时保存 PermissionError → 版本化工具先复制 V+1 再写
