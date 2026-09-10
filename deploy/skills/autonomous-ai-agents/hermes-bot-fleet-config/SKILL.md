---
name: hermes-bot-fleet-config
description: Use when 批量同步 bot profile 的 provider/model 配置。
---

# Hermes Bot Fleet 配置同步

主窗口 provider/model 变更后同步到 Bot Mode 的多个 profile（如 8 个 patent bot），或排查「bot 还在用旧 provider / 报 provider 无效」类问题。

## 核心坑位（先读这个）

1. **profile 配置完全隔离，不继承主配置**：每个 bot 是 `C:\Users\<user>\AppData\Local\hermes\profiles\<bot>\config.yaml`，`custom_providers` 列表段不会从主配置合并。主窗口改了 provider，bot 不会跟着变——必须逐 profile 显式写入。bot 报「provider 无效/未知」多半是 profile 里缺 `custom_providers` 段。
2. **`HERMES_PROFILE` 环境变量与 `-p` 旗标对 `hermes config` 子命令无效**：`HERMES_PROFILE=xxx hermes config get ...` 返回的是主配置，极易误判「已改好」。只有 `HERMES_HOME="<profiles/<bot> 目录>" hermes config ...` 才真正切到 profile 配置（`chat` 子命令则 `-p <bot>` 正常可用，两者行为不一致）。
3. **`hermes config set` 写不了 `custom_providers` 列表段**（点路径只适合标量）——用 Python yaml 从主配置整段提取后逐 profile 写入。
4. 写 profile yaml 用 `sort_keys=False` + `newline='\n'`，保持 model 段在前、custom_providers 紧随其后的顺序。

## 同步流程（四步）

1. **看现状**：`hermes profile list`（各 bot 当前 model/provider 一目了然）。
2. **model 段**：逐 bot 用 `HERMES_HOME` 循环 `hermes config set model.provider <p>` / `model.default <m>`。
3. **custom_providers 段**：Python yaml 从主配置提取需要的 provider 条目（按 `name` 过滤，别全量复制无关 provider），插入每个 profile 的 model 段之后。
4. **三层验证缺一不可**：
   - CLI 读回：逐 profile `HERMES_HOME=... hermes config get model.default` / `model.provider`
   - yaml 读回：custom_providers 名称集合 == 目标集合
   - **端到端**：`HERMES_HOME=<profile目录> hermes chat -q "你是谁?当前模型名?"` 让 bot 真实出响应并自报模型——配置生效 ≠ 能出模型响应

完整命令、Python 脚本与验证输出示例见 `references/profile-config-sync.md`。

## 适用场景

- 主窗口换 provider/model 后同步 bot fleet
- bot 报 provider/模型不存在（profile 缺 custom_providers）
- 怀疑改了没生效（先用 HERMES_HOME 读回确认，别信 HERMES_PROFILE）
