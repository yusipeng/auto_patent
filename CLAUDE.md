# CLAUDE.md — auto_patent（Claude Code 项目指南）

@AGENTS.md

## Claude Code 备注

- 技能安装：`python deploy/agent_install.py --claude-code` → `~/.claude/skills/`（本机已装可直接 `/skills` 查看）
- 五个技能：`patent-workflow`（总纲）/ `docx-from-markdown` / `cn-patent-pdf-download` / `hermes-bot-orchestration` / `hermes-bot-fleet-config`
- 长任务建议：打印/管道模式 `claude -p "<task>" --max-turns N`；本仓库文本以中文为主，注意保持 UTF-8。
