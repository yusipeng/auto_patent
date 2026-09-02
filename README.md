# 专利交底书自动化流水线 (D:\auto_patent)

把论文预印本 → 公司专利交底书 docx + 检索报告 docx，全程 7 个 Hermes Bot 专人专项协作。

## 快速开始

1. 在 Hermes 桌面 **Bots** 标签页确认 7 个 Bot 在线：patent_searcher / patent_writer / patent_reviewer / patent_auditor / patent_docx / patent_report / patent_reviser
2. 主会话发：`@patent_searcher 检索关键词：<关键词>`（默认近 6 个月）
3. 按 4 个里程碑人工把关推进（选论文 → 确认方案 → 评审意见 → 定稿）
4. 修改评审，主会话发：`@patent_reviser 修订 cases/<发明名称>/：批注在 03_review/xxx.docx，对比专利在 01_source/xxx.pdf`

## 目录

```
D:\auto_patent\
  templates\          模板基准（只读）：-交底书V1.docx、-检索报告V1.docx
  cases\<发明名称>\   每个案件：01_source/ 02_draft/ 03_review/ 04_docx/
  tools\              工具脚本（见下）
  .venv_patent\       Python venv：python-docx 1.2.0 / pymupdf / matplotlib 3.11
```

## 工具脚本（tools/）

| 脚本                | 用途                                                     | 状态                |
| ------------------- | -------------------------------------------------------- | ------------------- |
| md2docx.py          | 交底书 md → 模板 docx（Mermaid/LaTeX 转图、表格、页眉） | ✅ 实测通过         |
| patent_search.py    | Google Patents 检索（走 Clash 127.0.0.1:7897）           | ✅ 实测返回真实专利 |
| extract_pdf.py      | PDF → 纯文本（pymupdf）                                 | ✅                  |
| extract_comments.py | 提取 docx 内 Word 批注                                   | ✅                  |
| new_case.py         | 创建案件目录结构                                         | ✅                  |
| puppeteer-edge.json | mermaid-cli 复用本机 Edge 的配置                         | ✅                  |

## 流水线（7 Bot + 4 人工确认点）

```
关键词 → searcher(检索+筛选) → [用户选1~3篇] → searcher(Grill-Me方向细化)
      → [用户确认清单] → writer(撰写) → reviewer(内容评审)
      → 不过则打回 writer(≤2轮) → auditor(格式审计) → 不过则打回(≤2轮)
      → docx(转写docx) → [用户评审意见] → report(检索报告，对比文件回流writer更新三)
      → reviser(批注+对比专利修订) → [定稿]
```

## 关键事实

- 模板章节实际为 **零~六**（「其他技术资料」并入六），非零~七
- 封面固定：申报单位=〔申报单位〕 / 申报类型=发明 / 发明人·技术联系人=〔联系人〕
- 成品命名：`发明名称-交底书vN.docx` / `发明名称-检索报告v1.docx`
- 所有命令需 `PYTHONPATH=""` 前缀（避免 Hermes venv 污染）
- 详细调度手册：`patent-workflow` skill（主会话加载即得）
