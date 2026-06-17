"""AIDO GUI — cyberpunk-themed desktop assistant built with customtkinter."""
import os
import sys
import time
import math
import random
import re
import tempfile
import customtkinter as ctk
from tkinter import Canvas, filedialog
from aido_overlay import AIDOOverlay
import pc_actions
import auth
import threading

try:
    import speech_recognition as sr
except Exception:
    sr = None
try:
    import cv2
except Exception:
    cv2 = None


# ── Colour palette ────────────────────────────────────────────────────────

BG        = "#04080f"
BG2       = "#080f1a"
BG3       = "#0c1525"
BG4       = "#101d30"
ACCENT    = "#00e5ff"
ACCENT2   = "#0099bb"
ACCENT3   = "#003d55"
ACCENT4   = "#001f2e"
TEXT      = "#ddeeff"
TEXT_DIM  = "#2d5070"
TEXT_MID  = "#6a9ab8"
DANGER    = "#ff3a4a"
SUCCESS   = "#00ffaa"
GOLD      = "#ffbb00"
PURPLE    = "#7b5ea7"


# ── Neural network background canvas ──────────────────────────────────────

class NeuralCanvas(Canvas):
    """Animated neural network particle background."""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG, highlightthickness=0, **kwargs)
        self.nodes = []
        self.active = False
        self._job = None
        self.speed = 0.0
        self.target_speed = 0.0
        self.tick = 0
        self.bind("<Configure>", self._init_nodes)

    def _init_nodes(self, event=None):
        w = self.winfo_width() or 540
        h = self.winfo_height() or 160
        self.nodes = []
        for _ in range(90):
            self.nodes.append({
                "x": random.uniform(0, w), "y": random.uniform(0, h),
                "vx": random.uniform(-0.8, 0.8), "vy": random.uniform(-0.8, 0.8),
                "r": random.uniform(1.2, 3.8),
                "pulse": random.uniform(0, math.pi * 2),
                "hue": random.choice([ACCENT, ACCENT2, PURPLE]),
            })

    def set_state(self, state):
        self.target_speed = {"standby": 0.0, "online": 0.4, "thinking": 2.5}.get(state, 0.4)

    def start(self):
        if self.active:
            return
        self.active = True
        if not self.nodes:
            self._init_nodes()
        self._animate()

    def stop(self):
        self.active = False
        if self._job:
            self.after_cancel(self._job)
        self.delete("all")

    def _animate(self):
        if not self.active:
            return
        self.delete("all")
        self.tick += 1
        w = self.winfo_width() or 540
        h = self.winfo_height() or 160
        self.speed += (self.target_speed - self.speed) * 0.05

        # Scan line
        sweep_x = (self.tick * 3) % (w + 60) - 30
        if self.speed > 0.1:
            self.create_rectangle(sweep_x, 0, sweep_x + 2, h, fill=ACCENT, outline="", stipple="gray25")

        for n in self.nodes:
            n["pulse"] += 0.025 + self.speed * 0.01
            n["x"] += n["vx"] * self.speed
            n["y"] += n["vy"] * self.speed
            if n["x"] < 0 or n["x"] > w: n["vx"] *= -1
            if n["y"] < 0 or n["y"] > h: n["vy"] *= -1

        # Connections
        for i, a in enumerate(self.nodes):
            for b in self.nodes[i + 1:]:
                dx, dy = a["x"] - b["x"], a["y"] - b["y"]
                dist = math.hypot(dx, dy)
                if dist < 120:
                    frac = 1 - dist / 120
                    alpha = int(200 * frac * frac)
                    if self.speed < 0.05:
                        alpha = int(alpha * 0.15)
                    g = min(int(alpha * 0.8) + 80, 220)
                    bv = min(alpha + 140, 255)
                    lw = 0.5 + frac * self.speed * 0.3
                    self.create_line(a["x"], a["y"], b["x"], b["y"],
                                     fill=f"#{0:02x}{g:02x}{bv:02x}",
                                     width=max(0.4, min(lw, 1.8)))

        # Nodes
        for n in self.nodes:
            pulse = 0.5 + 0.5 * math.sin(n["pulse"])
            r = n["r"] + pulse * self.speed * 0.6
            brt = int(60 + 195 * pulse) if self.speed > 0.05 else 35
            if self.speed > 0.5:
                gr = r + 3 + pulse * 2
                gc = f"#{0:02x}{int(brt*0.3):02x}{min(int(brt*0.3)+40,255):02x}"
                self.create_oval(n["x"] - gr, n["y"] - gr, n["x"] + gr, n["y"] + gr, fill=gc, outline="")
            self.create_oval(n["x"] - r, n["y"] - r, n["x"] + r, n["y"] + r,
                             fill=f"#{0:02x}{brt:02x}{min(brt+60,255):02x}", outline="")

        self._job = self.after(28, self._animate)


# ── Glowing separator ─────────────────────────────────────────────────────

class GlowSep(Canvas):
    """Thin horizontal glowing line separator."""
    def __init__(self, master, color=ACCENT, **kwargs):
        super().__init__(master, bg=BG, highlightthickness=0, height=2, **kwargs)
        self.color = color
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width() or 540
        self.create_line(0, 1, w, 1, fill=self.color, width=1)
        self.create_line(0, 0, w, 0, fill=ACCENT4, width=1)


# ── Login window ──────────────────────────────────────────────────────────

class LoginWindow(ctk.CTkToplevel):
    """Secure login screen with password and optional face recognition."""

    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title("A.I.D.O — Secure Access")
        self.geometry("520x760")
        self.configure(fg_color=BG)
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
        self.neural = NeuralCanvas(self, width=440, height=150)
        self.neural.pack(fill="x")
        self.after(200, lambda: [self.neural.start(), self.neural.set_state("thinking")])

        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=(14, 2))
        ctk.CTkLabel(logo_frame, text="A.I.D.O", font=("Courier New", 46, "bold"), text_color=ACCENT).pack()
        ctk.CTkLabel(logo_frame, text="◈  SECURE ACCESS TERMINAL  ◈",
                     font=("Courier New", 9), text_color=TEXT_DIM).pack(pady=(2, 0))
        GlowSep(self, color=ACCENT).pack(fill="x", padx=28, pady=(14, 18))

        card = ctk.CTkFrame(self, fg_color=BG2, corner_radius=18, border_width=1, border_color=ACCENT3)
        card.pack(padx=28, pady=(18, 24), fill="x")

        # Form fields
        self.user_entry = self._field(card, "▸  IDENTIFIER", "username")
        self.user_entry.insert(0, "duarte")
        self.pass_entry = self._field(card, "▸  PASSKEY", "password", show="●")
        self.pass_entry.bind("<Return>", lambda e: self._login())

        self.error_label = ctk.CTkLabel(card, text="", font=("Courier New", 11), text_color=DANGER)
        self.error_label.pack(pady=(10, 0))

        ctk.CTkButton(card, text="⟶  INITIATE ACCESS",
                      font=("Courier New", 12, "bold"),
                      fg_color=ACCENT3, hover_color=ACCENT2,
                      text_color=ACCENT, height=48, corner_radius=10,
                      border_width=1, border_color=ACCENT2,
                      command=self._login).pack(padx=24, pady=(12, 8), fill="x")

        ctk.CTkLabel(card, text="Registe o rosto apenas após login por senha.\nPode usar webcam ou carregar uma foto.",
                     font=("Courier New", 9), text_color=TEXT_DIM, wraplength=380, justify="left"
                     ).pack(padx=24, pady=(0, 12))

        # Face buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent", height=80)
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))
        btn_frame.pack_propagate(False)
        ctk.CTkButton(btn_frame, text="🙂  FACE LOGIN", font=("Courier New", 11, "bold"),
                      fg_color="#003d55", hover_color="#005577", text_color=ACCENT,
                      corner_radius=10, command=self._face_login
                      ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(btn_frame, text="📷  REGISTER FACE", font=("Courier New", 11, "bold"),
                      fg_color="#003d55", hover_color="#005577", text_color=ACCENT,
                      corner_radius=10, command=self._register_face
                      ).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ctk.CTkButton(btn_frame, text="📁  LOAD PHOTO", font=("Courier New", 11, "bold"),
                      fg_color="#003d55", hover_color="#005577", text_color=ACCENT,
                      corner_radius=10, command=self._register_face_from_file
                      ).pack(side="right", fill="x", expand=True, padx=(6, 0))

    def _field(self, parent, label, placeholder, show=None):
        ctk.CTkLabel(parent, text=label, font=("Courier New", 9), text_color=TEXT_DIM
                     ).pack(anchor="w", padx=24, pady=(20, 4))
        e = ctk.CTkEntry(parent, fg_color=BG3, border_color=ACCENT3, text_color=TEXT,
                         font=("Courier New", 13), height=46, corner_radius=10,
                         placeholder_text=placeholder, **(dict(show=show) if show else {}))
        e.pack(padx=24, fill="x")
        e.bind("<FocusIn>", lambda ev: e.configure(border_color=ACCENT))
        e.bind("<FocusOut>", lambda ev: e.configure(border_color=ACCENT3))
        return e

    def _login(self):
        username, password = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not username or not password:
            self.error_label.configure(text="⚠  All fields required.")
            return
        if auth.verify_login(username, password):
            self.neural.stop()
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
        if not temp_file:
            return
        if auth.verify_face(username, temp_file):
            self.neural.stop()
            self.destroy()
            self.on_success()
        else:
            self.error_label.configure(text="✕  Face not recognized. Try again.")
        try:
            os.remove(temp_file)
        except Exception:
            pass

    def _register_face(self):
        username, password = self.user_entry.get().strip(), self.pass_entry.get().strip()
        if not username or not password:
            return self.error_label.configure(text="⚠  Username and password required.")
        if not auth.verify_login(username, password):
            return self.error_label.configure(text="✕  Invalid password. Cannot register face.")
        if not cv2:
            return self.error_label.configure(text="⚠  Install opencv-python to register face.")
        temp_file = self._capture_face()
        if not temp_file:
            return
        if auth.register_face(username, temp_file):
            self.error_label.configure(text="✓  Face registered successfully.")
        else:
            self.error_label.configure(text="✕  Could not save face image.")
        try:
            os.remove(temp_file)
        except Exception:
            pass

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
        if not filename:
            return
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
            for _ in range(5):
                cap.read()
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


# ── Action confirmation dialogs ───────────────────────────────────────────

class ConfirmActionWindow(ctk.CTkToplevel):
    """Dialog for manually confirming and executing a PC action."""

    def __init__(self, master, on_complete, default_action=None, default_arg=None):
        super().__init__(master)
        self.on_complete = on_complete
        self.default_action = default_action
        self.default_arg = default_arg
        self.title("AIDO — Confirm Action")
        self.geometry("420x220")
        self.configure(fg_color=BG)
        self.grab_set()
        self._build()

    def _build(self):
        self.frame = ctk.CTkFrame(self, fg_color=BG2, corner_radius=12)
        self.frame.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(self.frame, text="Select action:", text_color=TEXT_DIM).pack(anchor="w", pady=(6, 2))
        self.action_var = ctk.CTkComboBox(self.frame, values=list(pc_actions.ALLOWED_ACTIONS.keys()) if pc_actions.ALLOWED_ACTIONS else ["(no actions available)"])
        keys = list(pc_actions.ALLOWED_ACTIONS.keys())
        self.action_var.set(self.default_action if self.default_action in keys else (keys[0] if keys else ""))
        self.action_var.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(self.frame, text="Argument (optional):", text_color=TEXT_DIM).pack(anchor="w")
        self.arg_entry = ctk.CTkEntry(self.frame, placeholder_text="e.g. https://example.com or scripts/myscript.py")
        if self.default_arg:
            self.arg_entry.insert(0, self.default_arg)
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
        try:
            self.on_complete(result)
        except Exception:
            pass
        self.destroy()


class ConfirmBrowserWindow(ctk.CTkToplevel):
    """Simple confirmation dialog for opening a browser."""

    def __init__(self, master, on_complete, browser_name):
        super().__init__(master)
        self.on_complete = on_complete
        self.browser_name = browser_name
        self.title("AIDO — Confirm Browser")
        self.geometry("380x170")
        self.configure(fg_color=BG)
        self.grab_set()
        self._build()

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color=BG2, corner_radius=12)
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
        result = pc_actions.open_browser(self.browser_name, use_opera=(self.browser_name.lower() == "opera gx" or self.browser_name.lower() == "opera"))
        try:
            self.on_complete(result)
        except Exception:
            pass
        self.destroy()


# ── Code update approval window ───────────────────────────────────────────

class CodeUpdateWindow(ctk.CTkToplevel):
    """Review and approve/reject AI-proposed source code changes."""

    def __init__(self, master, filename, code, on_approved):
        super().__init__(master)
        self.filename = filename
        self.code = code
        self.on_approved = on_approved
        self.title(f"System Modification — {filename}")
        self.geometry("740x640")
        self.configure(fg_color=BG)
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

        box = ctk.CTkTextbox(self, fg_color=BG2, font=("Courier New", 12), text_color=ACCENT,
                             corner_radius=12, border_width=1, border_color=ACCENT3)
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
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.code)
            self.destroy()
            self.on_approved()
        except Exception as e:
            print(f"Failed to write file: {e}")


# ── Main application ──────────────────────────────────────────────────────

class AIDOApp(ctk.CTk):
    """Main AIDO desktop application window."""

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("A.I.D.O — Advanced Intelligence & Digital Operations")
        self.geometry("560x860")
        self.configure(fg_color=BG)
        self.minsize(440, 620)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        from brain import AIDOBrain
        self.brain = AIDOBrain()
        self.overlay = AIDOOverlay(self, color_mode="cyan")
        self.requires_wake_word = True
        self.last_active_time = 0
        self.timeout_seconds = 60
        self.is_generating = False
        self.streaming_buffer = ""
        self._msg_count = 0

        self.setup_ui()
        LoginWindow(self, on_success=self._on_login_success)

    def _on_login_success(self):
        self.deiconify()
        self.boot_sequence()

    # ── UI setup ──────────────────────────────────────────────────────────

    def setup_ui(self):
        self.neural = NeuralCanvas(self)
        self.neural.place(x=0, y=0, relwidth=1, relheight=1)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        # Header
        self.header = ctk.CTkFrame(self.container, corner_radius=0, fg_color=BG2, height=110)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        top_line = Canvas(self.header, bg=ACCENT, highlightthickness=0, height=2)
        top_line.pack(fill="x")

        header_inner = ctk.CTkFrame(self.header, fg_color="transparent")
        header_inner.pack(expand=True)

        title_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_frame.pack()
        ctk.CTkLabel(title_frame, text="A", font=("Courier New", 52, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(title_frame, text=".I.", font=("Courier New", 52, "bold"), text_color=ACCENT2).pack(side="left")
        ctk.CTkLabel(title_frame, text="D", font=("Courier New", 52, "bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(title_frame, text=".O", font=("Courier New", 52, "bold"), text_color=ACCENT2).pack(side="left")
        ctk.CTkLabel(header_inner, text="ADVANCED  INTELLIGENCE  &  DIGITAL  OPERATIONS",
                     font=("Courier New", 8), text_color=TEXT_DIM).pack()

        GlowSep(self.container, color=ACCENT).pack(fill="x")

        # Chat box
        self.chat_box = ctk.CTkTextbox(self.container, fg_color="transparent", corner_radius=0,
                                       font=("Courier New", 13), text_color=TEXT,
                                       state="disabled", wrap="word", spacing3=10, spacing1=2)
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=6)
        self.chat_box.tag_config("user", foreground="#7de8ff", justify="right")
        self.chat_box.tag_config("aido", foreground="#c8f0ff", justify="left")
        self.chat_box.tag_config("system", foreground=TEXT_DIM, justify="center")
        self.chat_box.tag_config("label_user", foreground=ACCENT2, justify="right")
        self.chat_box.tag_config("label_aido", foreground=ACCENT, justify="left")
        self.chat_box.tag_config("divider", foreground=ACCENT4, justify="center")

        GlowSep(self.container, color=ACCENT3).pack(fill="x")

        # Input bar
        self.input_frame = ctk.CTkFrame(self.container, corner_radius=0, fg_color=BG2, height=78)
        self.input_frame.pack(fill="x")
        self.input_frame.pack_propagate(False)

        ctk.CTkLabel(self.input_frame, text="▸", font=("Courier New", 16), text_color=ACCENT2
                     ).pack(side="left", padx=(14, 0))

        self.input_field = ctk.CTkEntry(self.input_frame, placeholder_text="speak to aido...",
                                        fg_color=BG3, border_color=ACCENT4, text_color=TEXT,
                                        font=("Courier New", 13), height=46, corner_radius=12)
        self.input_field.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=16)
        self.input_field.bind("<Return>", self.send_message)
        self.input_field.bind("<FocusIn>", lambda e: self.input_field.configure(border_color=ACCENT))
        self.input_field.bind("<FocusOut>", lambda e: self.input_field.configure(border_color=ACCENT4))

        self.send_btn = ctk.CTkButton(self.input_frame, text="⏎", width=46, height=46,
                                      fg_color=ACCENT4, hover_color=ACCENT3, text_color=ACCENT,
                                      font=("Helvetica", 18), corner_radius=12, border_width=1,
                                      border_color=ACCENT3, command=lambda: self.send_message(None))
        self.send_btn.pack(side="right", padx=(0, 14), pady=16)

        self.mic_btn = ctk.CTkButton(self.input_frame, text="🎤", width=46, height=46,
                                     fg_color="#0a2030", hover_color="#0a3040", text_color=ACCENT,
                                     font=("Helvetica", 14), corner_radius=12, border_width=1,
                                     border_color=ACCENT3, command=self.toggle_listen)
        self.mic_btn.pack(side="right", padx=(4, 0), pady=16)

        self.actions_btn = ctk.CTkButton(self.input_frame, text="⚙", width=46, height=46,
                                         fg_color="#0a2030", hover_color="#0a3040", text_color=ACCENT,
                                         font=("Helvetica", 14), corner_radius=12, border_width=1,
                                         border_color=ACCENT3,
                                         command=lambda: ConfirmActionWindow(self, self._on_action_result))
        self.actions_btn.pack(side="right", padx=(4, 0), pady=16)

        # Voice
        self.listening = False
        self._listen_thread = None
        self._listen_stop = threading.Event()
        self._recognizer = sr.Recognizer() if sr else None

        GlowSep(self.container, color=ACCENT3).pack(fill="x")

        # Quick actions
        self.quick_frame = ctk.CTkFrame(self.container, corner_radius=0, fg_color=BG, height=38)
        self.quick_frame.pack(fill="x")
        self.quick_frame.pack_propagate(False)

        quick_actions = [
            ("🖥  SYSTEM", "system info"),
            ("📝  NOTE", "save note: "),
            ("🧮  CALC", "calc "),
            ("🚀  APP", "open app "),
            ("📁  FILES", "list folder "),
            ("🗑  CLEAR", "__clear__"),
        ]
        for label, cmd in quick_actions:
            btn = ctk.CTkButton(self.quick_frame, text=label,
                                font=("Courier New", 9, "bold"),
                                fg_color=BG3, hover_color=BG4, text_color=TEXT_MID,
                                corner_radius=8, height=26, width=90,
                                border_width=1, border_color=ACCENT4,
                                command=lambda c=cmd: self._quick_action(c))
            btn.pack(side="left", padx=(6, 0), pady=6)

        GlowSep(self.container, color=ACCENT3).pack(fill="x")

        # Status bar
        status_bar = ctk.CTkFrame(self.container, fg_color=BG, corner_radius=0, height=26)
        status_bar.pack(fill="x")
        status_bar.pack_propagate(False)

        self.status_dot = ctk.CTkLabel(status_bar, text="◉", font=("Courier New", 9), text_color=TEXT_DIM)
        self.status_dot.pack(side="left", padx=(12, 4))
        self.status_label = ctk.CTkLabel(status_bar, text="◈  STANDBY  ◈", font=("Courier New", 9), text_color=TEXT_DIM)
        self.status_label.pack(side="left")
        ctk.CTkLabel(status_bar, text="v1.0.0  ◈  AIDO CORE",
                     font=("Courier New", 9), text_color=TEXT_DIM).pack(side="right", padx=12)

    def _set_status(self, text, color=None):
        color = color or TEXT_DIM
        self.status_label.configure(text=text, text_color=color)
        self.status_dot.configure(text_color=color)

    # ── Message handling ──────────────────────────────────────────────────

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
        self.neural.set_state("thinking")
        self.overlay.show("cyan")
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
        self.neural.set_state("online")
        self.overlay.hide()
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", "\n", "aido")
        self.chat_box.configure(state="disabled")
        self.is_generating = False
        self._set_status(f"LISTENING — Timeout in {self.timeout_seconds}s", ACCENT)
        self.input_field.configure(state="normal")
        self.input_field.focus()

    def _on_action_result(self, result_text):
        self.add_system_message(result_text)

    def on_approved_restart(self):
        self.add_system_message("System file updated. Rebooting core systems...")
        self.update()
        self.after(2000, lambda: os.execv(sys.executable, sys.argv))

    # ── Local commands ────────────────────────────────────────────────────

    def _handle_local_command(self, command: str) -> bool:
        """Handle simple commands locally without going through the AI."""
        lower = command.lower()
        if re.search(r"\b(abre|abrir|open)\b.*\b(opera gx|opera|operagx)\b", lower):
            result = pc_actions.open_browser("", use_opera=True)
            self.add_system_message(result)
            return True
        if re.search(r"\b(abre|abrir|open)\b.*\b(browser|navegador)\b", lower):
            result = pc_actions.open_browser("")
            self.add_system_message(result)
            return True
        if re.search(r"\b(abre|abrir|open)\b.*\b(explorer|file explorer|explorador)\b", lower):
            result = pc_actions.open_explorer("")
            self.add_system_message(result)
            return True
        return False

    def _quick_action(self, action: str):
        """Handle quick action button presses."""
        if action == "__clear__":
            self.clear_chat()
            return
        self.input_field.delete(0, "end")
        self.input_field.insert(0, action)
        self.input_field.focus()

    def clear_chat(self):
        """Clear the chat history."""
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        self.brain.conversation_history.clear()
        self._msg_count = 0
        self.add_system_message("Chat cleared.")

    # ── Boot sequence ─────────────────────────────────────────────────────

    def boot_sequence(self):
        try:
            self.neural.start()
            self.neural.set_state("thinking")
            self._set_status("INITIALIZING BRAIN...", ACCENT)
            self.update()
            self.brain.load_config()
            self._set_status("CONNECTING TO MEMORY CLOUD...", ACCENT)
            self.update()
            self.brain.init_memory()
            self._set_status("CONNECTING TO GROQ API...", ACCENT)
            self.update()
            self.brain.init_model()
            self.neural.set_state("online")
            self._set_status("SYSTEMS ONLINE — SAY 'AIDO' TO BEGIN", SUCCESS)
            self.add_system_message("AIDO systems online. Say 'AIDO' to activate.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.neural.set_state("standby")
            self._set_status(f"BOOT ERROR: {e}", DANGER)

    # ── Voice input ───────────────────────────────────────────────────────

    def toggle_listen(self):
        if not sr:
            self.add_system_message("Microphone support not available (install speech_recognition).")
            return
        if self.listening:
            self._listen_stop.set()
            if self._listen_thread and self._listen_thread.is_alive():
                self._listen_thread.join(timeout=2)
            self.listening = False
            self._listen_stop.clear()
            self.mic_btn.configure(fg_color="#0a2030")
            self._set_status("STANDBY", TEXT_DIM)
            self.add_system_message("Microphone disabled.")
        else:
            self.listening = True
            self.mic_btn.configure(fg_color=SUCCESS)
            self._set_status("MICROPHONE ACTIVE", ACCENT)
            self.add_system_message("Microphone enabled. Listening...")
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
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
            self.listening = False
            self.mic_btn.configure(fg_color="#0a2030")

    def _on_recognized(self, text: str):
        self.input_field.delete(0, "end")
        self.input_field.insert(0, text)
        self.send_message(None)

    # ── Send message ──────────────────────────────────────────────────────

    def send_message(self, event):
        if self.is_generating:
            return
        command = self.input_field.get().strip()
        self.input_field.delete(0, "end")
        if not command:
            return

        # Wake word check
        if self.requires_wake_word and (time.time() - self.last_active_time) > self.timeout_seconds:
            normalized = command.lower().replace("aido,", "aido").strip()
            if not (normalized.startswith("aido ") or normalized == "aido"):
                self.neural.set_state("standby")
                self._set_status("STANDBY — Say 'AIDO' to activate", DANGER)
                return
            command = normalized.replace("aido", "", 1).strip()
            if not command:
                self.add_system_message("AIDO activated. Listening...")
                self.last_active_time = time.time()
                self.requires_wake_word = False
                self.neural.set_state("online")
                return

        self.last_active_time = time.time()
        self.requires_wake_word = False

        if self._handle_local_command(command):
            return

        self.add_user_message(command)
        self.is_generating = True
        self._set_status("PROCESSING...", ACCENT2)
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
            result = launch_app(arg or "")
            self._on_action_result(result)
        else:
            self.after(0, lambda: ConfirmActionWindow(self, self._on_action_result,
                                                       default_action=action, default_arg=arg))


if __name__ == "__main__":
    app = AIDOApp()
    app.mainloop()
