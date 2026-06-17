"""Utility tools for AIDO: web search, system info, notes, calculator, clipboard."""
import os
import re
import json
import math
import subprocess
import platform
import shutil
import datetime
import requests
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

TOOLS_DIR = Path(__file__).parent
NOTES_FILE = TOOLS_DIR / "notes.json"

# ── Web Search ──────────────────────────────────────────────────────────────

def search_web(query):
    """Search Google via Custom Search API. Returns top 3 results as text."""
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        return "Error: Google API keys not configured in .env file."

    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query, "num": 3}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("items", [])
        if not results:
            return "No web results found."
        return "### Web Search Results:\n" + "\n".join(
            f"- {r.get('title')}: {r.get('snippet')}" for r in results
        )
    except Exception as e:
        return f"Web search failed: {str(e)}"


# ── System Information ──────────────────────────────────────────────────────

def system_info():
    """Get system information (OS, CPU, RAM, disk)."""
    try:
        total, used, free = shutil.disk_usage(TOOLS_DIR)
        info = (
            f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
            f"CPU: {os.cpu_count()} cores\n"
            f"RAM: {round(psutil.virtual_memory().total / (1024**3), 1)} GB total, "
            f"{round(psutil.virtual_memory().available / (1024**3), 1)} GB available\n"
            f"Disk: {round(total / (1024**3), 1)} GB total, "
            f"{round(free / (1024**3), 1)} GB free"
        )
        return info
    except Exception as e:
        return f"Error getting system info: {e}"

def cpu_usage():
    """Get current CPU usage percentage."""
    try:
        return f"CPU usage: {psutil.cpu_percent(interval=0.5)}%"
    except Exception as e:
        return f"Error getting CPU usage: {e}"

def ram_usage():
    """Get current RAM usage."""
    try:
        mem = psutil.virtual_memory()
        return f"RAM usage: {mem.percent}% ({round(mem.used / (1024**3), 1)} GB / {round(mem.total / (1024**3), 1)} GB)"
    except Exception as e:
        return f"Error getting RAM usage: {e}"


# ── Notes ───────────────────────────────────────────────────────────────────

def _load_notes():
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_notes(notes):
    NOTES_FILE.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")

def note_save(title, content):
    """Save a note with a title."""
    notes = _load_notes()
    notes[title] = {"content": content, "date": datetime.datetime.now().isoformat()}
    _save_notes(notes)
    return f"Note '{title}' saved."

def note_read(title):
    """Read a specific note."""
    notes = _load_notes()
    if title in notes:
        n = notes[title]
        return f"### {title}\n{n['content']}\n(saved {n['date'][:10]})"
    return f"Note '{title}' not found."

def note_list():
    """List all saved notes."""
    notes = _load_notes()
    if not notes:
        return "No notes saved."
    return "### Saved Notes:\n" + "\n".join(f"- {t} ({n['date'][:10]})" for t, n in notes.items())

def note_delete(title):
    """Delete a note."""
    notes = _load_notes()
    if title in notes:
        del notes[title]
        _save_notes(notes)
        return f"Note '{title}' deleted."
    return f"Note '{title}' not found."


# ── Clipboard ───────────────────────────────────────────────────────────────

def clipboard_get():
    """Read text from clipboard."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if text:
            return f"Clipboard contents:\n{text[:500]}"
        return "Clipboard is empty."
    except ImportError:
        return "pyperclip not installed. Run: pip install pyperclip"
    except Exception as e:
        return f"Error reading clipboard: {e}"

def clipboard_set(text):
    """Write text to clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return f"Copied to clipboard: {text[:100]}"
    except ImportError:
        return "pyperclip not installed. Run: pip install pyperclip"
    except Exception as e:
        return f"Error writing to clipboard: {e}"


# ── Calculator (safe eval) ──────────────────────────────────────────────────

SAFE_GLOBALS = {"__builtins__": {}}
SAFE_LOCALS = {
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    "int": int, "float": float, "str": str, "len": len,
    "math": math, "pi": math.pi, "e": math.e,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "sqrt": math.sqrt, "pow": pow, "log": math.log, "log10": math.log10,
    "radians": math.radians, "degrees": math.degrees,
}

def calculate(expression):
    """Evaluate a math expression safely."""
    try:
        expr = expression.strip()
        expr = re.sub(r"[^0-9+\-*/.%()\[\] ,eE]", "", expr)
        if not expr:
            return "No expression to evaluate."
        result = eval(expr, SAFE_GLOBALS, SAFE_LOCALS)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as e:
        return f"Error in calculation: {e}"


# ── File reading (self-improvement) ─────────────────────────────────────────

def read_local_file(filename):
    """Read a local source file for AIDO's self-improvement."""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    allowed = ["brain.py", "tools.py", "ui.py", "auth.py", "aido_system_prompt.txt", "self_evolution.txt"]

    if filename not in allowed:
        return f"Error: Access denied. Cannot read '{filename}'."
    if not os.path.exists(filepath):
        return f"Error: File '{filename}' not found."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return f"### Contents of {filename}:\n```python\n{content}\n```"
    except Exception as e:
        return f"Error reading file: {str(e)}"


# ── App Launcher ────────────────────────────────────────────────────────────

def launch_app(name):
    """Search for and launch an application by name."""
    name_lower = name.lower().strip()

    # Known app map for common programs
    known_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "terminal": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "control panel": "control.exe",
        "control": "control.exe",
        "registry": "regedit.exe",
        "regedit": "regedit.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "brave": "brave",
        "opera": "opera",
        "opera gx": "opera",
        "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE",
        "outlook": "OUTLOOK.EXE",
        "vs code": "code",
        "vscode": "code",
        "visual studio code": "code",
        "spotify": "spotify",
        "discord": "discord",
        "slack": "slack",
        "telegram": "telegram",
        "whatsapp": "whatsapp",
        "zoom": "zoom",
        "obs": "obs64",
        "steam": "steam",
    }

    target = known_apps.get(name_lower, name_lower)

    import shutil
    import subprocess

    # Try PATH first
    exe = shutil.which(target)
    if exe:
        subprocess.Popen([exe])
        return f"Launched {name}."

    # Try direct start command
    try:
        subprocess.Popen(["start", target], shell=True)
        return f"Launched {name}."
    except Exception:
        pass

    return f"Could not find application '{name}'. Try a different name."


def list_apps():
    """List commonly available applications."""
    common = [
        "Notepad", "Calculator", "Paint", "CMD", "PowerShell",
        "Task Manager", "Control Panel", "Registry Editor",
        "Chrome", "Firefox", "Edge", "Brave", "Opera GX",
        "Word", "Excel", "PowerPoint", "Outlook",
        "VS Code", "Spotify", "Discord", "Slack",
        "Telegram", "WhatsApp", "Zoom", "OBS", "Steam",
    ]
    return "### Available Applications\n" + "\n".join(f"- {a}" for a in common)


# ── File Management ─────────────────────────────────────────────────────────

def list_directory(path="."):
    """List files and folders in a directory."""
    try:
        p = Path(path)
        if not p.is_absolute():
            p = (TOOLS_DIR / p).resolve()
        if not p.exists():
            return f"Path does not exist: {p}"
        items = list(p.iterdir())
        folders = sorted([i for i in items if i.is_dir()])
        files = sorted([i for i in items if i.is_file()])
        result = f"### Directory: {p}\n"
        for f in folders:
            result += f"  [DIR]  {f.name}/\n"
        for f in files:
            size = f.stat().st_size
            size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            result += f"  [FILE] {f.name} ({size_str})\n"
        return result
    except Exception as e:
        return f"Error listing directory: {e}"

def create_folder(path, name):
    """Create a new folder."""
    try:
        p = Path(path) / name
        if not path.startswith("/") and not path.startswith("\\") and ":" not in path:
            p = (TOOLS_DIR / path / name).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {p}"
    except Exception as e:
        return f"Error creating folder: {e}"

def rename_item(path, new_name):
    """Rename a file or folder."""
    try:
        p = Path(path)
        if not p.is_absolute():
            p = (TOOLS_DIR / p).resolve()
        if not p.exists():
            return f"Item not found: {p}"
        new_path = p.parent / new_name
        p.rename(new_path)
        return f"Renamed to: {new_path}"
    except Exception as e:
        return f"Error renaming: {e}"

def move_item(src, dest):
    """Move a file or folder to another location."""
    try:
        s = Path(src)
        d = Path(dest)
        if not s.is_absolute():
            s = (TOOLS_DIR / s).resolve()
        if not d.is_absolute():
            d = (TOOLS_DIR / d).resolve()
        if not s.exists():
            return f"Source not found: {s}"
        if d.is_dir():
            d = d / s.name
        s.rename(d)
        return f"Moved to: {d}"
    except Exception as e:
        return f"Error moving: {e}"

def delete_item(path):
    """Move a file or folder to recycle bin."""
    try:
        import subprocess
        p = Path(path)
        if not p.is_absolute():
            p = (TOOLS_DIR / p).resolve()
        if not p.exists():
            return f"Item not found: {p}"
        # Use PowerShell to move to recycle bin
        subprocess.run(
            ["powershell", "-Command",
             f"$item = '{p}'; $shell = New-Object -ComObject Shell.Application; $shell.Namespace(0).ParseName($item).InvokeVerb('delete')"],
            capture_output=True, timeout=5
        )
        return f"Moved to recycle bin: {p.name}"
    except Exception as e:
        return f"Error deleting: {e}"
