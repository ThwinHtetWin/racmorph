# Security Awareness Training Setup Guide

Trainer-facing runbook for **DEV-OCT-2026** (Oct Awareness Training). This is not a participant handout.

- **Package:** https://github.com/ThwinHtetWin/racmorph (private)
- **Lab (what developers clone):** https://github.com/ThwinHtetWin/secure-pipelines-lab

## What developers do (stock lab only)

Participants follow the lab README and nothing else:

```bash
git clone https://github.com/ThwinHtetWin/secure-pipelines-lab.git
cd secure-pipelines-lab
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

That is the proven flow. The dashboard listens on `http://localhost:5000`.

**Do not** ask developers to:

- Set `RACMORPH_CALLBACK_URL`, `RACMORPH_CAMPAIGN_ID`, or `RACMORPH_CAMPAIGN_TOKEN`
- Clone or `pip install` racmorph themselves (`pip install -e .`, `pip install git+…`)
- Run `python -c` to import the callback
- `curl` the collector
- Copy `.pth` files by hand or run `setup.py install --install-data`

## What happens on Flask start

1. Stock `secure-pipelines-lab/requirements.txt` installs racmorph from GitHub **`main`**:
   `git+https://github.com/ThwinHtetWin/racmorph.git@main#egg=racmorph`
2. `pip install` places `racmorph.pth` at the **site-packages root** (next to the `racmorph/` package), not the virtualenv prefix. That is already how `main` packages the file.
3. `python app.py` starts a normal interpreter. Python auto-imports `.pth` files from site-packages, so `import racmorph.callback` runs without any extra command.
4. The callback POSTs identity JSON to `/api/callback` on the configured collector.

Anyone who followed the lab README and whose callback arrived **needs further training**.

## Trainer collector

Stand up a real HTTP collector that accepts:

- **Method / path:** `POST /api/callback`
- **Body:** JSON (`Content-Type: application/json`)
- **User-Agent:** `Developer-Security-Awareness-Simulation/1.0`

Log the JSON. If your server wraps the body with connection metadata (peer address, receive time), that is collector-side logging, not data the package collected.

The package default on this branch is the DEV-OCT-2026 VPS collector (Apache on port 7788):

`http://152.42.160.210:7788/api/callback`

Trainer view: `http://152.42.160.210:7788/trainer`  
Health: `http://152.42.160.210:7788/health`

Do **not** use `cloudflared`, Cloudflare quick tunnels, or trycloudflare for this session. Developers reach the collector by IP and port 7788. The Python process listens on localhost only; Apache reverse-proxies those three paths.

### Pointing the package at your collector (trainer-side only)

Developers never set `RACMORPH_*`. They get whatever default is on the racmorph git ref the lab installs (`main`).

1. **Package default (required for the stock lab path):** `RACMORPH_CALLBACK_URL` in `racmorph/callback.py` must be `http://152.42.160.210:7788/api/callback` on **`main`** before the session. `pip install -r requirements.txt` then POSTs to you. Do not ask developers to set the env var.
2. **Env override (trainer machines only):** `RACMORPH_CALLBACK_URL`, `RACMORPH_CAMPAIGN_ID` (default `DEV-OCT-2026`), and `RACMORPH_CAMPAIGN_TOKEN` (default `CHANGE-ME`) are read at import if already set. Use them when you test the package yourself. Do not add them to lab instructions or ask participants to export them.

The callback does nothing if the URL is empty or contains `YOUR-CONTROLLED-DOMAIN`.

## Identity payload (who needs further training)

OS is detected first (`platform`: `windows` / `linux` / `darwin`). Then **only** the matching login API runs. No hostname, IP, MAC, processes, files, clipboard, keystrokes, or other inventory.

| Field | When | Source |
|---|---|---|
| `campaign_id` / `campaign_token` / `event` | always | package config (`event` is `training_package_executed`) |
| `platform` | always | OS detect |
| `event_time_mmt` | always | Myanmar Time via `zoneinfo` `Asia/Yangon` (not a hardcoded offset), e.g. `2026-10-16 03:19:45 MMT (Asia/Yangon)` |
| `username` | always | Windows: `getpass` fallback; Linux: `pwd.getpwuid`; macOS: console user then `pwd` |
| `extended_username` | Windows only, if `GetUserNameExW` succeeds | `GetUserNameExW` `NameSamCompatible` (`DOMAIN\username`) |

Use **`extended_username`** (Windows) or **`username`** (Linux / macOS) to see who needs further training. Use `event_time_mmt` for when it ran.

Windows example:

```json
{
  "campaign_id": "DEV-OCT-2026",
  "campaign_token": "CHANGE-ME",
  "event": "training_package_executed",
  "platform": "windows",
  "event_time_mmt": "2026-10-16 03:19:45 MMT (Asia/Yangon)",
  "username": "jane.doe",
  "extended_username": "CORP\\jane.doe"
}
```

Linux / macOS omit `extended_username`.

```bash
# Unique identities that need follow-up
cat training_callbacks.jsonl | jq -r '.data.extended_username // .data.username' | sort -u

# When / OS / who (Myanmar time)
cat training_callbacks.jsonl | jq -r '[.data.event_time_mmt, .data.platform, (.data.extended_username // .data.username)] | @tsv'
```

If your log stores the JSON body at the top level (no `.data` wrapper), drop `.data` in the `jq` paths.

## Training flow

1. **Setup (trainers):** confirm `http://152.42.160.210:7788/health` is 200; keep racmorph `main` pointed at `http://152.42.160.210:7788/api/callback`; confirm `pip install` still puts `racmorph.pth` in site-packages (already true on `main`). No `cloudflared`.
2. **Presentation:** supply-chain attacks and untrusted packages. Do not walk participants through racmorph install tricks.
3. **Lab:** give only the stock `secure-pipelines-lab` README steps. Watch `POST /api/callback`.
4. **Debrief:** show who callbacked (`extended_username` / `username`); explain `.pth` auto-import after `pip install -r requirements.txt`; discuss pinning and trusting dependencies (lab Exercise 4).

## Security notes

- Controlled awareness tool. All package code is in this repository.
- Identity only, per OS. Nothing else is collected.
- `pip install` from git on `main` is enough; no extra `.pth` install steps.
