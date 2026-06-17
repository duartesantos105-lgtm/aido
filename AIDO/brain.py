"""AIDO Brain — Core AI logic. Connects to Groq API for chat, manages memory and self-evolution."""
import os
import re
from pathlib import Path
from threading import Thread
from groq import Groq
from dotenv import load_dotenv
from mem0 import MemoryClient
import tools

BRAIN_DIR = Path(__file__).parent
load_dotenv(BRAIN_DIR / ".env")
load_dotenv(BRAIN_DIR.parent / ".env")

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

    def get_memory_context(self, query):
        """Retrieve relevant memories for the given query."""
        try:
            results = self.memory.search(query=query, user_id="duarte_001", limit=5)
            if results:
                return "\n".join(f"- {m['memory']}" for m in results if "memory" in m)
        except Exception:
            pass
        return ""

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

        def thread_func():
            """Run Groq API call in a separate thread to keep UI responsive."""
            try:
                memory_context = self.get_memory_context(command)
                search_context = self.check_for_search(command)
                file_context = self.check_for_file_read(command)

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
                    parts.extend(["\n\n### Relevant Context from Memory\n", memory_context])
                if search_context:
                    parts.extend(["\n\n### Tool Results\n", search_context, "\nUse the above tool results accurately."])
                if file_context:
                    parts.extend(["\n\n### File Contents Retrieved\n", file_context,
                                  "\nAnalyze this code. If you see a flaw, you have permission to rewrite it using your [CODE_UPDATE:] tag."])

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
                for chunk in stream:
                    token = chunk.choices[0].delta.content or ""
                    if token:
                        buffer += token
                        if "[SELF_CORRECT:" not in buffer and "[CODE_UPDATE:" not in buffer:
                            on_token_callback(token)

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
                clean_text = re.sub(r"\[(SELF_CORRECT|CODE_UPDATE):.*?\]", "", buffer, flags=re.DOTALL).strip()
                if "[CODE_UPDATE:" in clean_text:
                    clean_text = clean_text.split("[CODE_UPDATE:")[0].strip()

                self.conversation_history.append({"role": "user", "content": command})
                self.conversation_history.append({"role": "assistant", "content": clean_text})

                try:
                    self.memory.add(
                        messages=[{"role": "user", "content": command}, {"role": "assistant", "content": clean_text}],
                        user_id="duarte_001",
                    )
                except Exception:
                    pass

                on_complete_callback()

            except Exception as e:
                on_token_callback(f"Error: {str(e)}")
                on_complete_callback()

        Thread(target=thread_func, daemon=True).start()
