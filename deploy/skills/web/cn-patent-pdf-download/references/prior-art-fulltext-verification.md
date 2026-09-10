# 对比文件细节核验流程（reviewer 报"描述超出归档摘要"时）

## 触发场景
patent_reviewer 评审时发现交底书 3.2 对某对比文件的描述（具体数值/机制）**超出了 01_source 已归档的摘要**，打回要求"补全说明书核实或删除无据细节"。

**教训**：摘要往往不含实施例/权利要求的具体数值（如 CN113807252A 摘要只说"分年龄段管控"，具体"等级1每天半小时/等级2每天45分钟"在说明书实施例里）。交底书引用对比文件细节**必须可溯源**，审查中引用不实会削弱 3.3 差异化论证可信度。

## 核验步骤（2026-09-04 儿童守护案件实测，3/3 全部证实描述有据）

1. **优先抓 Google Patents `/en` 完整文本**（不是 `/zh`，中文页乱码/偶发失败）:
   `web_extract(urls=["https://patents.google.com/patent/CNxxxxxxxA/en"])`
   - 大文件产出存到 `~/.hermes cache/web/*.md`（footnote 给路径），用 read_file + `grep` 搜具体数值/关键词
   - CN 专利 claims 是英文机翻但结构、数值、选项完整，够核验
2. **在全文搜目标细节**：`grep -n -B2 -A2 "half an hour|45 min|eye exercises|play Current Content" ...md`，确认原文真实存在
3. **每件专利归档一份核实材料**到 `01_source/<公开号>-核实材料.md`，格式：
   - 标题+来源（Google Patents /en web_extract，日期）
   - **核实结论**（针对 reviewer 的 C 项：成立/不成立 + 原文引用）
   - 技术方案概要 + 与本案区别特征对应
4. **判定性质**：
   - 描述**有据但缺出处** → 不改内容，让 reviser 在 3.2 补出处标注（"（据其说明书实施例）""（据其权利要求4）"）+ 指向 01_source 核实材料
   - 描述**失真** → 删除/改写无据细节
5. 让 reviser 处理 + 补 C4 类连带问题后，产出新版本 → 重跑 reviewer+auditor 复核

## 本机实测核验结果（儿童守护案件）
| reviewer C 项 | 对比文件 | 核实细节 | 依据 | 结论 |
|---|---|---|---|---|
| C1 等级1半小时/等级2 45分钟 | CN113807252A | 说明书实施例明确 Level 1 half an hour every day / Grade 2 45 minutes every day（还有 Level 0/3） | /en Description | ✅ 有据 |
| C2 眼保健操/休闲音乐 | CN102469366A | 权4/5：进入视力保护模式播放眼保健操或休闲音乐或控制待机 | /en Claims 4/5 | ✅ 有据 |
| C3 播放完当前内容后停止 | CN108769790A | 权4：控制第一终端播放完当前内容后停止播放并关闭屏幕（stop playing and closing screen after Current Content） | /en Claims 4 | ✅ 有据 |

## 相关
- 来源路由/PDF 下载：cn-patent-pdf-download SKILL.md 主体
- 著录+摘要批量抓：cnipa_epub_search.py（见 batch-fetch-cn-refs.md）
- CNIPA 详情页全文抓取（`cnipa_detail_fetch.py`，直接 goto /patent/xxx）：**2026-09-04 实测过 WAF 超时不可靠**（180s 内未出 #searchStr），别依赖它；详情核验走 Google Patents /en 更稳
