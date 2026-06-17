"""AIDO Brain — Core AI logic. Connects to Groq API for chat, manages memory and self-evolution."""
import os
import re
import json
from pathlib import Path
from threading import Thread
from groq import Groq
from dotenv import load_dotenv
from mem0 import MemoryClient
import tools

BRAIN_DIR = Path(__file__).parent
load_dotenv(BRAIN_DIR.parent / ".env")

FACTS_FILE = BRAIN_DIR / "user_facts.json"

class AIDOBrain:
    """Handles AI chat, memory, web search, and code self-modification."""

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.mem0_api_key = os.getenv("MEM0_API_KEY")

        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        if not self.mem0_api_key:
            raise ValueError("MEM0_API_KEY not found in .env")

        self.client = Groq(api_key=self.groq_api_key)
        self.model = "llama-3.3-70b-versatile"

        # Config sections loaded from aido_system_prompt.txt
        self.system_prompt = ""
        self.personality_context = ""
        self.response_patterns = ""
        self.evolution_context = ""

        self.memory = None
        self.conversation_history = []
        self.max_history_turns = 1000

        self.search_triggers = [
            "who is", "what is", "latest", "news", "current",
            "weather", "price of", "search for", "look up", "google"
        ]

    # ── Configuration ─────────────────────────────────────────────────────

    def load_config(self):
        """Parse aido_system_prompt.txt into prompt sections."""
        try:
            with open(BRAIN_DIR / "aido_system_prompt.txt", "r", encoding="utf-8") as f:
                content = f.read()

            sections = {
                "system_prompt": ("## 1. SYSTEM PROMPT\n\n", "\n\n## 2."),
                "personality": ("## 2. PERSONALITY PROFILE\n\n", "\n\n## 3."),
                "response_patterns": ("## 5. RESPONSE PATTERNS\n\n", "\n\n## 6."),
                "evolution": ("## 6. SELF-EVOLUTION PROTOCOL\n\n", "\n\n## 7."),
                "code_mod": ("## 7. CODE SELF-MODIFICATION\n\n", None),
            }

            for key, (start, end) in sections.items():
                s_idx = content.find(start)
                e_idx = content.find(end) if end else len(content)
                if s_idx != -1 and e_idx != -1:
                    value = content[s_idx + len(start):e_idx].strip()
                    if key == "personality":
                        self.personality_context = value
                    elif key == "evolution":
                        self.evolution_protocol = value
                    elif key == "code_mod":
                        self.code_mod_protocol = value
                    else:
                        setattr(self, key, value)

            if not self.system_prompt:
                self.system_prompt = "You are AIDO, an advanced AI assistant."

            evolution_path = BRAIN_DIR / "self_evolution.txt"
            if evolution_path.exists():
                with open(evolution_path, "r", encoding="utf-8") as f:
                    self.evolution_context = f.read().strip()

        except FileNotFoundError:
            raise ValueError("aido_system_prompt.txt not found")

    # ── Memory ────────────────────────────────────────────────────────────

    def init_memory(self):
        """Initialise mem0 memory client."""
        self.memory = MemoryClient(api_key=self.mem0_api_key)

    def init_model(self):
        """Placeholder — model initialisation not needed for Groq API."""

    # ── Local facts (JSON fallback) ──────────────────────────────────

    def _load_facts(self):
        """Load local facts from JSON file."""
        if FACTS_FILE.exists():
            try:
                return json.loads(FACTS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_facts(self, facts):
        """Save local facts to JSON file."""
        FACTS_FILE.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_fact(self, key, value):
        """Store a local fact (e.g. name, preferences)."""
        facts = self._load_facts()
        facts[key] = value
        self._save_facts(facts)
        print(f"[facts] saved: {key} = {value}")

    def get_facts_context(self):
        """Return all local facts as formatted string."""
        facts = self._load_facts()
        if not facts:
            return ""
        return "\n".join(f"- {k}: {v}" for k, v in facts.items())

    def get_memory_context(self, query):
        """Retrieve relevant memories from mem0 and local facts."""
        local_facts = self.get_facts_context()

        queries = [query, "about me", "user information", "facts about user", "name",
                   "preferences", "history", "personal details"]
        facts = self._load_facts()
        if "nome" in facts:
            queries.append(facts["nome"])

        seen = set()
        memories = []
        for q in queries:
            try:
                result = self.memory.search(query=q, filters={"user_id": "duarte_001"}, limit=10)
                if result and isinstance(result, dict):
                    for m in result.get("results", []):
                        mem = m.get("memory", "")
                        if mem and mem not in seen:
                            seen.add(mem)
                            memories.append(mem)
            except Exception as e:
                print(f"[mem0] search error for '{q}': {e}")

        result = ""
        if local_facts:
            result += "### Local Facts About You\n" + local_facts + "\n\n"
        if memories:
            result += "### Memories from Cloud\n" + "\n".join(f"- {m}" for m in memories)
        return result

    def save_memory(self, text):
        """Save important facts to long-term memory explicitly."""
        try:
            self.memory.add(messages=[
                {"role": "system", "content": f"Save this information: {text}"}
            ], user_id="duarte_001", infer=True)
            return True
        except Exception as e:
            print(f"[mem0] save error: {e}")
            return False

    # ── Tool detection ────────────────────────────────────────────────────

    def check_for_search(self, query):
        """Trigger web search if query matches keywords."""
        if any(trigger in query.lower() for trigger in self.search_triggers):
            return tools.search_web(query)
        return None

    def check_for_file_read(self, query):
        """Let AIDO read its own source files for self-improvement."""
        q = query.lower()
        if "read " in q and (".py" in q or ".txt" in q):
            for name in ["brain.py", "tools.py", "ui.py", "auth.py", "aido_system_prompt.txt", "self_evolution.txt"]:
                if name in q:
                    return tools.read_local_file(name)
        return None

    def check_for_system_tools(self, query):
        """Detect system info, notes, clipboard, calculator requests."""
        q = query.lower()

        # System info
        if any(w in q for w in ["system info", "system information", "specs", "especificações"]):
            return tools.system_info()
        if any(w in q for w in ["cpu usage", "cpu %", "cpu percent", "uso do cpu", "uso cpu"]):
            return tools.cpu_usage()
        if any(w in q for w in ["ram usage", "ram %", "ram percent", "uso de ram", "uso ram", "memória"]):
            return tools.ram_usage()

        # Notes
        if q.startswith("save note") or q.startswith("guardar nota") or q.startswith("note:"):
            parts = q.split(":", 1) if ":" in q else q.split(None, 2)
            if len(parts) >= 3:
                title = parts[2].split()[0] if len(parts) == 3 else parts[1].strip()
                content = query[query.index(title) + len(title):].strip()
                return tools.note_save(title, content)
        if "read note" in q or "ler nota" in q or "show note" in q:
            for word in q.split():
                if word not in ("read", "note", "ler", "nota", "show", "my", "a", "o", "a"):
                    return tools.note_read(word.capitalize())
            return tools.note_list()
        if any(w in q for w in ["list notes", "listar notas", "my notes", "minhas notas"]):
            return tools.note_list()
        if "delete note" in q or "apagar nota" in q or "remover nota" in q:
            for word in q.split():
                if word not in ("delete", "note", "apagar", "nota", "remover", "the"):
                    return tools.note_delete(word.capitalize())

        # Clipboard
        if any(w in q for w in ["clipboard read", "read clipboard", "ler clipboard", "ler area de transferencia", "o que tem no clipboard", "what is on clipboard", "clipboard content"]):
            return tools.clipboard_get()
        if any(w in q for w in ["copy to clipboard", "copiar para clipboard", "clipboard write", "clipboard set", "copiar"]):
            match = re.search(r'(?:clipboard|copy|copiar)\s*(?:to|for|para)?\s*(?:clipboard)?\s*[""](.+?)[""]', query, re.IGNORECASE)
            if match:
                return tools.clipboard_set(match.group(1))

        # Calculator
        calc_match = re.search(r'(?:calculate|calc|calcula|calcular|quanto e|quanto é)\s+(.+?)$', q)
        if calc_match:
            return tools.calculate(calc_match.group(1))

        # App launcher
        if any(w in q for w in ["abrir app", "open app", "launch app", "abrir programa", "open program", "iniciar"]):
            for word in ["abrir", "open", "launch", "app", "programa", "program", "iniciar"]:
                q = q.replace(word, "")
            app_name = q.strip()
            if app_name:
                return tools.launch_app(app_name)
        app_match = re.search(r'(?:abre|abrir|open|launch)\s+(?:o\s+)?(?:app|programa|program)?\s*[""]?(.+?)[""]?$', q)
        if app_match:
            return tools.launch_app(app_match.group(1).strip())

        # List available apps
        if any(w in q for w in ["list apps", "listar apps", "available apps", "apps disponiveis", "que apps"]):
            return tools.list_apps()

        # File management
        if any(w in q for w in ["list dir", "listar pasta", "list folder", "mostrar pasta", "whats in", "o que tem em", "mostrar diretorio", "list directory"]):
            path_match = re.search(r'(?:pasta|folder|diretorio|directory|em|in)\s+[""]?(.+?)[""]?(?:\s|$)', q)
            if path_match:
                return tools.list_directory(path_match.group(1).strip())
            return tools.list_directory(".")

        if "create folder" in q or "criar pasta" in q or "create directory" in q or "nova pasta" in q:
            name_match = re.search(r'(?:folder|pasta|directory|chamada|named)\s+[""]?(.+?)[""]?(?:\s|$)', q)
            path_match = re.search(r'(?:em|in|at)\s+[""]?(.+?)[""]?(?:\s|$)', q)
            name = name_match.group(1) if name_match else "new_folder"
            path = path_match.group(1) if path_match else "."
            return tools.create_folder(path, name)

        if "rename" in q or "renomear" in q:
            match = re.search(r'(?:rename|renomear)\s+[""]?(.+?)[""]?\s+(?:to|para)\s+[""]?(.+?)[""]?$', q)
            if match:
                return tools.rename_item(match.group(1).strip(), match.group(2).strip())

        if any(w in q for w in ["move file", "mover", "move item", "move folder"]):
            match = re.search(r'(?:move|mover)\s+[""]?(.+?)[""]?\s+(?:to|para)\s+[""]?(.+?)[""]?$', q)
            if match:
                return tools.move_item(match.group(1).strip(), match.group(2).strip())

        if "delete file" in q or "apagar" in q or "delete item" in q:
            match = re.search(r'(?:delete|apagar)\s+(?:file|ficheiro|item|folder|pasta)?\s*[""]?(.+?)[""]?$', q)
            if match:
                path = match.group(1).strip()
                if path and path not in ("file", "ficheiro", "item", "folder", "pasta"):
                    return tools.delete_item(path)

        return None

    # ── Streaming response ────────────────────────────────────────────────

    def stream_response(self, command, on_token_callback, on_complete_callback,
                        on_code_update_callback, on_action_request=None):
        """Send command to Groq, stream tokens to UI, handle system tags."""
        lower_cmd = command.lower().strip()

        # ── Local command detection ───────────────────────────────────
        if on_action_request:
            if re.search(r"\b(abre|abrir|open)\b.*\b(opera gx|opera|operagx)\b", lower_cmd):
                on_action_request("open_browser_opera", "")
                return
            m = re.search(r"\b(abre|abrir|open)\b.*\b(chrome|firefox|edge|brave|safari|yandex)\b", lower_cmd)
            if m:
                on_action_request("confirm_browser", m.group(2))
                return
            if re.search(r"\b(abre|abrir|open)\b.*\b(browser|navegador)\b", lower_cmd):
                on_action_request("open_browser", "")
                return
            if re.search(r"\b(abre|abrir|open)\b.*\b(explorer|file explorer|explorador)\b", lower_cmd):
                on_action_request("open_explorer", "")
                return

        # ── Manual rule addition ──────────────────────────────────────
        if lower_cmd.startswith("rule:"):
            rule_text = command[5:].strip()
            evolution_path = BRAIN_DIR / "self_evolution.txt"
            with open(evolution_path, "a", encoding="utf-8") as f:
                f.write(f"- {rule_text}\n")
            self.evolution_context += f"\n- {rule_text}"
            on_token_callback(f"Behavioral rule acknowledged: '{rule_text}'.")
            on_complete_callback()
            return

        # ── Auto-save user facts ─────────────────────────────────────
        name_match = re.search(r"(?:o\s*)?meu\s*nome\s*(?:e|é)\s*(\w+)", lower_cmd)
        if not name_match:
            name_match = re.search(r"(?:chamo-me|chamou?\s*-\s*me|my name is|i'?m? called)\s+(\w+)", lower_cmd, re.IGNORECASE)
        if name_match:
            name = name_match.group(1)
            self.save_memory(f"O nome do utilizador é {name}")
            self.add_fact("nome", name)
            print(f"[facts] auto-saved user name: {name}")

        def thread_func():
            """Run Groq API call in a separate thread to keep UI responsive."""
            try:
                memory_context = self.get_memory_context(command)
                search_context = self.check_for_search(command)
                file_context = self.check_for_file_read(command)
                tool_context = self.check_for_system_tools(command)

                # Build system message from all context sections
                parts = [self.system_prompt, "\n\n### Personality Guidelines\n", self.personality_context]
                if hasattr(self, "evolution_protocol"):
                    parts.extend(["\n\n### Self-Evolution Protocol\n", self.evolution_protocol])
                if hasattr(self, "code_mod_protocol"):
                    parts.extend(["\n\n### Code Modification Access\n", self.code_mod_protocol])
                if self.evolution_context:
                    parts.extend(["\n\n### Active Hardcoded Rules\n", self.evolution_context])
                if self.response_patterns:
                    parts.extend(["\n\n### Response Style Guidelines\n", self.response_patterns])
                if memory_context:
                    parts.extend(["\n\n### Relevant Context from Memory\n", memory_context,
                                  "\nUse the above memories in your response. If the user asks about something already in memory, respond naturally as if you remember."])
                if search_context:
                    parts.extend(["\n\n### Tool Results\n", search_context, "\nUse the above tool results accurately."])
                if file_context:
                    parts.extend(["\n\n### File Contents Retrieved\n", file_context,
                                  "\nAnalyze this code. If you see a flaw, you have permission to rewrite it using your [CODE_UPDATE:] tag."])
                if tool_context:
                    parts.extend(["\n\n### Tool Result\n", tool_context,
                                  "\nUse the above information to answer the user."])

                parts.append("\n\n### Current Session\nMaintain character. Never output 'AIDO:'.")
                system_message = "".join(parts)

                messages = [{"role": "system", "content": system_message}]
                for turn in self.conversation_history[-(self.max_history_turns * 2):]:
                    messages.append({"role": turn["role"], "content": turn["content"]})
                messages.append({"role": "user", "content": command})

                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.7,
                    stream=True,
                )

                buffer = ""
                pending = ""

                for chunk in stream:
                    token = chunk.choices[0].delta.content or ""
                    if token:
                        buffer += token
                        for ch in token:
                            if ch == "[":
                                pending = "["
                            elif pending:
                                pending += ch
                                if ch == "]":
                                    is_known = any(
                                        pending.startswith(t)
                                        for t in ("[SELF_CORRECT:", "[CODE_UPDATE:", "[SAVE_MEMORY:")
                                    )
                                    if not is_known:
                                        on_token_callback(pending)
                                    pending = ""
                            else:
                                on_token_callback(ch)
                # ── Handle SELF_CORRECT tag ──────────────────────────
                if "[SELF_CORRECT:" in buffer:
                    start = buffer.find("[SELF_CORRECT:") + len("[SELF_CORRECT:")
                    end = buffer.find("]", start)
                    if end != -1:
                        new_rule = buffer[start:end].strip()
                        evolution_path = BRAIN_DIR / "self_evolution.txt"
                        with open(evolution_path, "a", encoding="utf-8") as f:
                            f.write(f"- {new_rule}\n")
                        self.evolution_context += f"\n- {new_rule}"

                # ── Handle SAVE_MEMORY tag ──────────────────────────
                if "[SAVE_MEMORY:" in buffer:
                    start = buffer.find("[SAVE_MEMORY:") + len("[SAVE_MEMORY:")
                    end = buffer.find("]", start)
                    if end != -1:
                        fact = buffer[start:end].strip()
                        self.save_memory(fact)
                        print(f"[mem0] saved fact: {fact}")

                # ── Handle CODE_UPDATE tag ───────────────────────────
                if "[CODE_UPDATE:" in buffer:
                    match = re.search(r"\[CODE_UPDATE:\s*(.*?)\]", buffer, re.DOTALL)
                    if match:
                        raw = match.group(1).strip()
                        file_match = re.search(r"([\w\-]+\.py)", raw)
                        code_match = re.search(r"```[\w]*\s*\n?(.*?)\n?```", raw, re.DOTALL)
                        if file_match and code_match:
                            on_code_update_callback(file_match.group(1), code_match.group(1).strip())

                if not buffer.strip():
                    buffer = "Understood."
                    on_token_callback(buffer)

                # Strip system tags before storing in history
                clean_text = re.sub(r"\[(SELF_CORRECT|CODE_UPDATE|SAVE_MEMORY):.*?\]", "", buffer, flags=re.DOTALL).strip()
                if "[CODE_UPDATE:" in clean_text:
                    clean_text = clean_text.split("[CODE_UPDATE:")[0].strip()

                self.conversation_history.append({"role": "user", "content": command})
                self.conversation_history.append({"role": "assistant", "content": clean_text})

                try:
                    self.memory.add(
                        messages=[
                            {"role": "user", "content": command},
                            {"role": "assistant", "content": clean_text}
                        ],
                        user_id="duarte_001",
                        infer=True,
                    )
                except Exception as e:
                    print(f"[mem0] store error: {e}")

                on_complete_callback()

            except Exception as e:
                on_token_callback(f"Error: {str(e)}")
                on_complete_callback()

        Thread(target=thread_func, daemon=True).start()
