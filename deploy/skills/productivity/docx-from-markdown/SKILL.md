---
name: docx-from-markdown
description: Use when markdown 含公式/图转 Word。pandoc-OMML 可编辑公式为主，mathtext 位图仅兜底。
---

# Markdown → Word (docx) 渲染（LaTeX 公式 / Mermaid 图 / 标题层级）

把 md 源（专利交底书、报告、论文笔记等）转成排版正确的 .docx。参考实现：`D:\auto_patent\tools\md2docx.py`（python-docx 1.2 + pandoc ≥3.x，需在 PATH）。

## 主链路：LaTeX → Word 原生 OMML 可编辑公式（2026-09 起）

**用户验收标准：公式必须可双击编辑（原生 Word 公式），位图公式被明确拒绝（"图片无法修改"）。** 块级 ```latex 与正文行内 `$...$` 全部走 pandoc → OMML，matplotlib mathtext 位图仅作 OMML 失败时的降级路径。

### 关键坑位（按杀伤力排序）

1. **pandoc 必须用 `-f latex`（latex reader），不可用 `markdown+tex_math_dollars`**
   markdown 层会把 `\t` 开头的 LaTeX 命令当转义吞掉：`\theta` → `heta`（`v_\theta` 渲染成 `vheta`），块级 `$$...$$` 同样受害。用 `-f latex` 直解析：块级 `$$..$$` → `oMathPara`，行内 `$..$` → `oMath`，且 Unicode 数学字符（θ λ Σ）与 `\text{中文}`（中文词入公式）均可直接解析。
2. **重复行内公式必须 `copy.deepcopy(el)` 后再 `p._p.append`**
   若把 pandoc 结果缓存复用同一 lxml 元素，第二次 append 会把节点从上一段落移走 → 重复公式丢失（实测 196 处只渲染出 85 处）。缓存 + 深拷贝是标配。
3. **`**粗体 $公式$ 混排** 需要两级解析**
   先按 `**`/`*`/`` ` ``/`$` 切粗粒度片段，粗体/斜体片段内容再递归展开 `$...$`。只按 `$` 先切会把粗体闭合符拆散 → 字面 `**` 残留。
4. **OMML 片段无命名空间声明，需包一层带 xmlns 的根再 parse_xml**
   从 pandoc 产出的 document.xml 里正则提取 `<m:oMathPara>..</m:oMathPara>` 后，包 `<w:root xmlns:w=... xmlns:m=...>` 再 `docx.oxml.parse_xml`，取 `root[0]` append。

### md 源编写规范（上游必须遵守，否则白转）

- **正文每个数学变量/式子都必须包 `$...$` LaTeX**：`λ_j`→`$\lambda_j$`、`Σλ_j·p_ij·C_j`→`$\sum_j \lambda_j p_{ij} C_j$`、`0≤γ<1`→`$0\le\gamma<1$`。裸文本数学（希腊字母/下划线/Σ·≤∈）不会自动识别，纯文本直出 → 用户投诉"变量没渲染"。
- 英文缩写（CPA/KPI/RTB 等业务词）**不是数学，勿包**；公式块代码 ```latex、Mermaid、图片引用、标题行不动。
- 单独变量做粗体（`**v_θ**`）且内容是纯数学时，直接改 `$v_\theta$`（公式自带样式）；中文强调词保留 `**`。
- 表格单元格（如术语表第三列）里的变量同样包 `$...$`，单元格渲染与正文一致。

## 标题层级（# → Word 大纲）

- md `#`~`####` → `w:outlineLvl` 0~3（`add_heading_para` 里 pPr 加 OxmlElement('w:outlineLvl')），导航窗格可见层级；只设字体/加粗不设 outline 会被用户判定"没转成文档层级"。
- 解析器必须支持 1~4 个 `#`：曾因正则 `#{1,3}` 把 `#### 5.3.1` 漏成正文段落。
- 字号随层级（16/14/12/11pt 对应 h1~h4）。

## Mermaid / 位图 / 表格（unchanged basics）

- Mermaid：npx @mermaid-js/mermaid-cli + 本机 Edge（puppeteer-edge.json），PNG 与源文件一一对应，正文 `![..](../media/..)` 引用路径以 md 所在目录为基准。
- 行内 md 标记：`**粗体**`/`*斜体*`/`` `代码` `` 必须解析成多个 run，否则字面星号。
- 模板无 `Table Grid` 样式时手动 append `w:tblBorders` 六边（`tbl.style` 抛 KeyError）。
- docx 被 Word/WPS 占用时保存抛 PermissionError → 版本化工具先复制 V+1 再写 / 请用户关闭。
- 纵向图固定宽度会高度爆炸：宽高双约束 `scale = min(max_w/w, max_h/h, max_scale, 1.0)`。

## 产出自检清单

- 章节齐全、顺序正确；标题有 outlineLvl（一~八=lvl0，5.x=lvl1，5.3.x=lvl2）——**校验要走双通道**：标题挂命名样式时段落上无直接 outlineLvl，须 样式名（`Heading N`）∨ 直接 outlineLvl 双路识别，只查直接属性会误报 0 个标题
- **自动编号不在段落文本里**：章节/编号逐字比对前先剥离编号前缀（文本 `发明名称` ↔ 模板 `一、发明名称` 归一化后相等；写成文字的 `零、` 前缀除外）
- 现成校验脚本：`D:\auto_patent\tools\verify_docx.py`（章节模板比对/公式计数/`$`残留扫描）、`verify_cover_and_media.py`（封面/媒体内嵌/页数）
- oMath 元素计数 = 期望值（块 oMathPara N + 行内 M），含表格内公式；用元素级遍历统计，勿用 XML 子串计数（会多算 oMathParaPr 等开启标签）
- 无字面 `**`、`$`、LaTeX 源码（`\lambda`）外泄；无「渲染失败/图片缺失」标记
- 公式图片位图数量 = 0（降级未触发时）

## 模板样式套用与 Word 自动编号（2026-09 实践）

- **排版走命名样式**：以用户定稿 docx 派生"空白格式模板"（保留 styles.xml/numbering.xml/封面/页脚，清空正文；参考实现 `D:\auto_patent\tools\make_template.py`），生成时标题/正文分别套 `Heading 1~4`/`Body Text` 样式；**run 上不要写死字体名**（否则西文被中文字体接管、失去 Times New Roman/宋体分流），仅保留加粗/斜体标志位。
- **标题自动编号**：编号前缀从标题文字剥离，改挂 `numPr`；优先复用模板既有编号定义（如 chineseCounting `%1、`、`3.%1`），缺失时动态新增——新 `abstractNum` 须插在所有 `abstractNum` 之后、所有 `num` 之前；`numPr` 必须插在段落 pPr 的 `pStyle` 之后（OOXML 顺序）。
- **反向导入**（docx→md，参考实现 `D:\auto_patent\tools\docx2md.py`）：自动编号按文档顺序用计数器合成回文字（即使不用返回值也须逐段推进计数）；OMML 公式可用"单段迷你 docx + `pandoc -t markdown`"逐段还原为 `$...$`；pandoc markdown 输出会转义 `" ' [ ] >`（数学段外需反向去转义，`$...$` 内原样保留）。

## 支持文件

- `references/omml-formula-chain.md` — **主链路**：pandoc `-f latex`→OMML 块级/行内公式注入配方、`**与$` 两级混排解析、`copy.deepcopy` 缓存、命名空间包根、字节级反斜杠验证陷阱（grep/Python-repr 都会误报双反斜杠）。
- `references/mathtext-image-rendering.md` — **降级路径**（OMML 失败才用）：matplotlib mathtext 渲染代码：render_formula（$ 强制数学模式/自动断行）、add_picture_fit、字号匹配。注意其中的坑位描述是旧主链路的教训，现仅适用降级场景。
