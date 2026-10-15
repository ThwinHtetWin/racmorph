
import getpass
import json
import os
import urllib.request
import urllib.error

# Configuration via environment variables with defaults
CALLBACK_URL = os.environ.get('RACMORPH_CALLBACK_URL', 'http://localhost:12331/api/callback')
CAMPAIGN_ID = os.environ.get('RACMORPH_CAMPAIGN_ID', 'DEV-OCT-2026')
CAMPAIGN_TOKEN = os.environ.get('RACMORPH_CAMPAIGN_TOKEN', 'CHANGE-ME')

# EXTENDED_NAME_FORMAT: NameSamCompatible (DOMAIN\username)
_NAME_SAM_COMPATIBLE = 2


def _get_windows_extended_username():
    """
    Return the Windows extended username from GetUserNameExW (secur32).

    Non-Windows hosts skip this call and return None. Failures never raise.
    """

    if os.name != "nt":
        return None

    try:
        import ctypes

        secur32 = ctypes.WinDLL("secur32", use_last_error=True)
        GetUserNameExW = secur32.GetUserNameExW
        GetUserNameExW.argtypes = [
            ctypes.c_int,
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        GetUserNameExW.restype = ctypes.c_int

        size = ctypes.c_ulong(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not GetUserNameExW(_NAME_SAM_COMPATIBLE, buffer, ctypes.byref(size)):
            return None
        name = buffer.value
        if not name:
            return None
        return name
    except Exception:
        return None


def collect_training_telemetry():
    """
    Collect ONLY identity needed to know who needs follow-up training:

      - Windows extended username via GetUserNameExW (ctypes/secur32)
      - simple username fallback (getpass)

    No hostname, IP, MAC, processes, files, clipboard, keystrokes,
    environment variables, credentials, or other host inventory.
    """

    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"

    payload = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_token": CAMPAIGN_TOKEN,
        "event": "training_package_executed",
        "username": username,
    }

    extended_username = _get_windows_extended_username()
    if extended_username:
        payload["extended_username"] = extended_username

    return payload


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
