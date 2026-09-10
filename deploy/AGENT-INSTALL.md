# 给 AI Agent 的安装指南（Claude Code / Codex / WorkBuddy / CodeBuddy / 通用）

本仓库的 5 个 skill 采用 **Agent Skills 开放标准**（`SKILL.md` + `references/`），可安装到任何支持该标准的 Agent：

| skill | 用途 | 适用 |
| --- | --- | --- |
| `patent-workflow` | **流水线总纲**：8 Bot 名册、4 人工确认点、版本/复核规则、工具链索引 | 全部 Agent |
| `docx-from-markdown` | md→docx 转写（模板样式、Word 自动编号、OMML 公式） | 全部 |
| `cn-patent-pdf-download` | 对比文件获取（CNIPA / drugfuture / 来源路由） | 全部 |
| `hermes-bot-orchestration` | Hermes Bot 调度、托管标记排障、审查员预审闭环 | Hermes 场景 |
| `hermes-bot-fleet-config` | Hermes 多 profile 的 provider/model 同步 | Hermes 场景 |

三种使用方式：

1. **其他 Agent 用户** → `python deploy/agent_install.py --all`（本指南）
2. **Hermes 用户** → `python deploy/install.py --all`（8 bot + skills，见 `deploy/README.md`）
3. **只想让 Agent 读工作流** → 直接给它看根目录 `AGENTS.md` 与 `deploy/skills/patent/patent-workflow/SKILL.md`

## 一键指令（复制给你的 Agent 即可）

```text
请安装 auto_patent 专利流水线技能（私有仓库，需已配置 git 凭据）：
1) git clone https://github.com/<owner>/auto_patent.git D:/auto_patent  （已存在则 cd 后 git pull）
2) cd D:/auto_patent && python deploy/agent_install.py --list
3) python deploy/agent_install.py --all
4) 验证：列出你的技能目录下新增的 patent-workflow / docx-from-markdown / cn-patent-pdf-download /
   hermes-bot-orchestration / hermes-bot-fleet-config 五个目录
5) 阅读 D:/auto_patent/AGENTS.md 与 deploy/skills/patent/patent-workflow/SKILL.md，
   之后按该工作流协助处理专利交底书任务
```

## 各 Agent 的安装路径（官方约定，2026-09）

| Agent | 用户级（本机全局） | 项目级（随仓库） | 查看/调用 |
| --- | --- | --- | --- |
| **Claude Code** | `~/.claude/skills/<name>/` | `<repo>/.claude/skills/` | `/skills` 查看；`/patent-workflow` 调用 |
| **OpenAI Codex**（CLI/IDE） | `~/.agents/skills/<name>/` | `<repo>/.agents/skills/`（自 CWD 向上扫描至仓库根） | `/skills` 或 `$patent-workflow` 提及 |
| **腾讯 WorkBuddy** | `~/.workbuddy/skills/<name>/` | — | 「技能」面板查看；「添加技能→上传技能包」亦可导入 |
| **腾讯 CodeBuddy Code** | `~/.codebuddy/skills/<name>/` | — | 用户级 Skills 目录（官方文档） |
| **通用**（Cursor / OpenCode / Amp 等 AGENTS.md 规范） | — | 仓库根 `AGENTS.md` | Agent 打开仓库自动读取项目指南 |

> Windows 上 `~` = `C:\Users\<你>`；`<repo>` 建议克隆到 `D:\auto_patent`（全部文档默认此路径）。
> Claude Code 首次创建 `~/.claude/skills` 顶层目录后需重启一次；其余文件级变动实时生效。

## 命令速查（`deploy/agent_install.py`）

```bash
python deploy/agent_install.py --list          # 探测本机 Agent 与技能目录现状（默认）
python deploy/agent_install.py --all           # 安装到全部已探测到的 Agent
python deploy/agent_install.py --claude-code   # 仅 Claude Code
python deploy/agent_install.py --codex         # 仅 Codex（~/.agents/skills）
python deploy/agent_install.py --workbuddy     # 仅 WorkBuddy
python deploy/agent_install.py --codebuddy     # 仅 CodeBuddy Code
python deploy/agent_install.py --project       # 装进仓库内 .claude/skills 与 .agents/skills（可随仓库分发）
python deploy/agent_install.py --remove --all  # 卸载
python deploy/agent_install.py --force         # 覆盖已存在 / 强制移除
python deploy/agent_install.py --home DIR      # 覆盖用户主目录（测试用）
```

幂等：已存在默认跳过；卸载时内容与仓库不一致的版本默认保留（`--force` 才删）。

## 手动安装（不用脚本）

把 `deploy/skills/<category>/<skill>/` **整个目录**复制到目标技能目录，**目录名必须是 skill 名**（不要在中间保留 category 层）：

```bash
# Claude Code — 全部 5 个
for s in patent/patent-workflow productivity/docx-from-markdown web/cn-patent-pdf-download \
         autonomous-ai-agents/hermes-bot-orchestration autonomous-ai-agents/hermes-bot-fleet-config; do
  cp -r "deploy/skills/$s" ~/.claude/skills/
done
# 其余 Agent 只需替换目标目录：~/.agents/skills/（Codex）、~/.workbuddy/skills/（WorkBuddy）
```

## 验证

- 文件级：`ls ~/.claude/skills | grep -E "patent|hermes"`（应看到 5 个）
- Claude Code：`/skills` 列表出现 5 个中文描述技能；或直接问「patent-workflow 是什么」
- Codex：`/skills`；`$patent-workflow 介绍一下工作流`
- WorkBuddy：技能面板「已安装」出现 5 个
- 语义级（推荐）：让 Agent「读 patent-workflow 并复述 4 个人工确认点」——能复述即安装生效

## 常见问题

| 现象 | 处理 |
| --- | --- |
| 技能没出现 | 目录层级不对：必须是 `<skills目录>/<skill名>/SKILL.md`，不能多套一层 |
| Claude Code 找不到 | 首次创建 `~/.claude/skills` 目录后需重启一次 |
| Codex 找不到 | 用户级在 `~/.agents/skills`；项目级在仓库 `.agents/skills`（勿放 `~/.codex/skills`） |
| WorkBuddy 找不到 | 确认放 `~/.workbuddy/skills/`；重启 WorkBuddy 或重新打开技能面板 |
| 私有仓库 clone 失败 | 先配置 GitHub 凭据（HTTPS token 或 SSH key） |
| 想彻底移除 | `python deploy/agent_install.py --remove --all`（或按 Agent 单独 `--remove`） |
