# AGENTS.md — auto_patent 专利交底书流水线（Agent 项目指南）

把论文预印本 → 专利交底书 docx + 检索报告 docx 的自动化流水线（8 个 Hermes Bot 专人专项协作）。

> **公开仓库**：请勿提交公司名称、项目名称、姓名、联系方式、内部代号等个人信息；提交前运行 `python deploy/privacy_check.py`。

- **工作流总纲 skill**：`deploy/skills/patent/patent-workflow/SKILL.md`（已装 skill 的 Agent 会自动加载；未装先读它）
- **部署/迁移**：`deploy/README.md`（Hermes 全量）与 `deploy/AGENT-INSTALL.md`（Claude Code / Codex / WorkBuddy 等安装本仓库技能）

## 环境与命令约定

- 所有命令在**仓库根目录**执行。
- Python 工具统一用仓库 venv：`PYTHONPATH="" .venv_patent/Scripts/python.exe tools/<x>.py`（Windows；POSIX 用 `.venv_patent/bin/python`）。
  首次使用先建 venv：`python deploy/install.py --venv`（或 `python -m venv .venv_patent && .venv_patent/Scripts/pip install -r deploy/requirements-venv.txt`）。
- 外部依赖：**pandoc**（LaTeX→OMML 公式）、**Node/npx + 本机 Edge**（Mermaid 出图）、**Word**（可选：docx→PDF 排版核对、页数统计）。
- **模板自备**：`templates/*.docx` 不入库（含公司信息），按 `templates/README.md` 放入；md2docx 默认读取 `templates/技术交底书模板-发明新型-用户定稿.docx`。

## 仓库结构

- `templates/` — 模板目录（自备；`README.md` 有生成「格式基准」的方法）
- `tools/` — 工具链（转换 / 校验 / 检索 / 版本管理；清单见 `README.md`）
- `cases/<发明名称>/` — `01_source/`（论文与对比文件）→ `02_draft/`（交底书 md）→ `03_review/`（评审/审计报告）→ `04_docx/`（成品 docx）
- `deploy/` — 迁移包（skills / bot 骨架 / 安装脚本 / 脱敏体检）；`references/` — 规范文档

## 核心链路（单案）

1. 建案：`python tools/new_case.py "<发明名称>"`
2. 按模板撰写 `02_draft/交底书-vN.md`（12 节：零~八 + 3 个无编号节）
3. 转写：`PYTHONPATH="" .venv_patent/Scripts/python.exe tools/md2docx.py "cases/<案>/02_draft/交底书-vN.md" "cases/<案>/04_docx/<发明名称>-交底书VN.docx"`
4. 校验：`… tools/verify_docx.py <out.docx>`（12 章节匹配 / OMML 公式数 / 图片数 / `$` 残留 / 失败标注）
5. 反向导入（改已有 docx）：`… tools/docx2md.py <已有.docx> <out.md>`
6. 版本管理：`… tools/versioned_output.py "cases/<案>/04_docx" "<发明名称>" 交底书`（修改前先建 V+1 副本）
7. CNIPA 检索（对比文件）：`python tools/crawl/cnipa_epub_search.py --type invention <关键词>`（需 playwright；公开号不带 A 后缀）

## 硬规则（勿违反）

- **版本**：产物命名 `<发明名称>-交底书VN.docx`（V1 起步）；每次修改先复制旧版为 V+1 副本，**旧版永不覆盖**。
- **不编造**：信息不足标 `[待补充]` 并问用户；专利/论文信息必须真实可查。
- **不引 NPL**：不写「据某论文」式引用——把文献方法吸收为方案自身的技术手段。
- **模板**：章节标题逐字一致、无额外章节；改动创新点后须同步重绘全部相关图。
- **格式**：以本机自备的定稿格式基准输出（md2docx 已内置）；公式为 Word 原生 OMML（`$…$` 行内、```latex 块）。
- **脱敏**：不提交含公司/个人信息的文件；新文件入库前跑 `python deploy/privacy_check.py`。
