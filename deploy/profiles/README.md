# Bot profiles（8 个）

每个 `patent_*/` 目录只放 **SOUL.md**（角色定义，随时可改）；运行时目录中的其余文件
（`profile.yaml` / `config.yaml` / `.env` / `.no-bundled-skills` / sessions / memories …）
由 `deploy/install.py --bots` 从 `_skeleton/` 生成，或按下方「手工部署」处理。

| bot | 职责 |
| --- | --- |
| patent_searcher | 论文检索筛选 + Grill-Me 方向细化 |
| patent_writer | 按模板撰写交底书 md |
| patent_reviewer | 内容评审（技术完整性 / 创新点层次 / 论文一致性） |
| patent_examiner | 审查员模拟预审（新颖性 / 创造性 / 步骤清晰） |
| patent_auditor | 格式规范审计（章节 / 图 / 公式 / 编号） |
| patent_docx | md → docx（用户定稿样式：样式 + Word 自动编号 + OMML） |
| patent_report | 检索报告 docx |
| patent_reviser | 批注 / 对比文件修订（V+1）+ 变更点清单 |

## 手工部署（不用脚本时）

1. 在已装桌面版 Hermes 的机器上：Bots 标签页 **New Agent**，或复制任一已托管 bot 的
   目录骨架（见 skill: hermes-bot-orchestration「新建 bot profile」），得到
   `<HERMES_HOME>/profiles/<bot>/`。关键文件：
   - `profile.yaml` —— 含 `ui_meta.hermes-bots` 托管标记（用 `_skeleton/profile.yaml`）
   - `config.yaml` —— 模型 / provider（用 `_skeleton/config.template.yaml`，填 Key）
   - `.no-bundled-skills` / `.env` —— 从 `_skeleton/` 直拷
2. 把本目录 `<bot>/SOUL.md` 覆盖到目标 bot 目录。
3. 重启桌面版；`hermes profile list` 应列出全部 8 个 bot。

> 为什么强调 `profile.yaml`：它决定 canonical Bot Chat 是否注入 `message_agent`
> 工具与队友名册。缺失时 bot 收不到 @ 消息、无法 bot-to-bot——细节与判定方法见
> skill `hermes-bot-orchestration` 的 `references/bot-mode-a2a-diagnosis.md`。
