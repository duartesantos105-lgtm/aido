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
