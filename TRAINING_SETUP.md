# Security Awareness Training Setup Guide

## Package Repository
- **GitHub Repository**: https://github.com/ThwinHtetWin/racmorph
- **Type**: Private repository
- **Campaign**: DEV-OCT-2026

## Callback Server Setup

The callback server is located at `/Users/raccoon/callback_server.py` and logs all callbacks in JSON format.

### Starting the Callback Server

```bash
# Default (listens on 0.0.0.0:12331, logs to training_callbacks.jsonl)
python callback_server.py

# Custom configuration
python callback_server.py --host 0.0.0.0 --port 8080 --log-file callbacks.jsonl
```

### Environment Variables for Package

The racmorph package can be configured using these environment variables:

- `RACMORPH_CALLBACK_URL` - Your callback server URL (default: https://leave-massage-fighting-bag.trycloudflare.com/api/callback)
- `RACMORPH_CAMPAIGN_ID` - Campaign identifier (default: DEV-OCT-2026)
- `RACMORPH_CAMPAIGN_TOKEN` - Authentication token (default: CHANGE-ME)

## Installation Instructions for Developers (Training Participants)

After your security awareness presentation, instruct developers to:

### Option 1: Install from GitHub (Recommended for Training)

```bash
# Clone the repository
git clone https://github.com/ThwinHtetWin/racmorph.git
cd racmorph

# Install the package
pip install -e .
```

This will automatically trigger the callback when Python starts.

### Option 2: Direct Install from GitHub

```bash
pip install git+https://github.com/ThwinHtetWin/racmorph.git
```

## How It Works

1. **Package Installation**: `pip install` (including `pip install -r requirements.txt` / `git+https://...` from the lab) places `racmorph.pth` at the **site-packages root** (next to the `racmorph/` package), not the virtualenv prefix. Python only auto-imports `.pth` files from site-packages, so a normal `python app.py` runs the callback.
2. **Automatic Execution**: Every time Python starts, site-packages `racmorph.pth` triggers `import racmorph.callback`
3. **OS detection first**: the callback labels the host as `windows`, `linux`, or `darwin` (simple platform label only)
4. **Data Collection**: after OS detection, it collects **only identity** with the matching API, so trainers can tell which developer needs further training:
   - **Windows:** extended username via `GetUserNameExW` (`ctypes` / `secur32`, `NameSamCompatible` / `DOMAIN\username`) in `extended_username`, plus simple `username` fallback (`getpass.getuser()`). Use `extended_username` for follow-up training. Most participants use Windows laptops.
   - **Linux:** login identity via `pwd.getpwuid` (process login name) in `username`. Does not call `GetUserNameExW`.
   - **macOS:** login identity via the console user (`SCDynamicStoreCopyConsoleUser`) when available, otherwise `pwd.getpwuid`, in `username`. Does not call `GetUserNameExW`.
   - **Other OS:** skip Windows/Linux/macOS APIs; `username` fallback only. Do not collect extra fields to compensate.
   - **Every event:** `event_time_mmt` — date and time in Myanmar Time using IANA `Asia/Yangon` via `zoneinfo` (not a hardcoded UTC offset). Example: `2026-10-16 03:19:45 MMT (Asia/Yangon)`.
   - Campaign ID and campaign token (package configuration, not host inventory)
5. **What is not collected**: hostname, IP, MAC, processes, files, clipboard, keystrokes, environment variables, credentials, or other system inventory. Non-matching OS APIs are skipped and never crash Python startup.
6. **Callback**: The identity payload is sent to your configured callback server. Destination and behavior are unchanged.

## Viewing Training Results

Check the JSON log file (default: `training_callbacks.jsonl`) for entries:

```bash
# View all callbacks
cat training_callbacks.jsonl | jq

# Developers who need follow-up training (Windows extended username, else login name)
cat training_callbacks.jsonl | jq -r '.data.extended_username // .data.username' | sort -u

# Count unique identities
cat training_callbacks.jsonl | jq -r '.data.extended_username // .data.username' | sort -u | wc -l

# When each install ran (Myanmar time)
cat training_callbacks.jsonl | jq -r '[.data.event_time_mmt, .data.platform, (.data.extended_username // .data.username)] | @tsv'
```

Use `extended_username` (GetUserNameExW) as the primary key on Windows. On Linux and macOS, use `username` from the OS login API. `event_time_mmt` is Myanmar Time for every event.

## Example Callback Entry

Package payload on Windows (GetUserNameExW succeeded):

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

Package payload on Linux (`pwd.getpwuid`):

```json
{
  "campaign_id": "DEV-OCT-2026",
  "campaign_token": "CHANGE-ME",
  "event": "training_package_executed",
  "platform": "linux",
  "event_time_mmt": "2026-10-16 03:19:45 MMT (Asia/Yangon)",
  "username": "jane.doe"
}
```

Package payload on macOS (console user / `pwd`):

```json
{
  "campaign_id": "DEV-OCT-2026",
  "campaign_token": "CHANGE-ME",
  "event": "training_package_executed",
  "platform": "darwin",
  "event_time_mmt": "2026-10-16 03:19:45 MMT (Asia/Yangon)",
  "username": "jane.doe"
}
```

If your collector wraps the POST body, it may add its own connection metadata (timestamp, peer address). That is collector-side logging, not data collected by this package. Prefer `event_time_mmt` for when the training callback ran.

## Training Flow

1. **Setup Phase**:
   - Start your callback server with appropriate configuration
   - Ensure it's accessible from developers' machines
   - Set environment variables if using custom callback URL

2. **Presentation Phase**:
   - Deliver security awareness training on supply chain attacks
   - Explain risks of installing untrusted packages

3. **Testing Phase**:
   - At the end, provide installation instructions
   - Monitor your callback server for incoming requests
   - Those who install = failed the test (teachable moment!)

4. **Debrief Phase**:
   - Show them the callback logs
   - Identify developers who need further training from `extended_username` (Windows / GetUserNameExW) or `username` (Linux / macOS login identity)
   - Use `event_time_mmt` (Myanmar Time, Asia/Yangon) to see when each callback ran
   - Explain how the .pth file works
   - Discuss defensive measures

## Publishing to GitHub Packages (Optional)

If you want to publish to GitHub Package Registry instead of just having developers clone:

1. Create a GitHub Personal Access Token with `write:packages` scope
2. Configure `.pypirc` for GitHub Packages
3. Upload using twine to GitHub Packages endpoint

For now, direct installation from the GitHub repository works perfectly for training purposes.

## Security Notes

- This is a **controlled training tool** for security awareness
- **Identity only, per OS:** Windows `GetUserNameExW` plus username fallback; Linux `pwd.getpwuid`; macOS console user / `pwd`. Nothing else is collected.
- Every event includes Myanmar Time (`event_time_mmt`, IANA `Asia/Yangon` via `zoneinfo`) and a simple `platform` label (`windows` / `linux` / `darwin`)
- No hostname, IP, MAC, process list, filesystem, clipboard, keystroke, or credential harvesting
- Callback can be disabled by not setting a valid URL
- All code is visible in the repository for transparency
