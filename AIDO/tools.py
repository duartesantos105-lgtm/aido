"""Utility tools for AIDO: web search and file reading."""
import os
import requests

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
