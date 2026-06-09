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


def is_allowed_script(path: str) -> bool:
    try:
        p = (PROJECT_ROOT / path).resolve()
        return PROJECT_ROOT in p.parents or p == PROJECT_ROOT
    except Exception:
        return False


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        return "https://" + url
    return url


def find_opera_exe() -> str | None:
    # Explicit override via environment variable
    env_path = os.environ.get("OPERA_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # Common install locations for Opera / Opera GX on Windows
    possible = []
    local = os.environ.get("LOCALAPPDATA")
    programfiles = os.environ.get("PROGRAMFILES")
    programfiles_x86 = os.environ.get("PROGRAMFILES(X86)")
    if local:
        possible += [os.path.join(local, "Programs", "Opera GX", "launcher.exe"),
                     os.path.join(local, "Programs", "Opera", "launcher.exe")]
    if programfiles:
        possible += [os.path.join(programfiles, "Opera GX", "launcher.exe"),
                     os.path.join(programfiles, "Opera", "launcher.exe")]
    if programfiles_x86:
        possible += [os.path.join(programfiles_x86, "Opera GX", "launcher.exe"),
                     os.path.join(programfiles_x86, "Opera", "launcher.exe")]

    # also try system path
    which_path = shutil.which("launcher") or shutil.which("opera") or shutil.which("operagx")
    if which_path:
        return which_path

    for p in possible:
        if p and os.path.exists(p):
            return p

    # Search possible base folders for Opera launcher if not found directly
    def search_base(base_path):
        if not base_path or not os.path.isdir(base_path):
            return None
        try:
            for root, dirs, files in os.walk(base_path):
                if "launcher.exe" in files and "opera" in root.lower():
                    return os.path.join(root, "launcher.exe")
        except Exception:
            return None
        return None

    for base in [local, programfiles, programfiles_x86]:
        candidate = search_base(base)
        if candidate:
            return candidate

    # Try Windows registry (if available) for installed Opera products
    if winreg and os.name == 'nt':
        def check_uninstall_key(root, subkey):
            try:
                key = winreg.OpenKey(root, subkey)
            except Exception:
                return None

            try:
                i = 0
                while True:
                    try:
                        sk = winreg.EnumKey(key, i)
                    except OSError:
                        break
                    try:
                        appk = winreg.OpenKey(key, sk)
                    except Exception:
                        i += 1
                        continue
                    try:
                        name = winreg.QueryValueEx(appk, 'DisplayName')[0]
                    except Exception:
                        name = ''
                    if 'opera' in name.lower():
                        try:
                            val = winreg.QueryValueEx(appk, 'DisplayIcon')[0]
                            if val:
                                candidate = val.split(',')[0]
                                if os.path.exists(candidate):
                                    return candidate
                        except Exception:
                            pass
                    i += 1
            finally:
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass
            return None

        regs = [r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
                r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"]
        for reg in regs:
            for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                candidate = check_uninstall_key(root, reg)
                if candidate:
                    return candidate

    return None


def open_browser(url: str, use_opera: bool = False) -> str:
    try:
        if use_opera and os.name == 'nt':
            exe = find_opera_exe()
            if exe:
                if url:
                    url = _normalize_url(url)
                    subprocess.Popen([exe, url])
                    return f"Opened Opera with {url}"
                subprocess.Popen([exe])
                return "Opened Opera GX"
        if url:
            url = _normalize_url(url)
            webbrowser.open_new_tab(url)
            return f"Opened browser to {url}"
        try:
            webbrowser.open_new_tab("about:blank")
            return "Opened browser to a blank tab"
        except Exception:
            webbrowser.open("https://www.google.com")
            return "Opened browser (default page)"
    except Exception as e:
        return f"Failed to open browser: {e}"


def open_explorer(path: str) -> str:
    try:
        p = Path(path)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        if not p.exists():
            return f"Path does not exist: {p}"
        if sys.platform.startswith("win"):
            os.startfile(str(p))
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return f"Opened explorer at {p}"
    except Exception as e:
        return f"Failed to open explorer: {e}"


def run_script(path: str) -> str:
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
    try:
        # Relaunch ui.py using execv
        python = sys.executable
        os.execv(python, [python, str(PROJECT_ROOT / "ui.py")])
    except Exception as e:
        return f"Failed to restart app: {e}"


ALLOWED_ACTIONS = {
    "open_browser": open_browser,
    "open_browser_opera": lambda arg: open_browser(arg, use_opera=True),
    "open_explorer": open_explorer,
    "run_script": run_script,
    "restart_app": restart_app,
}


def perform_action(action: str, arg: str, username: str, password: str) -> str:
    # Security: only allow on home machine
    if not auth.is_home_machine():
        return "Action not allowed on this machine."
    if not auth.verify_login(username, password):
        return "Authentication failed."
    fn = ALLOWED_ACTIONS.get(action)
    if not fn:
        return f"Unknown action: {action}"
    return fn(arg) if arg is not None else fn("")
