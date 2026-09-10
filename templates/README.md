# templates/ — 模板目录（模板不入库，需自备）

出于信息安全，本仓库**不提供**任何含公司信息 / 个人信息的 docx 模板；请自备（下表为建议命名）：

| 文件（建议命名） | 用途 | 获取方式 |
| --- | --- | --- |
| `技术交底书模板-发明新型-用户定稿.docx` | ★输出格式基准（md2docx 默认模板） | 用内部最新交底书模板 + 一份手工定稿文档，经 `tools/make_template.py` 提取 |
| `技术交底书模板-发明新型.docx` | 官方原版留档（可选） | 内部获取 |
| `检索报告模板（修订版）.docx` | 检索报告输出模板 | 内部获取 |

## 生成「格式基准模板」（推荐）

```bash
# 从一份手工调好格式的交底书 docx 提取空白格式模板
#（保留样式 / 编号定义 / 封面表 / 页脚 / 页面设置，清空正文）
PYTHONPATH="" .venv_patent/Scripts/python.exe tools/make_template.py \
    "<你的定稿.docx>" "templates/技术交底书模板-发明新型-用户定稿.docx"
```

- md2docx 默认读取 `templates/技术交底书模板-发明新型-用户定稿.docx`；如用别的文件名，请改 `tools/md2docx.py` 顶部 `DEFAULT_TEMPLATE`。
- 更换模板后建议跑一遍冒烟：`tools/md2docx.py` 生成 → `tools/verify_docx.py` 校验（12 章节匹配）。

> 本目录的 `*.docx` 默认被 `.gitignore` 忽略；请勿把含公司 / 个人信息的模板提交进公开仓库（提交前运行 `python deploy/privacy_check.py`）。
