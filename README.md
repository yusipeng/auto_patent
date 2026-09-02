# 专利交底书自动化流水线 (D:\auto_patent)

把论文预印本 → 公司专利交底书 docx + 检索报告 docx，全程 7 个 Hermes Bot 专人专项协作。

## 快速开始

1. 在 Hermes 桌面 **Bots** 标签页确认 7 个 Bot 在线：patent_searcher / patent_writer / patent_reviewer / patent_auditor / patent_docx / patent_report / patent_reviser
2. 主会话发：`@patent_searcher 检索关键词：<关键词>`（默认近 6 个月）
3. 按 4 个里程碑人工把关推进（选论文 → 确认方案 → 评审意见 → 定稿）

## 目录

```
D:\auto_patent\
  templates\          模板基准（只读）
    技术交底书模板-发明新型.docx        # 2026-09 新版：零~八 + 3 无编号节
    检索报告模板 （修订版）.docx  # 二→四跳号原样保留
  cases\<发明名称>\   每个案件：01_source/ 02_draft/ 03_review/ 04_docx/
  tools\              工具脚本（见下）
  .venv_patent\       Python venv：python-docx 1.2.0 / pymupdf / matplotlib 3.11
```

## 版本管理规范

- 产出文件名：`<发明名称>-交底书VN.docx` / `<发明名称>-检索报告VN.docx`，**初始 V1**
- **每次修改**：先由 `tools/versioned_output.py` 把最新旧版复制为 V+1 副本（留档），新内容写入 V+1 文件，**旧版本永不覆盖**
- md 中间源同步 `交底书-vN.md` 递增

```bash
# 查当前最新版本
PYTHONPATH="" .venv_patent/Scripts/python.exe tools/versioned_output.py cases/<案>/04_docx "<发明名称>" 交底书 --peek
# 修改前创建 V+1 副本（输出 TARGET= 应写入的路径）
PYTHONPATH="" .venv_patent/Scripts/python.exe tools/versioned_output.py cases/<案>/04_docx "<发明名称>" 交底书
```

## 工具脚本（tools/）

| 脚本 | 用途 | 状态 |
|------|------|------|
| md2docx.py | 交底书 md → 模板 docx（Mermaid/LaTeX 转图、表格） | ✅ 已适配新模板实测 |
| docx2md.py | 已有交底书 docx → md 源（导入） | ✅ 往返实测通过 |
| versioned_output.py | 产物版本管理（V1 起步，修改即副本+1） | ✅ 实测通过 |
| patent_search.py | Google Patents 检索（走 Clash 127.0.0.1:7897） | ✅ 实测返回真实专利 |
| extract_pdf.py | PDF → 纯文本（pymupdf） | ✅ |
| extract_comments.py | 提取 docx 内 Word 批注 | ✅ |
| new_case.py | 创建案件目录结构 | ✅ |
| puppeteer-edge.json | mermaid-cli 复用本机 Edge 的配置 | ✅ |

## 模板结构速查（2026-09 新版交底书）

零 术语定义和解释（三列表格）→ 一 发明名称 → 二 技术领域（14 选）→ 三 现有技术的技术方案 → 四 现有技术的缺点及本申请提案要解决的技术问题 → 五 技术方案详细阐述（≥50% 篇幅）→ 六 关键点和欲保护点 → 七 技术优点 → 八 发散思维以及规避方案思考 → 商业价值 → 侵权证据可获得性/标准进展情况 → 其他技术资料

## 流水线（7 Bot + 4 人工确认点）

```
关键词 → searcher(检索+筛选) → [用户选1~3篇] → searcher(Grill-Me方向细化)
      → [用户确认清单] → writer(撰写) → reviewer(内容评审)
      → 不过则打回 writer(≤2轮) → auditor(格式审计) → 不过则打回(≤2轮)
      → docx(转写docx, V1) → [用户评审意见] → report(检索报告, 对比文件回流writer更新三)
      → reviser(批注+对比专利修订, V+1) → [定稿]
```

## 关键事实

- 模板章节以 `templates/` 最新文件为准（当前 2026-09 新版：零~八 + 3 无编号节）
- 封面固定：申报单位=〔申报单位〕 / 申报类型=发明 / 发明人·技术联系人=〔联系人〕
- 检索报告模板「二」之后直接「四」（无三），保持跳号原样
- 新交底书模板无保密页眉（检索报告模板有），各随其模板
- 所有命令需 `PYTHONPATH=""` 前缀（避免 Hermes venv 污染）
- 详细调度手册：`patent-workflow` skill（主会话加载即得）
