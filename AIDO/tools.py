import os
import requests

def search_web(query):
    """Performs a fast Google search and returns the top 3 results."""
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return "Error: Google API keys not configured in .env file."

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 3  # Only grab top 3 to keep it fast and light
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("items", [])
        
        if not results:
            return "No web results found."

        context = "### Web Search Results:\n"
        for r in results:
            context += f"- {r.get('title')}: {r.get('snippet')}\n"
        return context
        
    except Exception as e:
        return f"Web search failed: {str(e)}"


# ==========================================
# NEW: Give AIDO eyes to read her own code
# ==========================================
def read_local_file(filename):
    """Reads a local file and returns its contents. Used for self-improvement."""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    # Security: Only allow her to read specific python files
    allowed_files = ["brain.py", "tools.py", "ui.py", "auth.py", "aido_system_prompt.txt", "self_evolution.txt"]
    
    if filename not in allowed_files:
        return f"Error: Access denied. You are not allowed to read '{filename}'."
        
    if not os.path.exists(filepath):
        return f"Error: File '{filename}' does not exist."
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"### Contents of {filename}:\n```python\n{content}\n```"
    except Exception as e:
        return f"Error reading file: {str(e)}"