# Bot-to-bot (message_agent) not working — root cause & fix

## Symptom

- In the main (default) desktop chat, typing `@patent_auditor …` resolves the mention but there is **no `message_agent` tool** in the session, so the bot can't be messaged directly — only CLI works (`hermes -p <bot> chat`).
- Bot Chats exist in each profile's `state.db` (title `Bot Chat`, `hidden=1`), gateway may be running — still no `message_agent`.

## Root cause (verified by code, 2026-09-03)

`message_agent` is injected **only** into a canonical `Bot Chat` session on a **Bot-Mode-managed install**. Three gates (tools/bot_mode_dm.py `ensure_message_agent_tool` + tools/bot_mode_probe.py):

1. session title == `"Bot Chat"` ✓ (usually present)
2. `is_bot_mode_managed(home)` == True  ← **the failing gate**
3. managed-install check

`is_bot_mode_managed()` is True when **ANY profile** has a `profile.yaml` containing a `ui_meta.hermes-bots` block. Bots created via **CLI** (`hermes profile create`, or copied/imported) have `config.yaml` + `SOUL.md` but **NO `profile.yaml`** → `is_bot_mode_managed()` = False → protocol section is empty → `message_agent` never injected. Desktop Bots created via **New Agent** in the Bots tab DO write `profile.yaml` with `ui_meta.hermes-bots`.

**Restarting the desktop / starting the gateway does NOT fix it.** Opening a Bot Chat session creates the session row but not the `profile.yaml` marker.

## Verify (read-only probe)

```bash
cd "$LOCALAPPDATA/hermes/hermes-agent" && PYTHONPATH= python -c "
import sys; sys.path.insert(0, r'C:\Users\<user>\AppData\Local\hermes\hermes-agent')
from tools.bot_mode_probe import is_bot_mode_managed, get_bot_mode_protocol_section
home = r'C:\Users\<user>\AppData\Local\hermes'
print('is_bot_mode_managed:', is_bot_mode_managed(home))
print('protocol section len:', len(get_bot_mode_protocol_section(home)))
"
# expect: is_bot_mode_managed: False / protocol section len: 0  → not managed
```

Check markers: `find "$LOCALAPPDATA/hermes/profiles" -maxdepth 2 -name profile.yaml` — none → not managed.

## Fixes

- **A (clean, recommended):** in desktop Bots tab use **New Agent** (NOT clicking an existing row) to (re)create each bot with the same name, pin provider/model in Advanced, select skills. This writes `profile.yaml` + `ui_meta.hermes-bots` → managed → `message_agent` injected on the Bot Chat's next turn. Old CLI-made profiles can be deleted to avoid name clash.
- **B (manual, risky):** hand-write a `profile.yaml` with `ui_meta.hermes-bots` per profile. The desktop plugin SDK may expect more fields (avatar/section/group); test on ONE bot first.
- **C (no change):** keep using CLI `hermes -p <bot> chat -Q` — unaffected, just no A2A tool.

## Windows: other windows periodically flashing while bots work

Three stacked causes, all upstream (not user config):

1. `cua-driver-serve` Scheduled Task (installed with Computer Use toolset, runs at login): flashes a 2–3s blue PowerShell console on every boot — GitHub issue #97389. Disable: `Disable-ScheduledTask -TaskName 'cua-driver-serve'` (only if not using the cua desktop driver).
2. Desktop app periodically spawns `git.exe` (~every 3.5–4 min, update-badge + review probes) which flashes a console window on Windows — issue #96694 (`windowsHide` inert against pythonw.exe; fix = CREATE_NO_WINDOW, land via `hermes update`).
3. CLI bot runs spawn bash/git subprocesses, each flashing a cmd/bash window — issues #42544 / #52310.

Mitigations: `hermes update` to latest (594+ commits behind at time of writing), disable cua-driver task, prefer `-Q` background CLI runs, or use Bot-Mode group chats/@mentions instead of spawning a CLI process per task.
