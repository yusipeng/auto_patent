# Profile 配置批量同步完整操作

实测环境：Windows 11 + git-bash，7 个 patent bot profile。同步 huoshan-code-plan/deepseek-v4-flash 全部验证通过（2026-09）。

## 1. 现状

```bash
hermes profile list
# ◆default glm-5.3
#   patent_auditor  deepseek-v4-flash-free   ← 待同步
#   ...（7 个 bot）
```

## 2. model 段（HERMES_HOME 循环）

```bash
for p in patent_auditor patent_docx patent_report patent_reviewer patent_reviser patent_searcher patent_writer; do
  export HERMES_HOME="C:/Users/<user>/AppData/Local/hermes/profiles/$p"
  hermes config set model.provider huoshan-code-plan
  hermes config set model.default deepseek-v4-flash
done
```

注意：`hermes config set` 会回显 `✓ Set ... in <profile路径>\config.yaml`，看路径确认写对了 profile。

## 3. custom_providers 段（Python yaml）

```bash
python - <<'PYEOF'
import yaml

base = r'C:/Users/<user>/AppData/Local/hermes'
main = yaml.safe_load(open(base + '/config.yaml', encoding='utf-8'))

# 从主配置提取目标 provider 段（按 name 过滤，避免全量复制）
want = [p for p in main.get('custom_providers', [])
        if p.get('name') in ('deepseek', 'huoshan-code-plan')]

bots = ['patent_auditor','patent_docx','patent_report','patent_reviewer',
        'patent_reviser','patent_searcher','patent_writer']
for b in bots:
    path = f'{base}/profiles/{b}/config.yaml'
    cfg = yaml.safe_load(open(path, encoding='utf-8')) or {}
    new = {}
    for k, v in cfg.items():
        new[k] = v
        if k == 'model':          # custom_providers 紧随 model 段
            new['custom_providers'] = want
    if 'custom_providers' not in new:
        new['custom_providers'] = want
    yaml.dump(new, open(path, 'w', encoding='utf-8', newline='\n'),
              sort_keys=False, allow_unicode=True)
    print(f'{b}: custom_providers x{len(want)} 已写入')
PYEOF
```

## 4. 三层验证

```bash
# 层1+2：CLI 读回 + yaml 读回
for p in patent_auditor patent_docx patent_report patent_reviewer patent_reviser patent_searcher patent_writer; do
  HERMES_HOME="C:/Users/<user>/AppData/Local/hermes/profiles/$p" hermes config get model.default | tr -d '\r\n'
  echo -n " / "
  HERMES_HOME="C:/Users/<user>/AppData/Local/hermes/profiles/$p" hermes config get model.provider | tr -d '\r\n'
  echo "  <- $p"
done

# 层3：端到端，让 bot 自报模型
HERMES_HOME="C:/Users/<user>/AppData/Local/hermes/profiles/patent_searcher" \
  hermes chat -q "你是谁?用一句话回答,然后说明你当前使用的模型名"
# 期望输出含: 当前使用的模型名是 deepseek-v4-flash
```

## 踩坑实录

- `HERMES_PROFILE=patent_writer hermes config get model.provider` → 返回主配置的值，当时主配置恰好也是同值，几乎骗过去；`hermes config path` 才暴露还是主 config.yaml。结论：验证 profile 配置一律 `HERMES_HOME` + `config path` 确认目标文件。
- profile 里原 model 段指向 `opencode-free`/`deepseek-v4-flash-free`（上个周期的免费方案），主配置切换后 bot 静默落后——这是本同步任务的典型起因。
- Windows git-bash 下 `tr -d '\r\n'` 清理 hermes 输出的 CRLF 再拼接。
