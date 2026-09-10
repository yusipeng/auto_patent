---
name: hermes-bot-orchestration
description: Use when CLI 直投 Bot Mode 机器人或同步多 profile 配置。
---

# Hermes Bot Mode 多 Bot 调度与配置维护（本机实践）

把任务交给常驻 Bot（Bot Mode profile，如 D:\auto_patent 的 8 个 patent_* bot），或维护这些 profile 的模型配置时用本技能。与 hermes-agent 技能（总纲，受保护）互补：这里只记本机实测过的操作细节与坑。

## 何时 CLI 直投（而非 @ 提及）

主会话没有 `message_agent` 工具（Bot Mode 中继不可用/未注入）时，用 CLI 把任务直接投给真实 bot profile——不要在主会话里自己扮演该 bot。

## `message_agent`/bot-to-bot 失效的根因（2026-09 实测）

CLI 建的 bot 没有 `profile.yaml` 的 `ui_meta.hermes-bots` 块 → `is_bot_mode_managed()`=False → canonical Bot Chat 会话**不注入** `message_agent` 工具与队友名册。**重启桌面版/启动 gateway 都救不了**（gateway 与 managed 标记无关）。判定/修复/规避三种方案见 `references/bot-mode-a2a-diagnosis.md`。要点：用桌面版 Bots 标签 **New Agent**（不是点现有行）重建 bot 才能写 managed 标记；或继续 CLI 直投。

## CLI 直投流程（已验证）

1. **任务书写入临时 txt**（write_file，不走 shell 转义）。骨架见 `templates/bot-task-brief.txt`，要点：
   - 自包含：bot 无主会话上下文，关键词/输入文件路径写全
   - 本轮范围限制（如「阶段一只检索推荐，不建案不下载 PDF」）
   - 声明一次性模式无交互，信息不足标 `[待补充]` 绝不编造
   - 指定交付物格式（-Q 模式 stdout 尾部即最终回复）
   - 网络代理说明（本机 Clash 127.0.0.1:7897）
2. **后台投递**：
   ```bash
   cd /d/auto_patent && hermes -p <bot_name> chat -Q --query-file "C:/Users/<user>/AppData/Local/Temp/<task>.txt"
   ```
   terminal(background=true, notify=true, timeout≥600)。检索类任务实跑 6~10 分钟。
3. **收结果**：process(action=wait) 轮询——单次 wait 上限 180s，到点仍 running 不是错误，继续 wait；notify=true 会在退出时提醒。完成后 action=log 看全文。输出尾部附 `session_id: ...`，需要追问用 `hermes -p <bot> chat --resume <id>` 续聊。
4. **核验再转述**（bot 自报 ≠ 事实）：对外部可查结果（论文存在性、上传、发布状态）先用独立来源抽查，一致才呈给用户。例：论文列表用 arXiv API 逐 id 比对标题/日期（见下）。
5. 把里程碑决策（用户选 1~3 篇等人工确认点）交回用户，不代用户选。

## 新建 bot profile（2026-09-04 实测跑通：复制已托管骨架法）

新增常驻 bot（如 patent_examiner）不必走桌面 New Agent：直接**复制一个已托管 bot 的 profile 骨架**即可获得 managed 标记与全套配置：

```bash
cd "$LOCALAPPDATA/hermes/profiles"
mkdir -p <新bot名>
for f in config.yaml .env .no-bundled-skills auth.json profile.yaml; do
  cp <已有bot名>/$f <新bot名>/ 2>/dev/null
  done
mkdir -p <新bot名>/skills <新bot名>/memories <新bot名>/home
```

关键：`profile.yaml`（含 `ui_meta.hermes-bots`）必须一并复制——这是 is_bot_mode_managed 标记，缺了 message_agent 不注入。config.yaml 复制自同模型 bot 即可（模型配置/自定义 provider 都随迁）。然后写新 SOUL.md 定义角色。

验证三步：① `hermes profile list` 出现新 bot；② `is_bot_mode_managed(home)` 仍 True；③ 用 `message_agent` 发一条问候确认投递成功（target_busy 时改 CLI）。

> **新机器首次部署**（无任何已托管 bot 可复制）时，改用仓库 `deploy/profiles/_skeleton/`（含 `profile.yaml` 托管标记、`.no-bundled-skills`、`config.template.yaml`），运行 `python deploy/install.py --bots` 批量生成 8 个 bot 骨架，再按 `deploy/README.md` 填 Key。

## 同 bot 批量任务：勿并行 message_agent（target_busy）

2026-09-04 实测：一次给同一 bot 并行发 5 条 message_agent（如 examiner 批量审 5 案），Bot Chat 串行处理 → 4 条被拒（`target_busy ... NOT delivered`）。多任务投同一 bot 时逐案写 query-file 用 `hermes -p <bot> chat -Q --query-file <f>` CLI 直投（每个独立进程，互不占用 Bot Chat）。

## 专利审查员预审闭环（patent_examiner 多轮复审）

给 patent_examiner 做授权前预审、驱动 reviser 按审查意见书迭代时，流程/FAIL 分类/缺陷模式/驱动方式见 `references/patent-examiner-review-loop.md`（2026-09-04 5 案全流程实测）。核心：收敛性 FAIL（文本可修）vs 结构性 FAIL（创造性，需数据/降级/发明人决策）；同 bot 批量勿并行 message_agent。

- **arXiv API 必须 https 直连**：`https://export.arxiv.org/api/query?id_list=<id1>,<id2>` 可用；`http://` 或走 Clash 代理会返回空响应（exit 0 但 body 空）。返回空先换 https 直连再怀疑其他原因。
- bioRxiv 对非生物医学主题无结果是预期，不是检索失败。

## Windows 窗口周期性闪烁（bot 工作时）

三个已知上游原因叠加，非用户配置问题：① `cua-driver-serve` 计划任务每次登录闪蓝 PowerShell 窗（issue #97389，可 `Disable-ScheduledTask -TaskName 'cua-driver-serve'`）；② 桌面版每 ~3.5–4min spawn git.exe 探测闪窗（issue #96694）；③ CLI bot 的 bash/git 子进程闪 cmd/bash 窗。缓解：`hermes update` 到最新、禁用 cua 任务、CLI 用 `-Q` 后台跑。详见 `references/bot-mode-a2a-diagnosis.md`。

## Bot profile 配置维护

- **改单个 profile 的 config**：`HERMES_HOME=C:/Users/<user>/AppData/Local/hermes/profiles/<bot> hermes config set KEY VAL`。坑：`HERMES_PROFILE` 对 config 子命令**无效**（仍读主 config.yaml），必须用 HERMES_HOME 指向 profile 目录。
- **custom_providers 按 profile 隔离不合并**：主配置新增/修改 provider（如 deepseek、huoshan-code-plan）后，须同步进每个 bot 的 config.yaml。做法：python+pyyaml 从主 config 抽取目标 provider dict（按 name 过滤），逐 profile 读入→插到 model 段之后→dump 回（sort_keys=False, allow_unicode=True），再逐个 `HERMES_HOME=... hermes config get model.default` CLI 侧复验。
- 端到端实测：挑一个 bot `hermes -p <bot> chat -q "你是谁?用什么模型?"`，确认自报模型与配置一致。
- Bot 名册/角色：`hermes profile list` 总览；各 bot 的 SOUL.md 在 `profiles/<bot>/`。
