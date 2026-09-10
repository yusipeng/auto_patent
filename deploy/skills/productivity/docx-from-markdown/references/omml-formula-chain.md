# pandoc -f latex → OMML 可编辑公式链（实测配方）

参考实现：`D:\auto_patent\tools\md2docx.py`（python-docx 1.2 + pandoc ≥3.x，需在 PATH）。主链路 2026-09 起，位图仅降级。

## 块级公式（```latex）→ oMathPara

```python
# 写临时 md: $$\n <latex> \n$$\n，然后:
subprocess.run(['pandoc', md, '-f', 'latex', '-t', 'docx', '-o', out])
# 从 out 的 word/document.xml 里正则提取 <m:oMathPara>.*?</m:oMathPara>
# (无则回退 <m:oMath>.*?</m:oMath>)
```

## 行内公式（正文 $...$）→ oMath

```python
# 写临时 md: $<latex>$\n，同样 -f latex
# 提取 <m:oMath>.*?</m:oMath>
# 缓存结果; 每次 append 前 copy.deepcopy(el), 否则重复公式丢失(节点被从上一段移走)
```

## 注入 docx 的通用壳（命名空间声明）

OMML 片段无 xmlns 声明，需包根再解析：

```python
wrapped = f'<w:root xmlns:w="{NS_W}" xmlns:m="{NS_M}">{frag}</w:root>'
from docx.oxml import parse_xml
root = parse_xml(wrapped)
# 块公式: 放独立段 p._p.append(root[0]); 行内: 混在普通 run 之间 append
```

命名空间：
- NS_W = `http://schemas.openxmlformats.org/wordprocessingml/2006/main`
- NS_M = `http://schemas.openxmlformats.org/officeDocument/2006/math`

## 必须用 -f latex（不是 markdown+tex_math_dollars）

markdown 层把 `\t` 开头的命令当转义吞掉：`\theta`→`heta`、`\tau` 丢字符、`\alpha`→`alpha`（丢反斜杠）。块级 $$ 同样受害。`-f latex` 直解析：块 `$$`→oMathPara、行内 `$`→oMath，Unicode 数学字符（θ λ Σ）与 `\text{中文}` 都正常。

## 混排解析（** 与 $ 两级）

先按 `(**...**|*...*|`...`|$...$)` 切粗粒度片段；`**`/`*` 片段内容再递归展开 `$...$`。只按 `$` 先切会把粗体闭合符拆散。

## ⚠ 验证陷阱：反斜杠计数别用 grep / Python repr

- **grep 陷阱**：`grep -c '\$\\\\times'` 之类在 bash 里匹配到的是**单反斜杠** `$\times`（grep 把 `\\` 折叠），会误报"双反斜杠残留 5 处"——实际全对。
- **Python repr 陷阱**：`'\\times'` 这类源码字符串打印/取 repr 显示成 `\\`，看着像双反斜杠，其实是**一个**反斜杠的转义表示。
- **正解**：用 Python 逐 `$...$` 片段做字节级检查——对每个 `re.finditer(r'\$[^$]+\$', line)` 的片段查 `'\\\\'`（两个真实反斜杠字节）是否在串内；剥离 `$` 后扫裸数学（`[α-ωΑ-ΩΣ∑·∈≤≥≠×÷−]`）。

```python
# 字节级双反斜杠检查(正确姿势)
dbl = sum(1 for m in re.finditer(r'\$[^$]+\$', md) if '\\\\' in m.group(0))
# 裸数学残留(剥离 $ 后)
stripped = re.sub(r'\$[^$]*\$', '', line)
if re.search(r'[α-ωΑ-ΩΣ∑·∈≤≥≠×÷−]', stripped): ...
```

## 计数口径

- oMath 总数 = 块 oMathPara + 行内 oMath，**含表格内公式**；用元素级遍历（`p._p.findall('.//{...}oMath')`）统计，勿用 XML 子串计数（多算 oMathParaPr 开启标签）。
- 正文行内 $ 片段数 vs docx 行内 oMath 数可能差 N：被剔除区（附录/待补充/封面元信息）里的 $ 不进正文——按剔除后口径核对。
- `\text{中文}` 命令：pandoc latex reader 支持（转 m:r 文本 run）；若渲染失败会整体降级，检查该段 oMath 存在。
