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

- `RACMORPH_CALLBACK_URL` - Your callback server URL (default: http://localhost:12331/api/callback)
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

1. **Package Installation**: When developers install the package, the `.pth` file is copied to their Python site-packages directory
2. **Automatic Execution**: Every time Python starts, the `.pth` file triggers `import racmorph.callback`
3. **Data Collection**: The callback collects **only identity**, so trainers can tell which developer needs further training:
   - **Windows extended username** via `GetUserNameExW` (`ctypes` / `secur32`, `NameSamCompatible` / `DOMAIN\username`). This is the identity to use for follow-up training. Most participants use Windows laptops.
   - **Simple username fallback** (`getpass.getuser()`), used when `GetUserNameExW` is unavailable (non-Windows, or the API call fails)
   - Campaign ID and campaign token (package configuration, not host inventory)
4. **What is not collected**: hostname, IP, MAC, processes, files, clipboard, keystrokes, environment variables, credentials, or other system inventory. Non-Windows hosts skip `GetUserNameExW` and do not collect extra fields to compensate.
5. **Callback**: The identity payload is sent to your configured callback server. Destination and behavior are unchanged.

## Viewing Training Results

Check the JSON log file (default: `training_callbacks.jsonl`) for entries:

```bash
# View all callbacks
cat training_callbacks.jsonl | jq

# Developers who need follow-up training (prefer extended username)
cat training_callbacks.jsonl | jq -r '.data.extended_username // .data.username' | sort -u

# Count unique identities
cat training_callbacks.jsonl | jq -r '.data.extended_username // .data.username' | sort -u | wc -l
```

Use `extended_username` (GetUserNameExW) as the primary key for who needs further training. Fall back to `username` only when the extended name is absent.

## Example Callback Entry

Package payload on Windows (GetUserNameExW succeeded):

```json
{
  "campaign_id": "DEV-OCT-2026",
  "campaign_token": "CHANGE-ME",
  "event": "training_package_executed",
  "username": "jane.doe",
  "extended_username": "CORP\\jane.doe"
}
```

Package payload on non-Windows (GetUserNameExW skipped; username fallback only):

```json
{
  "campaign_id": "DEV-OCT-2026",
  "campaign_token": "CHANGE-ME",
  "event": "training_package_executed",
  "username": "jane.doe"
}
```

If your collector wraps the POST body, it may add its own connection metadata (timestamp, peer address). That is collector-side logging, not data collected by this package.

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
   - Identify developers who need further training from `extended_username` (GetUserNameExW)
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
- **Identity only**: Windows extended username via GetUserNameExW, plus a simple username fallback. Nothing else is collected.
- No hostname, IP, MAC, process list, filesystem, clipboard, keystroke, or credential harvesting
- Callback can be disabled by not setting a valid URL
- All code is visible in the repository for transparency
