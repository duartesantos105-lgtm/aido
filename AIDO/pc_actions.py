"""PC automation actions for AIDO — open browsers, explorer, run scripts."""
import os
import sys
import subprocess
import webbrowser
import shutil
from pathlib import Path
import auth

try:
    import winreg
except Exception:
    winreg = None

PROJECT_ROOT = Path(__file__).parent


# ── Helpers ───────────────────────────────────────────────────────────────

def _normalize_url(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def is_allowed_script(path: str) -> bool:
    """Ensure a script path is within the project directory."""
    try:
        p = (PROJECT_ROOT / path).resolve()
        return PROJECT_ROOT in p.parents or p == PROJECT_ROOT
    except Exception:
        return False


# ── Opera detection ───────────────────────────────────────────────────────

def find_opera_exe():
    """Locate the Opera / Opera GX executable via paths, PATH, and registry."""
    env_path = os.environ.get("OPERA_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    local = os.environ.get("LOCALAPPDATA")
    pf = os.environ.get("PROGRAMFILES")
    pf_x86 = os.environ.get("PROGRAMFILES(X86)")

    possible = []
    if local:
        possible += [os.path.join(local, "Programs", "Opera GX", "launcher.exe"),
                     os.path.join(local, "Programs", "Opera", "launcher.exe")]
    if pf:
        possible += [os.path.join(pf, "Opera GX", "launcher.exe"),
                     os.path.join(pf, "Opera", "launcher.exe")]
    if pf_x86:
        possible += [os.path.join(pf_x86, "Opera GX", "launcher.exe"),
                     os.path.join(pf_x86, "Opera", "launcher.exe")]

    which_path = shutil.which("launcher") or shutil.which("opera") or shutil.which("operagx")
    if which_path:
        return which_path

    for p in possible:
        if p and os.path.exists(p):
            return p

    # Search base folders recursively
    def search_base(base):
        if not base or not os.path.isdir(base):
            return None
        for root, dirs, files in os.walk(base):
            if "launcher.exe" in files and "opera" in root.lower():
                return os.path.join(root, "launcher.exe")
        return None

    for base in [local, pf, pf_x86]:
        candidate = search_base(base)
        if candidate:
            return candidate

    # Registry fallback
    if winreg and os.name == "nt":
        for reg_key in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]:
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    key = winreg.OpenKey(hive, reg_key)
                    i = 0
                    while True:
                        try:
                            sk = winreg.EnumKey(key, i)
                        except OSError:
                            break
                        try:
                            appk = winreg.OpenKey(key, sk)
                            name = winreg.QueryValueEx(appk, "DisplayName")[0]
                            if "opera" in name.lower():
                                val = winreg.QueryValueEx(appk, "DisplayIcon")[0]
                                if val:
                                    candidate = val.split(",")[0]
                                    if os.path.exists(candidate):
                                        return candidate
                        except Exception:
                            pass
                        i += 1
                except Exception:
                    pass

    return None


# ── Actions ───────────────────────────────────────────────────────────────

def open_browser(url: str, use_opera: bool = False) -> str:
    """Open the default browser or Opera GX with an optional URL."""
    try:
        if use_opera and os.name == "nt":
            exe = find_opera_exe()
            if exe:
                target = _normalize_url(url) if url else ""
                subprocess.Popen([exe, target] if target else [exe])
                return f"Opened Opera with {url}" if url else "Opened Opera GX"
        if url:
            webbrowser.open_new_tab(_normalize_url(url))
            return f"Opened browser to {url}"
        webbrowser.open_new_tab("about:blank")
        return "Opened browser (blank tab)"
    except Exception:
        webbrowser.open("https://www.google.com")
        return "Opened browser (default page)"
    except Exception as e:
        return f"Failed to open browser: {e}"

def open_explorer(path: str) -> str:
    """Open Windows File Explorer at the given path."""
    try:
        p = Path(path)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        if not p.exists():
            return f"Path does not exist: {p}"
        os.startfile(str(p)) if sys.platform.startswith("win") else subprocess.Popen(["xdg-open", str(p)])
        return f"Opened explorer at {p}"
    except Exception as e:
        return f"Failed to open explorer: {e}"

def run_script(path: str) -> str:
    """Run a Python script from the project directory."""
    try:
        if not is_allowed_script(path):
            return "Script path not allowed."
        p = (PROJECT_ROOT / path).resolve()
        if not p.exists():
            return f"Script not found: {p}"
        subprocess.Popen([sys.executable, str(p)])
        return f"Launched script: {p.name}"
    except Exception as e:
        return f"Failed to run script: {e}"

def restart_app() -> str:
    """Restart the AIDO application."""
    try:
        os.execv(sys.executable, [sys.executable, str(PROJECT_ROOT / "ui.py")])
    except Exception as e:
        return f"Failed to restart app: {e}"


# ── Action registry ───────────────────────────────────────────────────────

ALLOWED_ACTIONS = {
    "open_browser": open_browser,
    "open_browser_opera": lambda arg: open_browser(arg, use_opera=True),
    "open_explorer": open_explorer,
    "run_script": run_script,
    "restart_app": restart_app,
}

def perform_action(action: str, arg: str, username: str, password: str) -> str:
    """Execute a PC action after authentication."""
    if not auth.is_home_machine():
        return "Action not allowed on this machine."
    if not auth.verify_login(username, password):
        return "Authentication failed."
    fn = ALLOWED_ACTIONS.get(action)
    if not fn:
        return f"Unknown action: {action}"
    return fn(arg) if arg is not None else fn("")
