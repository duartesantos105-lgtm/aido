"""AIDO GUI — Neural HUD v2.1: high-tech cyberpunk interface."""
import os
import sys
import time
import math
import random
import re
import tempfile
import customtkinter as ctk
from tkinter import Canvas, Text, filedialog
from threading import Thread, Event
from aido_overlay import AIDOOverlay
import pc_actions
import auth

try:
    import speech_recognition as sr
except Exception:
    sr = None
try:
    import cv2
except Exception:
    cv2 = None

# ── colours ──
BG        = "#02080F"
BG2       = "#040D14"
BG3       = "#060F18"
BG4       = "#081420"
ACCENT    = "#00D4FF"
ACCENT2   = "#0099BB"
ACCENT3   = "#003D55"
ACCENT4   = "#002030"
TEXT      = "#DDF0FF"
TEXT_DIM  = "#2A5070"
TEXT_MID  = "#6A9AB8"
DANGER    = "#FF3A4A"
SUCCESS   = "#00FF88"
GOLD      = "#FFBB00"
ORANGE    = "#FF6B35"
PURPLE    = "#7B5EA7"


# ═══════════════════════════════════════════════════════════════════════════════
#  CANVAS WIDGETS
# ═══════════════════════════════════════════════════════════════════════════════

class NeuralMini(Canvas):
    """Mini neural network visualisation for the left panel."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG, highlightthickness=0, **kwargs)
        self.nodes = []
        self.pulses = []
        self._job = None
        self.active = False
        self.bind("<Configure>", self._init_nodes)

    def _init_nodes(self, event=None):
        w, h = self.winfo_width() or 200, self.winfo_height() or 120
        self.nodes = []
        for _ in range(20):
            self.nodes.append({
                "x": random.uniform(8, w - 8), "y": random.uniform(8, h - 8),
                "vx": random.uniform(-0.3, 0.3), "vy": random.uniform(-0.3, 0.3),
                "r": random.uniform(1.5, 3),
                "bright": random.random(), "bv": random.uniform(0.02, 0.04),
                "type": random.choice(["normal", "hot", "accent"])
            })
        self._rebuild_edges()

    def _rebuild_edges(self):
        w, h = self.winfo_width() or 200, self.winfo_height() or 120
        self.edges = []
        for i, a in enumerate(self.nodes):
            for b in self.nodes[i+1:]:
                dx, dy = a["x"] - b["x"], a["y"] - b["y"]
                dist = math.hypot(dx, dy)
                if dist < 55:
                    self.edges.append((i, self.nodes.index(b), dist))

    def start(self):
        if self.active: return
        self.active = True
        if not self.nodes:
            self._init_nodes()
        self._animate()

    def stop(self):
        self.active = False
        if self._job:
            self.after_cancel(self._job)

    def _animate(self):
        if not self.active: return
        self.delete("all")
        w, h = self.winfo_width() or 200, self.winfo_height() or 120

        for e in self.edges[:]:
            i, j, dist = e
            a, b = self.nodes[i], self.nodes[j]
            if i >= len(self.nodes) or j >= len(self.nodes):
                continue
            alpha = max(0, 0.3 - dist / 140)
            self.create_line(a["x"], a["y"], b["x"], b["y"],
                             fill=f"#0088BB", width=0.5, stipple="gray50")

        for p in self.pulses[:]:
            if p["t"] >= 1:
                self.pulses.remove(p); continue
            i, j = p["i"], p["j"]
            if i >= len(self.nodes) or j >= len(self.nodes):
                continue
            a, b = self.nodes[i], self.nodes[j]
            px = a["x"] + (b["x"] - a["x"]) * p["t"]
            py = a["y"] + (b["y"] - a["y"]) * p["t"]
            self.create_oval(px-3, py-3, px+3, py+3, fill=SUCCESS, outline="")
            p["t"] += p["s"]

        for n in self.nodes:
            n["bright"] += n["bv"]
            if n["bright"] > 1 or n["bright"] < 0: n["bv"] *= -1
            n["bright"] = max(0, min(1, n["bright"]))
            col = ORANGE if n["type"] == "hot" else SUCCESS if n["type"] == "accent" else ACCENT
            a = 0.3 + n["bright"] * 0.7
            self.create_oval(n["x"] - n["r"], n["y"] - n["r"],
                             n["x"] + n["r"], n["y"] + n["r"],
                             fill=col, outline="")
            n["x"] += n["vx"]; n["y"] += n["vy"]
            if n["x"] < 5 or n["x"] > w - 5: n["vx"] *= -1
            if n["y"] < 5 or n["y"] > h - 5: n["vy"] *= -1

        if random.random() < 0.04 and self.edges:
            e = random.choice(self.edges)
            self.pulses.append({"i": e[0], "j": e[1], "t": 0, "s": random.uniform(0.015, 0.03)})

        self._job = self.after(35, self._animate)


class HUDrings(Canvas):
    """Animated HUD rings with spinning arcs and pulsing core."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG, highlightthickness=0, **kwargs)
        self._angles = [0, 0, 0, 0]
        self._speeds = [1.2, -0.8, 1.8, -0.5]
        self._pulse = 0
        self._job = None
        self.active = False

    def start(self):
        if self.active: return
        self.active = True
        self._animate()

    def stop(self):
        self.active = False
        if self._job:
            self.after_cancel(self._job)

    def _animate(self):
        if not self.active: return
        self.delete("all")
        cx, cy = self.winfo_width() / 2 or 120, self.winfo_height() / 2 or 120
        self._pulse += 0.04
        b = 0.5 + 0.5 * math.sin(self._pulse)

        # Tick ring text
        r_tick = min(cx, cy) * 0.78
        for i in range(24):
            a = math.radians(i * 15)
            x1 = cx + r_tick * math.cos(a) - 0.5
            y1 = cy + r_tick * math.sin(a) - 0.5
            x2 = cx + r_tick * math.cos(a) + 0.5
            y2 = cy + r_tick * math.sin(a) + 0.5
            self.create_oval(x1, y1, x2, y2, fill=ACCENT, outline="")

        # Spinning rings
        ring_specs = [
            (min(cx, cy) * 0.92, 220, ACCENT, self._angles[0]),
            (min(cx, cy) * 0.78, 160, SUCCESS, self._angles[1]),
            (min(cx, cy) * 0.64, 260, f"{ACCENT}88", self._angles[2]),
            (min(cx, cy) * 0.50, 140, ORANGE, self._angles[3]),
        ]
        for r, extent, color, angle in ring_specs:
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                            start=angle, extent=extent,
                            outline=color, width=1.2, style="arc")

        # Core
        core_r = min(cx, cy) * 0.28
        self.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                         outline=f"{ACCENT}66", width=1)
        inner_r = core_r * 0.65
        c_b = 0.06 + b * 0.12
        self.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                         fill=f"#00D4FF" + format(int(c_b * 255), '02x'),
                         outline=ACCENT, width=1)
        dot_r = core_r * 0.18
        dot_b = 0.5 + b * 0.5
        self.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                         fill=ACCENT, outline="")

        self._angles = [(a + s) % 360 for a, s in zip(self._angles, self._speeds)]
        self._job = self.after(30, self._animate)


class ScanOverlay(Canvas):
    """Scanline overlay with sweeping horizontal line."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="black", highlightthickness=0, **kwargs)
        self._scan_x = 0
        self._job = None
        self.active = False

    def start(self):
        if self.active: return
        self.active = True
        self._animate()

    def stop(self):
        self.active = False
        if self._job:
            self.after_cancel(self._job)

    def _animate(self):
        if not self.active: return
        self.delete("all")
        w, h = self.winfo_width() or 1, self.winfo_height() or 1
        self._scan_x = (self._scan_x + 4) % (w + 40)
        self.create_line(self._scan_x - 60, 0, self._scan_x + 60, h,
                         fill=f"#00D4FF22", width=1)
        self.create_line(self._scan_x, 0, self._scan_x + 2, h,
                         fill=f"#00D4FF44", width=1)
        self._job = self.after(30, self._animate)


# ═══════════════════════════════════════════════════════════════════════════════
#  DIALOG WINDOWS (unchanged from v1)
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title("A.I.D.O — Secure Access")
        self.geometry("520x760")
        self.configure(fg_color=BG2)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        rings = HUDrings(self, width=400, height=200)
        rings.pack(fill="x", pady=(20, 0))
        rings.start()

        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=(8, 2))
        ctk.CTkLabel(logo_frame, text="AI", font=("Courier New", 48, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(logo_frame, text="D", font=("Courier New", 48, "bold"), text_color=SUCCESS).pack(side="left")
        ctk.CTkLabel(logo_frame, text="O", font=("Courier New", 48, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(self, text="◈  NEURAL HUD v2.1  ◈",
                     font=("Courier New", 9), text_color=TEXT_DIM).pack()
        ctk.CTkLabel(self, text="",
                     font=("Courier New", 9), text_color=ACCENT3).pack(fill="x", padx=28, pady=(6, 18))

        self.neural_mini = NeuralMini(self, width=440, height=120)
        self.neural_mini.pack(fill="x", padx=28)
        self.after(300, self.neural_mini.start)

        card = ctk.CTkFrame(self, fg_color=BG3, corner_radius=18, border_width=1, border_color=ACCENT4)
        card.pack(padx=28, pady=(18, 24), fill="x")

        self.user_entry = self._field(card, "▸  IDENTIFIER", "username")
        self.user_entry.insert(0, "duarte")
        self.pass_entry = self._field(card, "▸  PASSKEY", "password", show="●")
        self.pass_entry.bind("<Return>", lambda e: self._login())

        self.error_label = ctk.CTkLabel(card, text="", font=("Courier New", 11), text_color=DANGER)
        self.error_label.pack(pady=(10, 0))

        ctk.CTkButton(card, text="⟶  INITIATE ACCESS",
                      font=("Courier New", 12, "bold"),
                      fg_color=ACCENT4, hover_color=ACCENT3,
                      text_color=ACCENT, height=48, corner_radius=10,
                      border_width=1, border_color=ACCENT3,
                      command=self._login).pack(padx=24, pady=(12, 8), fill="x")

        ctk.CTkLabel(card, text="Registe o rosto apenas após login por senha.\nPode usar webcam ou carregar uma foto.",
                     font=("Courier New", 9), text_color=TEXT_DIM, wraplength=380, justify="left"
                     ).pack(padx=24, pady=(0, 12))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent", height=80)
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))
        btn_frame.pack_propagate(False)
        ctk.CTkButton(btn_frame, text="🙂  FACE LOGIN", font=("Courier New", 11, "bold"),
                      fg_color="#003D55", hover_color="#005577", text_color=ACCENT,
                      corner_radius=10, command=self._face_login
                      ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(btn_frame, text="📷  REGISTER FACE", font=("Courier New", 11, "bold"),
                      fg_color="#003D55", hover_color="#005577", text_color=ACCENT,
                      corner_radius=10, command=self._register_face
                      ).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ctk.CTkButton(btn_frame, text="📁  LOAD PHOTO", font=("Courier New", 11, "bold"),
                      fg_color="#003D55", hover_color="#005577", text_color=ACCENT,
                      corner_radius=10, command=self._register_face_from_file
                      ).pack(side="right", fill="x", expand=True, padx=(6, 0))

    def _field(self, parent, label, placeholder, show=None):
        ctk.CTkLabel(parent, text=label, font=("Courier New", 9), text_color=TEXT_DIM
                     ).pack(anchor="w", padx=24, pady=(20, 4))
        e = ctk.CTkEntry(parent, fg_color=BG4, border_color=ACCENT4, text_color=TEXT,
                         font=("Courier New", 13), height=46, corner_radius=10,
                         placeholder_text=placeholder, **(dict(show=show) if show else {}))
        e.pack(padx=24, fill="x")
        e.bind("<FocusIn>", lambda ev: e.configure(border_color=ACCENT))
        e.bind("<FocusOut>", lambda ev: e.configure(border_color=ACCENT4))
        return e

    def _login(self):
        username, password = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not username or not password:
            self.error_label.configure(text="⚠  All fields required.")
            return
        if auth.verify_login(username, password):
            self.neural_mini.stop()
            self.destroy()
            self.on_success()
        else:
            self.error_label.configure(text="✕  Access denied. Invalid credentials.")
            self.pass_entry.delete(0, "end")
            self.pass_entry.focus()

    def _face_login(self):
        username = self.user_entry.get().strip()
        if not username:
            return self.error_label.configure(text="⚠  Enter a username first.")
        if not auth.has_face_registered(username):
            return self.error_label.configure(text="⚠  Face not registered. Use password login and register.")
        if not cv2:
            return self.error_label.configure(text="⚠  Install opencv-python to use face login.")
        temp_file = self._capture_face()
        if not temp_file: return
        if auth.verify_face(username, temp_file):
            self.neural_mini.stop()
            self.destroy()
            self.on_success()
        else:
            self.error_label.configure(text="✕  Face not recognized. Try again.")
        try: os.remove(temp_file)
        except: pass

    def _register_face(self):
        username, password = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not username or not password:
            return self.error_label.configure(text="⚠  Username and password required.")
        if not auth.verify_login(username, password):
            return self.error_label.configure(text="✕  Invalid password. Cannot register face.")
        if not cv2:
            return self.error_label.configure(text="⚠  Install opencv-python to register face.")
        temp_file = self._capture_face()
        if not temp_file: return
        if auth.register_face(username, temp_file):
            self.error_label.configure(text="✓  Face registered successfully.")
        else:
            self.error_label.configure(text="✕  Could not save face image.")
        try: os.remove(temp_file)
        except: pass

    def _register_face_from_file(self):
        username, password = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not username or not password:
            return self.error_label.configure(text="⚠  Username and password required.")
        if not auth.verify_login(username, password):
            return self.error_label.configure(text="✕  Invalid password. Cannot register face.")
        filename = filedialog.askopenfilename(
            title="Select face image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png"), ("All files", "*")]
        )
        if not filename: return
        if auth.register_face(username, filename):
            self.error_label.configure(text="✓  Face registered from selected photo.")
        else:
            self.error_label.configure(text="✕  Could not save selected face image.")

    def _capture_face(self):
        self.error_label.configure(text="Capturing face... Please look at the camera.")
        self.update()
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if os.name == "nt" else 0)
            if not cap.isOpened():
                self.error_label.configure(text="✕  Camera not available.")
                return None
            for _ in range(5): cap.read()
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                self.error_label.configure(text="✕  Failed to capture image.")
                return None
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            cv2.imwrite(temp.name, frame)
            temp.close()
            return temp.name
        except Exception as e:
            self.error_label.configure(text=f"✕  Camera error: {e}")
            return None


class ConfirmActionWindow(ctk.CTkToplevel):
    def __init__(self, master, on_complete, default_action=None, default_arg=None):
        super().__init__(master)
        self.on_complete = on_complete
        self.default_action = default_action
        self.default_arg = default_arg
        self.title("AIDO — Confirm Action")
        self.geometry("420x220")
        self.configure(fg_color=BG2)
        self.grab_set()
        self._build()

    def _build(self):
        self.frame = ctk.CTkFrame(self, fg_color=BG3, corner_radius=12)
        self.frame.pack(padx=12, pady=12, fill="both", expand=True)
        ctk.CTkLabel(self.frame, text="Select action:", text_color=TEXT_DIM).pack(anchor="w", pady=(6, 2))
        self.action_var = ctk.CTkComboBox(
            self.frame, values=list(pc_actions.ALLOWED_ACTIONS.keys()) if pc_actions.ALLOWED_ACTIONS else ["(no actions available)"]
        )
        keys = list(pc_actions.ALLOWED_ACTIONS.keys())
        self.action_var.set(self.default_action if self.default_action in keys else (keys[0] if keys else ""))
        self.action_var.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(self.frame, text="Argument (optional):", text_color=TEXT_DIM).pack(anchor="w")
        self.arg_entry = ctk.CTkEntry(self.frame, placeholder_text="e.g. https://example.com or scripts/myscript.py")
        if self.default_arg: self.arg_entry.insert(0, self.default_arg)
        self.arg_entry.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(self.frame, text="Confirm with credentials:", text_color=TEXT_DIM).pack(anchor="w", pady=(6, 2))
        self.user_entry = ctk.CTkEntry(self.frame, placeholder_text="username")
        self.user_entry.pack(fill="x", pady=(0, 4))
        self.pass_entry = ctk.CTkEntry(self.frame, placeholder_text="password", show="●")
        self.pass_entry.pack(fill="x", pady=(0, 8))
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Confirm & Execute", command=self._confirm, width=180).pack(side="right", padx=6)

    def _confirm(self):
        action = self.action_var.get()
        arg = self.arg_entry.get().strip()
        username, password = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not username or not password:
            ctk.CTkLabel(self.frame, text="Credentials required.", text_color=DANGER).pack()
            return
        result = pc_actions.perform_action(action, arg, username, password)
        try: self.on_complete(result)
        except: pass
        self.destroy()


class ConfirmBrowserWindow(ctk.CTkToplevel):
    def __init__(self, master, on_complete, browser_name):
        super().__init__(master)
        self.on_complete = on_complete
        self.browser_name = browser_name
        self.title("AIDO — Confirm Browser")
        self.geometry("380x170")
        self.configure(fg_color=BG2)
        self.grab_set()
        self._build()

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color=BG3, corner_radius=12)
        frame.pack(padx=12, pady=12, fill="both", expand=True)
        ctk.CTkLabel(frame, text=f"AIDO detected a request to open {self.browser_name}.",
                     font=("Courier New", 11), text_color=TEXT, wraplength=340).pack(pady=(8, 12))
        ctk.CTkLabel(frame, text="Do you want to proceed?",
                     font=("Courier New", 10), text_color=TEXT_DIM).pack(pady=(0, 14))
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Open Browser", command=self._confirm, width=160).pack(side="right", padx=6)

    def _confirm(self):
        result = pc_actions.open_browser(self.browser_name, use_opera=(self.browser_name.lower() in ("opera gx", "opera")))
        try: self.on_complete(result)
        except: pass
        self.destroy()


class CodeUpdateWindow(ctk.CTkToplevel):
    def __init__(self, master, filename, code, on_approved):
        super().__init__(master)
        self.filename = filename
        self.code = code
        self.on_approved = on_approved
        self.title(f"System Modification — {filename}")
        self.geometry("740x640")
        self.configure(fg_color=BG2)
        self.grab_set()
        self._build()

    def _build(self):
        warn = ctk.CTkFrame(self, fg_color="#140800", corner_radius=0, height=58)
        warn.pack(fill="x")
        warn.pack_propagate(False)
        ctk.CTkLabel(warn, text=f"⚠  AIDO REQUESTS FILE MODIFICATION: {self.filename}",
                     font=("Courier New", 12, "bold"), text_color=GOLD).pack(expand=True)
        ctk.CTkLabel(self, text="Review the proposed changes carefully. Approving will overwrite the file and restart AIDO.",
                     font=("Courier New", 10), text_color=TEXT_MID, wraplength=700).pack(pady=(12, 8))
        box = ctk.CTkTextbox(self, fg_color=BG, font=("Courier New", 12), text_color=ACCENT,
                             corner_radius=12, border_width=1, border_color=ACCENT4)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        box.insert("1.0", self.code)
        box.configure(state="disabled")
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=14)
        ctk.CTkButton(btn_frame, text="✕  REJECT", fg_color="#300010", hover_color=DANGER,
                      text_color=DANGER, border_width=1, border_color=DANGER,
                      width=160, height=46, corner_radius=10, font=("Courier New", 12, "bold"),
                      command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="✓  APPROVE & RESTART", fg_color="#003020", hover_color=SUCCESS,
                      text_color=SUCCESS, border_width=1, border_color=SUCCESS,
                      width=220, height=46, corner_radius=10, font=("Courier New", 12, "bold"),
                      command=self._approve).pack(side="right", padx=10)

    def _approve(self):
        try:
            filepath = os.path.join(os.path.dirname(__file__), self.filename)
            with open(filepath, "w", encoding="utf-8") as f: f.write(self.code)
            self.destroy()
            self.on_approved()
        except Exception as e:
            print(f"Failed to write file: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

class AIDOApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("A.I.D.O — Neural HUD v2.1")
        self.geometry("1200x800")
        self.configure(fg_color=BG)
        self.minsize(900, 620)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        from brain import AIDOBrain
        self.brain = AIDOBrain()
        self.requires_wake_word = True
        self.last_active_time = 0
        self.timeout_seconds = 60
        self.is_generating = False
        self.streaming_buffer = ""
        self._msg_count = 0
        self._uptime_secs = 0
        self._metric_vals = {}
        self._listening = False
        self._listen_thread = None
        self._listen_stop = Event()
        self._recognizer = sr.Recognizer() if sr else None

        self._build_layout()
        LoginWindow(self, on_success=self._on_login_success)

    def _on_login_success(self):
        self.deiconify()
        self.boot_sequence()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_layout(self):
        self._scanline = ScanOverlay(self)
        self._scanline.place(x=0, y=0, relwidth=1, relheight=1)
        self._scanline.start()

        # Main grid container
        self.main_grid = ctk.CTkFrame(self, fg_color="transparent")
        self.main_grid.pack(fill="both", expand=True)
        self.main_grid.grid_rowconfigure(0, weight=0)
        self.main_grid.grid_rowconfigure(1, weight=1)
        self.main_grid.grid_rowconfigure(2, weight=0)
        self.main_grid.grid_columnconfigure(0, weight=0, minsize=220)
        self.main_grid.grid_columnconfigure(1, weight=1)
        self.main_grid.grid_columnconfigure(2, weight=0, minsize=220)

        self._build_topbar()
        self._build_left()
        self._build_center()
        self._build_right()
        self._build_bottombar()

    # ── Top bar ─────────────────────────────────────────────────────────────

    def _build_topbar(self):
        tb = ctk.CTkFrame(self.main_grid, fg_color=BG2, corner_radius=0, height=48)
        tb.grid(row=0, column=0, columnspan=3, sticky="nsew")
        tb.pack_propagate(False)
        tb.grid_propagate(False)

        ctk.CTkLabel(tb, text="AI", font=("Courier New", 20, "bold"), text_color=ACCENT).pack(side="left", padx=(24, 0))
        ctk.CTkLabel(tb, text="D", font=("Courier New", 20, "bold"), text_color=SUCCESS).pack(side="left", padx=0)
        ctk.CTkLabel(tb, text="O", font=("Courier New", 20, "bold"), text_color=ACCENT).pack(side="left", padx=(0, 24))

        status_frame = ctk.CTkFrame(tb, fg_color="transparent")
        status_frame.pack(side="left", fill="x", expand=True, padx=20)
        self.status_dot = Canvas(status_frame, width=8, height=8, bg=BG2, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6))
        self._draw_status_dot(SUCCESS)
        self.status_label = ctk.CTkLabel(status_frame, text="STANDBY",
                                         font=("Courier New", 10), text_color=TEXT_DIM)
        self.status_label.pack(side="left")

        self.time_label = ctk.CTkLabel(tb, text="",
                                       font=("Courier New", 10), text_color=TEXT_DIM)
        self.time_label.pack(side="right", padx=24)
        self._update_clock()

    def _update_clock(self):
        now = time.localtime()
        self.time_label.configure(text=f"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}")
        self.after(1000, self._update_clock)

    def _draw_status_dot(self, colour):
        self.status_dot.delete("all")
        x = y = 4
        self.status_dot.create_oval(x-3, y-3, x+3, y+3, fill=colour, outline="")

    # ── Left panel ──────────────────────────────────────────────────────────

    def _build_left(self):
        left = ctk.CTkFrame(self.main_grid, fg_color=BG2, corner_radius=0)
        left.grid(row=1, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_propagate(False)
        left.configure(width=220)

        # System metrics
        row = 0
        self._section_label(left, "SYSTEM METRICS", row)
        row = 1
        self._metric_row(left, row, "NEURAL LOAD", "74%", SUCCESS)
        self._progress_bar(left, row+1, 0.74, SUCCESS)
        row = 3
        self._metric_row(left, row, "MEMORY POOL", "58%", ACCENT)
        self._progress_bar(left, row+1, 0.58, ACCENT)
        row = 5
        self._metric_row(left, row, "PROC THREADS", "91%", ORANGE)
        self._progress_bar(left, row+1, 0.91, ORANGE)
        row = 7

        # Thought network
        self._section_label(left, "THOUGHT NETWORK", row)
        row = 8
        self.neural_mini = NeuralMini(left)
        self.neural_mini.grid(row=row, column=0, sticky="nsew", padx=10, pady=(0, 4))
        self.neural_mini.configure(height=120)
        left.grid_rowconfigure(row, weight=1)
        row = 9
        self.thought_label = ctk.CTkLabel(left, text="PROCESSANDO...",
                                          font=("Courier New", 8), text_color=TEXT_DIM)
        self.thought_label.grid(row=row, column=0, pady=(0, 8))

        # Active modules
        row = 10
        self._section_label(left, "ACTIVE MODULES", row)
        row = 11
        tags_frame = ctk.CTkFrame(left, fg_color="transparent")
        tags_frame.grid(row=row, column=0, padx=10, pady=(0, 12), sticky="w")
        for t in ["VOICE", "SCAN", "AI-CORE", "NET"]:
            lbl = ctk.CTkLabel(tags_frame, text=t, font=("Courier New", 8),
                               text_color=ACCENT, fg_color=BG4,
                               corner_radius=4, padx=8, pady=2)
            lbl.pack(side="left", padx=2)

        def cycle_thought():
            thoughts = ["ANALISANDO INPUT", "PROCESSANDO...", "MEMORIA ATIVA",
                        "INFERENCIA EM CURSO", "CONTEXTO CARREGADO", "RESPOSTA A GERAR"]
            import itertools
            self._thought_cycle = itertools.cycle(thoughts)
            self._cycle_thought()
        self.after(2000, cycle_thought)

    def _cycle_thought(self):
        self.thought_label.configure(text=next(self._thought_cycle))
        self.after(2000, self._cycle_thought)

    def _section_label(self, parent, text, row):
        lbl = ctk.CTkLabel(parent, text=text, font=("Courier New", 8),
                           text_color=TEXT_DIM, anchor="w", justify="left")
        lbl.grid(row=row, column=0, padx=14, pady=(14, 2), sticky="ew")

    def _metric_row(self, parent, row, label, value, colour):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=0, padx=14, pady=(2, 0), sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f, text=label, font=("Courier New", 9), text_color=TEXT_DIM,
                     anchor="w").grid(row=0, column=0, sticky="w")
        self._metric_vals[label] = ctk.CTkLabel(f, text=value, font=("Courier New", 11),
                                                text_color=colour, anchor="e")
        self._metric_vals[label].grid(row=0, column=1, sticky="e")

    def _progress_bar(self, parent, row, pct, colour):
        f = ctk.CTkFrame(parent, fg_color=BG4, corner_radius=2, height=4)
        f.grid(row=row, column=0, padx=14, pady=(2, 0), sticky="ew")
        f.pack_propagate(False)
        bar = ctk.CTkFrame(f, fg_color=colour, corner_radius=2, height=4)
        bar.place(relx=0, rely=0, relwidth=pct, relheight=1)

    # ── Center ──────────────────────────────────────────────────────────────

    def _build_center(self):
        center = ctk.CTkFrame(self.main_grid, fg_color="transparent")
        center.grid(row=1, column=1, sticky="nsew")
        center.grid_rowconfigure(0, weight=1)
        center.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(center, fg_color="transparent")
        inner.grid(row=0, column=0)

        # HUD Rings
        self.hud = HUDrings(inner, width=220, height=220)
        self.hud.pack(pady=(14, 0))

        self.aido_label = ctk.CTkLabel(inner, text="AIDO",
                                       font=("Courier New", 28, "bold"), text_color=ACCENT)
        self.aido_label.pack(pady=(4, 8))

        # Chat output
        self.chat_box = ctk.CTkTextbox(inner, fg_color="transparent", corner_radius=0,
                                       font=("Courier New", 12), text_color=TEXT,
                                       state="disabled", wrap="word", height=140, width=500)
        self.chat_box.pack(pady=(0, 6))
        self.chat_box.tag_config("user", foreground="#4DF0FF", justify="right")
        self.chat_box.tag_config("aido", foreground=SUCCESS, justify="left")
        self.chat_box.tag_config("system", foreground=TEXT_DIM, justify="center")
        self.chat_box.tag_config("label_user", foreground=ACCENT2, justify="right")
        self.chat_box.tag_config("label_aido", foreground=ACCENT, justify="left")
        self.chat_box.tag_config("divider", foreground=ACCENT4, justify="center")

        # Input
        inp_frame = ctk.CTkFrame(inner, fg_color="transparent")
        inp_frame.pack(fill="x", pady=(0, 14))
        self.input_field = ctk.CTkEntry(inp_frame, placeholder_text="> insere comando ou query...",
                                        fg_color=BG3, border_color=ACCENT4, text_color=TEXT,
                                        font=("Courier New", 13), height=42, corner_radius=6)
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.input_field.bind("<Return>", self.send_message)
        self.input_field.bind("<FocusIn>", lambda e: self.input_field.configure(border_color=ACCENT))
        self.input_field.bind("<FocusOut>", lambda e: self.input_field.configure(border_color=ACCENT4))

        self.send_btn = ctk.CTkButton(inp_frame, text="EXEC",
                                      font=("Courier New", 11, "bold"),
                                      fg_color=ACCENT4, hover_color=ACCENT3, text_color=ACCENT,
                                      height=42, width=80, corner_radius=6, border_width=1,
                                      border_color=ACCENT4, command=lambda: self.send_message(None))
        self.send_btn.pack(side="right", padx=(6, 0))

        # Bottom controls
        ctrl_frame = ctk.CTkFrame(center, fg_color="transparent")
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        self.mic_btn = ctk.CTkButton(ctrl_frame, text="🎤 MIC", width=70, height=30,
                                     font=("Courier New", 9, "bold"),
                                     fg_color=BG4, hover_color="#0A3040", text_color=ACCENT,
                                     corner_radius=6, border_width=1, border_color=ACCENT4,
                                     command=self.toggle_listen)
        self.mic_btn.pack(side="left", padx=2)

        actions = [
            ("🖥", "system info"),
            ("📝", "save note: "),
            ("🧮", "calc "),
            ("🚀", "open app "),
            ("📁", "list folder "),
            ("🗑", "__clear__"),
        ]
        for sym, cmd in actions:
            b = ctk.CTkButton(ctrl_frame, text=sym, width=36, height=30,
                              font=("Courier New", 11),
                              fg_color=BG4, hover_color=BG3, text_color=TEXT_MID,
                              corner_radius=6, border_width=1, border_color=ACCENT4,
                              command=lambda c=cmd: self._quick_action(c))
            b.pack(side="left", padx=2)

    # ── Right panel ─────────────────────────────────────────────────────────

    def _build_right(self):
        right = ctk.CTkFrame(self.main_grid, fg_color=BG2, corner_radius=0)
        right.grid(row=1, column=2, sticky="nsew")
        right.grid_propagate(False)
        right.configure(width=220)

        # Scan overlay block
        row = 0
        self._section_label(right, "SCAN OVERLAY", row)
        row = 1
        scan_b = ctk.CTkFrame(right, fg_color=BG3, corner_radius=6, border_width=1, border_color=ACCENT4)
        scan_b.grid(row=row, column=0, padx=10, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(scan_b, text="ENTITY DETECTED", font=("Courier New", 8),
                     text_color=SUCCESS).pack(anchor="w", padx=10, pady=(6, 2))
        for label, val in [("STATUS", "ACTIVE"), ("USER", "DUARTE"),
                           ("CLEARANCE", "ALPHA-1"), ("SESSION", "00:00")]:
            f = ctk.CTkFrame(scan_b, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(f, text=label, font=("Courier New", 9), text_color=TEXT_DIM).pack(side="left")
            ctk.CTkLabel(f, text=val, font=("Courier New", 9), text_color=ACCENT).pack(side="right")
        self._scan_sess_label = scan_b.winfo_children()[-1] if scan_b.winfo_children() else None
        if hasattr(self, '_scan_sess_label'):
            pass  # will update via uptime

        # Validation block
        row = 2
        self._section_label(right, "VALIDATION", row)
        row = 3
        val_b = ctk.CTkFrame(right, fg_color=BG3, corner_radius=6, border_width=1, border_color="#00FF8833")
        val_b.grid(row=row, column=0, padx=10, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(val_b, text="PROP CHECK", font=("Courier New", 8),
                     text_color=ACCENT).pack(anchor="w", padx=10, pady=(6, 2))
        for label, val in [("LAST-ACK", "38.6/100"), ("VALIDATION", "12.4/100"),
                           ("CMD-ID", "12-96-XXXX"), ("IBAN", "PT50-XXXX")]:
            f = ctk.CTkFrame(val_b, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=1)
            col = SUCCESS if label == "VALIDATION" else ACCENT
            ctk.CTkLabel(f, text=label, font=("Courier New", 9), text_color=TEXT_DIM).pack(side="left")
            ctk.CTkLabel(f, text=val, font=("Courier New", 9), text_color=col).pack(side="right")

        # System log
        row = 4
        self._section_label(right, "SYSTEM LOG", row)
        row = 5
        log_frame = ctk.CTkFrame(right, fg_color=BG3, corner_radius=6, border_width=1, border_color=ACCENT4)
        log_frame.grid(row=row, column=0, padx=10, pady=(0, 12), sticky="nsew")
        right.grid_rowconfigure(row, weight=1)
        self.log_text = ctk.CTkTextbox(log_frame, fg_color="transparent", font=("Courier New", 9),
                                       text_color=TEXT_DIM, state="disabled", wrap="none")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        for line in [
            "[OK] Neural core initialized",
            "[--] Groq API handshake...",
            "[OK] API link established",
            "[--] Loading persona: AIDO v2",
            "[OK] Persona loaded",
            "[!!] GPU offload limited",
            "[--] Monitoring threads...",
        ]:
            self._log_line(line)

    def _log_line(self, text):
        self.log_text.configure(state="normal")
        tag = None
        if "[OK]" in text: tag = "green"
        elif "[!!]" in text: tag = "orange"
        if tag:
            self.log_text.tag_config(tag, foreground=SUCCESS if tag == "green" else ORANGE)
        self.log_text.insert("end", text + "\n", tag)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    # ── Bottom bar ──────────────────────────────────────────────────────────

    def _build_bottombar(self):
        bb = ctk.CTkFrame(self.main_grid, fg_color=BG2, corner_radius=0, height=36)
        bb.grid(row=2, column=0, columnspan=3, sticky="nsew")
        bb.pack_propagate(False)

        items = [
            ("MODE", "ACTIVE"), ("UPTIME", "00:00:00"),
            ("TEMP", "42°C"), ("PACKETS", "0"), ("UPLINK", "SECURE"),
        ]
        for label, val in items:
            f = ctk.CTkFrame(bb, fg_color="transparent")
            f.pack(side="left", padx=(14, 0))
            ctk.CTkLabel(f, text=label, font=("Courier New", 8), text_color=TEXT_DIM).pack(side="left")
            lbl = ctk.CTkLabel(f, text=val, font=("Courier New", 8), text_color=TEXT_MID)
            lbl.pack(side="left", padx=(4, 0))
            if label == "UPTIME": self._uptime_label = lbl
            elif label == "TEMP": self._temp_label = lbl
            elif label == "PACKETS": self._pkt_label = lbl

        self._session_start = time.time()
        self._packets = 0
        self._update_bottombar()

    def _update_bottombar(self):
        e = int(time.time() - self._session_start)
        if hasattr(self, '_uptime_label'):
            self._uptime_label.configure(text=f"{e//3600:02d}:{(e//60)%60:02d}:{e%60:02d}")
            # also update scan session
            if hasattr(self, '_scan_sess_label'):
                pass
        if hasattr(self, '_temp_label'):
            import random
            self._temp_label.configure(text=f"{40 + random.randint(0,6)}°C")
        if hasattr(self, '_pkt_label'):
            self._packets += random.randint(0, 12)
            self._pkt_label.configure(text=str(self._packets))
        self.after(5000, self._update_bottombar)

    # ── Message handling ────────────────────────────────────────────────────

    def add_system_message(self, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"\n  ─── {text} ───\n\n", "system")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def add_user_message(self, text):
        self._msg_count += 1
        self.chat_box.configure(state="normal")
        if self._msg_count > 1:
            self.chat_box.insert("end", "  ·  ·  ·\n", "divider")
        self.chat_box.insert("end", "  you  ▸\n", "label_user")
        self.chat_box.insert("end", f"  {text}\n", "user")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def start_aido_stream(self):
        self.streaming_buffer = ""
        self._set_status("PROCESSING...", ACCENT)
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", "\naido  ◈\n", "label_aido")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def update_aido_stream(self, token):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", token, "aido")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def finish_aido_stream(self):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", "\n", "aido")
        self.chat_box.configure(state="disabled")
        self.is_generating = False
        self._set_status("LISTENING", ACCENT)
        self.input_field.configure(state="normal")
        self.input_field.focus()

    def _on_action_result(self, result_text):
        self.add_system_message(result_text)

    def on_approved_restart(self):
        self.add_system_message("System file updated. Rebooting core systems...")
        self.update()
        self.after(2000, lambda: os.execv(sys.executable, sys.argv))

    def _handle_local_command(self, command: str) -> bool:
        lower = command.lower()
        if re.search(r"\b(abre|abrir|open)\b.*\b(opera gx|opera|operagx)\b", lower):
            self._on_action_result(pc_actions.open_browser("", use_opera=True))
            return True
        if re.search(r"\b(abre|abrir|open)\b.*\b(browser|navegador)\b", lower):
            self._on_action_result(pc_actions.open_browser(""))
            return True
        if re.search(r"\b(abre|abrir|open)\b.*\b(explorer|file explorer|explorador)\b", lower):
            self._on_action_result(pc_actions.open_explorer(""))
            return True
        return False

    def _quick_action(self, action: str):
        if action == "__clear__":
            self.clear_chat()
            return
        self.input_field.delete(0, "end")
        self.input_field.insert(0, action)
        self.input_field.focus()

    def clear_chat(self):
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        self.brain.conversation_history.clear()
        self._msg_count = 0
        self.add_system_message("Chat cleared.")

    # ── Boot ────────────────────────────────────────────────────────────────

    def boot_sequence(self):
        try:
            self.neural_mini.start()
            self.hud.start()
            self._set_status("INITIALIZING BRAIN...", ACCENT)
            self.update()
            self.brain.load_config()
            self._set_status("CONNECTING TO MEMORY CLOUD...", ACCENT)
            self.update()
            self.brain.init_memory()
            self._set_status("CONNECTING TO GROQ API...", ACCENT)
            self.update()
            self.brain.init_model()
            self._set_status("SYSTEMS ONLINE", SUCCESS)
            self._draw_status_dot(SUCCESS)
            self.add_system_message("AIDO systems online. Say 'AIDO' to activate.")
            self._log_line("[OK] Neural core initialized")
            self._log_line("[OK] Groq API link established")
            self._log_line("[OK] Persona loaded")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._set_status(f"BOOT ERROR: {e}", DANGER)
            self._draw_status_dot(DANGER)

    # ── Voice ───────────────────────────────────────────────────────────────

    def toggle_listen(self):
        if not sr:
            self.add_system_message("Microphone support not available (install speech_recognition).")
            return
        if self._listening:
            self._listen_stop.set()
            if self._listen_thread and self._listen_thread.is_alive():
                self._listen_thread.join(timeout=2)
            self._listening = False
            self._listen_stop.clear()
            self.mic_btn.configure(fg_color=BG4)
            self._set_status("STANDBY", TEXT_DIM)
            self.add_system_message("Microphone disabled.")
        else:
            self._listening = True
            self.mic_btn.configure(fg_color=SUCCESS)
            self._set_status("MICROPHONE ACTIVE", ACCENT)
            self.add_system_message("Microphone enabled. Listening...")
            self._listen_thread = Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

    def _listen_loop(self):
        recognizer = self._recognizer
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                while not self._listen_stop.is_set():
                    try:
                        audio = recognizer.listen(source, phrase_time_limit=8)
                        try:
                            text = recognizer.recognize_google(audio, language="pt-PT")
                        except Exception:
                            try:
                                text = recognizer.recognize_google(audio, language="pt-BR")
                            except Exception:
                                continue
                        if text.strip():
                            self.after(0, lambda t=text.strip(): self._on_recognized(t))
                    except Exception:
                        continue
        except Exception as e:
            self.after(0, lambda: self.add_system_message(f"Microphone error: {e}"))
            self.mic_btn.configure(fg_color=BG4)
            self._listening = False

    def _on_recognized(self, text: str):
        self.input_field.delete(0, "end")
        self.input_field.insert(0, text)
        self.send_message(None)

    # ── Send ────────────────────────────────────────────────────────────────

    def send_message(self, event):
        if self.is_generating: return
        command = self.input_field.get().strip()
        self.input_field.delete(0, "end")
        if not command: return

        if self.requires_wake_word and (time.time() - self.last_active_time) > self.timeout_seconds:
            normalized = command.lower().replace("aido,", "aido").strip()
            if not (normalized.startswith("aido ") or normalized == "aido"):
                self._set_status("STANDBY — Say 'AIDO' to activate", DANGER)
                return
            command = normalized.replace("aido", "", 1).strip()
            if not command:
                self.add_system_message("AIDO activated. Listening...")
                self.last_active_time = time.time()
                self.requires_wake_word = False
                return

        self.last_active_time = time.time()
        self.requires_wake_word = False

        if self._handle_local_command(command): return

        self.add_user_message(command)
        self.is_generating = True
        self._set_status("PROCESSING...", ACCENT)
        self.input_field.configure(state="disabled")
        self.start_aido_stream()

        self.brain.stream_response(
            command,
            on_token_callback=lambda token: self.after(0, lambda t=token: self.update_aido_stream(t)),
            on_complete_callback=lambda: self.after(0, self.finish_aido_stream),
            on_code_update_callback=lambda filename, code: self.after(
                0, lambda: CodeUpdateWindow(self, filename, code, self.on_approved_restart)),
            on_action_request=self._handle_action_request,
        )

    def _handle_action_request(self, action, arg=None):
        if action == "open_browser_opera":
            self._on_action_result(pc_actions.open_browser(arg or "", use_opera=True))
        elif action == "open_browser":
            self._on_action_result(pc_actions.open_browser(arg or ""))
        elif action == "confirm_browser":
            self.after(0, lambda: ConfirmBrowserWindow(self, self._on_action_result, arg))
        elif action == "open_app":
            from tools import launch_app
            self._on_action_result(launch_app(arg or ""))
        else:
            self.after(0, lambda: ConfirmActionWindow(self, self._on_action_result,
                                                       default_action=action, default_arg=arg))

    def _set_status(self, text, color=None):
        color = color or TEXT_DIM
        self.status_label.configure(text=text, text_color=color)
        self._draw_status_dot(color)


if __name__ == "__main__":
    app = AIDOApp()
    app.mainloop()
