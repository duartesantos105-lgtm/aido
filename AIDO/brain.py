import os
import re
from threading import Thread
from groq import Groq
from dotenv import load_dotenv
from mem0 import MemoryClient
import tools

load_dotenv()

SELF_EVOLUTION_FILE = "self_evolution.txt"

class AIDOBrain:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.mem0_api_key = os.getenv("MEM0_API_KEY")

        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        if not self.mem0_api_key:
            raise ValueError("MEM0_API_KEY not found in .env")

        self.client = Groq(api_key=self.groq_api_key)
        self.model = "llama-3.3-70b-versatile"

        self.system_prompt = ""
        self.personality_context = ""
        self.response_patterns = ""
        self.evolution_context = ""
        self.memory = None
        self.conversation_history = []
        self.max_history_turns = 10

        self.search_triggers = [
            "who is", "what is", "latest", "news", "current",
            "weather", "price of", "search for", "look up", "google"
        ]

    def load_config(self):
        try:
            with open('aido_system_prompt.txt', 'r', encoding='utf-8') as f:
                content = f.read()

            sections = {
                "system_prompt": ("## 1. SYSTEM PROMPT\n\n", "\n\n## 2."),
                "personality": ("## 2. PERSONALITY PROFILE\n\n", "\n\n## 3."),
                "response_patterns": ("## 5. RESPONSE PATTERNS\n\n", "\n\n## 6."),
                "evolution": ("## 6. SELF-EVOLUTION PROTOCOL\n\n", "\n\n## 7."),
                "code_mod": ("## 7. CODE SELF-MODIFICATION\n\n", None)
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

            if os.path.exists(SELF_EVOLUTION_FILE):
                with open(SELF_EVOLUTION_FILE, 'r', encoding='utf-8') as f:
                    self.evolution_context = f.read().strip()

        except FileNotFoundError:
            raise ValueError("aido_system_prompt.txt not found")

    def init_memory(self):
        self.memory = MemoryClient(api_key=self.mem0_api_key)

    def init_model(self):
        pass

    def get_memory_context(self, query):
        try:
            results = self.memory.search(query=query, user_id="duarte_001", limit=5)
            if results:
                return "\n".join(["- " + m['memory'] for m in results if 'memory' in m])
        except Exception:
            pass
        return ""

    def check_for_search(self, query):
        if any(trigger in query.lower() for trigger in self.search_triggers):
            return tools.search_web(query)
        return None

    def check_for_file_read(self, query):
        query_lower = query.lower()
        if "read " in query_lower and (".py" in query_lower or ".txt" in query_lower):
            for file in ["brain.py", "tools.py", "ui.py", "auth.py", "aido_system_prompt.txt", "self_evolution.txt"]:
                if file in query_lower:
                    return tools.read_local_file(file)
        return None

    def stream_response(self, command, on_token_callback, on_complete_callback, on_code_update_callback, on_action_request=None):
        
        lower_cmd = command.lower().strip()
        # Detect simple app-launch intents and request UI confirmation or direct execution
        try:
            if on_action_request:
                if re.search(r"\b(abre|abrir|open)\b.*\b(opera gx|opera|operagx)\b", lower_cmd):
                    on_action_request('open_browser_opera', '')
                    return
                m = re.search(r"\b(abre|abrir|open)\b.*\b(chrome|firefox|edge|brave|safari|yandex)\b", lower_cmd)
                if m:
                    browser_name = m.group(2)
                    on_action_request('confirm_browser', browser_name)
                    return
                if re.search(r"\b(abre|abrir|open)\b.*\b(browser|navegador)\b", lower_cmd):
                    on_action_request('open_browser', '')
                    return
                if re.search(r"\b(abre|abrir|open)\b.*\b(explorer|file explorer|explorador)\b", lower_cmd):
                    on_action_request('open_explorer', '')
                    return
        except Exception:
            pass
        if lower_cmd.startswith("rule:"):
            rule_text = command[5:].strip()
            with open(SELF_EVOLUTION_FILE, "a", encoding="utf-8") as f:
                f.write(f"- {rule_text}\n")
            self.evolution_context += f"\n- {rule_text}"
            on_token_callback(f"Behavioral rule acknowledged: '{rule_text}'.")
            on_complete_callback()
            return

        def thread_func():
            try:
                memory_context = self.get_memory_context(command)
                search_context = self.check_for_search(command)
                file_context = self.check_for_file_read(command)

                parts = [self.system_prompt, "\n\n### Personality Guidelines\n", self.personality_context]
                
                if hasattr(self, 'evolution_protocol'):
                    parts.extend(["\n\n### Self-Evolution Protocol\n", self.evolution_protocol])
                if hasattr(self, 'code_mod_protocol'):
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
                    parts.extend(["\n\n### File Contents Retrieved\n", file_context, "\nAnalyze this code. If you see a flaw, you have permission to rewrite it using your [CODE_UPDATE:] tag."])

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

                if "[SELF_CORRECT:" in buffer:
                    start_idx = buffer.find("[SELF_CORRECT:") + len("[SELF_CORRECT:")
                    end_idx = buffer.find("]", start_idx)
                    if end_idx != -1:
                        new_rule = buffer[start_idx:end_idx].strip()
                        with open(SELF_EVOLUTION_FILE, "a", encoding="utf-8") as f:
                            f.write(f"- {new_rule}\n")
                        self.evolution_context += f"\n- {new_rule}"
                        print(f"\n[🧬 SELF-EVOLVED]: {new_rule}")

                # ==========================================
                # BULLETPROOF CODE EXTRACTOR
                # ==========================================
                if "[CODE_UPDATE:" in buffer:
                    # Extract everything between [CODE_UPDATE: and the final ]
                    match = re.search(r"\[CODE_UPDATE:\s*(.*?)\]", buffer, re.DOTALL)
                    
                    if match:
                        raw_update = match.group(1).strip()
                        
                        # Find the filename (e.g., brain.py)
                        file_match = re.search(r"([\w\-]+\.py)", raw_update)
                        
                        # Find the code block (forgiving of spaces/missing 'python' tag)
                        code_match = re.search(r"```[\w]*\s*\n?(.*?)\n?```", raw_update, re.DOTALL)
                        
                        if file_match and code_match:
                            filename = file_match.group(1)
                            new_code = code_match.group(1).strip()
                            print(f"\n[⚙️ CODE UPDATE PROPOSED]: {filename}")
                            # Send to UI
                            on_code_update_callback(filename, new_code)
                        else:
                            print("\n[⚠️ CODE UPDATE FAILED]: AIDO formatted the code block incorrectly.")
                    else:
                        print("\n[⚠️ CODE UPDATE FAILED]: Missing closing bracket ].")

                if not buffer.strip():
                    buffer = "Understood."
                    on_token_callback(buffer)

                # Strip ALL system tags from history
                clean_text = re.sub(r"\[(SELF_CORRECT|CODE_UPDATE):.*?\]", "", buffer, flags=re.DOTALL).strip()
                # Fallback just in case the regex misses a badly formatted tag
                if "[CODE_UPDATE:" in clean_text:
                    clean_text = clean_text.split("[CODE_UPDATE:")[0].strip()
                
                self.conversation_history.append({"role": "user", "content": command})
                self.conversation_history.append({"role": "assistant", "content": clean_text})

                try:
                    self.memory.add(
                        messages=[{"role": "user", "content": command}, {"role": "assistant", "content": clean_text}],
                        user_id="duarte_001"
                    )
                except Exception:
                    pass

                on_complete_callback()

            except Exception as e:
                print(f"\n[BRAIN ERROR]: {e}")
                on_token_callback(f"Error: {str(e)}")
                on_complete_callback()

        Thread(target=thread_func, daemon=True).start()