"""Full-screen transparent overlay with advanced animated wave borders and data-stream effects."""
import math
import random
import tkinter as tk

_ACCENT  = (0, 229, 255)
_ACCENT2 = (0, 136, 187)
_PURPLE  = (123, 94, 167)
_SUCCESS = (0, 255, 170)
_DANGER  = (255, 58, 74)

def _rgb(r, g, b, a=1.0):
    r = max(0, min(255, int(r * a)))
    g = max(0, min(255, int(g * a)))
    b = max(0, min(255, int(b * a)))
    return f"#{r:02x}{g:02x}{b:02x}"

class AIDOOverlay:
    MODES = {
        "cyan":    (_ACCENT, _ACCENT2, _PURPLE),
        "danger":  (_DANGER, (200, 20, 30), (150, 0, 20)),
        "success": (_SUCCESS, (0, 180, 120), (0, 100, 80)),
    }

    def __init__(self, master, color_mode="cyan", wave_layers=6, fps=40):
        self.master = master
        self.wave_layers = wave_layers
        self.fps = fps
        self._job = None
        self._tick = 0
        self._visible = False
        self._alpha = 0.0
        self._fade_dir = 0
        self._particles = []
        self._scanner_x = 0
        self._pulse_phase = 0
        self.set_mode(color_mode)
        self._build()

    def show(self, mode=None):
        if mode:
            self.set_mode(mode)
        if not self._visible:
            self._visible = True
            self._fade_dir = 1
            self.win.deiconify()
            self._generate_particles()
            self._animate()

    def hide(self):
        if self._visible:
            self._fade_dir = -1

    def set_mode(self, mode: str):
        self.colors = self.MODES.get(mode, self.MODES["cyan"])
        self._primary, self._secondary, self._tertiary = self.colors

    def destroy(self):
        if self._job:
            self.master.after_cancel(self._job)
        self.win.destroy()

    def _generate_particles(self):
        self._particles = []
        for _ in range(60):
            self._particles.append({
                "x": random.uniform(0, self._sw),
                "y": random.uniform(0, self._sh),
                "vx": random.uniform(-1.5, 1.5),
                "vy": random.uniform(-1.5, 1.5),
                "life": random.uniform(0.5, 1.0),
                "size": random.uniform(1, 3),
                "speed": random.uniform(0.3, 1.0),
            })

    def _build(self):
        self.win = tk.Toplevel(self.master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.0)
        self.win.configure(bg="black")
        try:
            self.win.attributes("-transparentcolor", "black")
        except tk.TclError:
            pass

        sw = self.win.winfo_screenwidth() or 540
        sh = self.win.winfo_screenheight() or 160
        self._sw, self._sh = sw, sh
        self.win.geometry(f"{sw}x{sh}+0+0")

        self.canvas = tk.Canvas(
            self.win, width=sw, height=sh, bg="black", highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()

    def _animate(self):
        if not self._visible and self._fade_dir == 0:
            return

        fade_speed = 0.05
        if self._fade_dir == 1:
            self._alpha = min(1.0, self._alpha + fade_speed)
            if self._alpha >= 1.0:
                self._fade_dir = 0
        elif self._fade_dir == -1:
            self._alpha = max(0.0, self._alpha - fade_speed)
            if self._alpha <= 0.0:
                self._visible = False
                self._fade_dir = 0
                self.win.withdraw()
                return

        self.win.attributes("-alpha", self._alpha)
        self._draw()
        self._tick += 1
        self._job = self.master.after(max(16, int(1000 / self.fps)), self._animate)

    def _draw(self):
        self.canvas.delete("all")
        t = self._tick * 0.04
        sw, sh = self._sw, self._sh
        c1, c2, c3 = self.colors
        alpha = self._alpha

        # Background gradient overlay
        for i in range(4):
            frac = i / 4
            a = alpha * 0.03 * (1 - frac)
            self.canvas.create_rectangle(
                0, sh * frac, sw, sh * (frac + 0.25),
                fill=_rgb(0, 229, 255, a), outline=""
            )

        # Wave border layers
        n, depth = self.wave_layers, 110
        for i in range(n):
            phase = t + i * (math.pi * 2 / n)
            i_frac = i / n
            amp = depth * (1 - i_frac * 0.5) * (0.5 + 0.5 * math.sin(phase * 1.3))
            amp2 = max(0.01, amp)
            layer_alpha = alpha * (1.0 - i_frac * 0.7) * 0.7
            mix = (math.sin(t * 0.5 + i * 0.8) + 1) / 2
            col = _rgb(
                c1[0] * (1 - mix) + c2[0] * mix,
                c1[1] * (1 - mix) + c2[1] * mix,
                c1[2] * (1 - mix) + c2[2] * mix,
                layer_alpha,
            )

            seg = 80
            pts_top, pts_bottom, pts_left, pts_right = [], [], [], []
            for s in range(seg + 1):
                frac = s / seg
                wave = amp * math.sin(frac * math.pi * 4 + phase)
                wave2 = amp * math.sin(frac * math.pi * 4 + phase + 1.0) + amp * 0.3
                x = frac * sw
                pts_top.extend([x, max(0, wave + amp * 0.3)])
                pts_bottom.extend([x, min(sh, sh - (wave2 + amp * 0.3))])
                y2 = frac * sh
                pts_left.extend(
                    [max(0, amp2 * math.sin(frac * math.pi * 4 + phase + 1.0) + amp2 * 0.3), y2]
                )
                pts_right.extend(
                    [
                        min(sw, sw - (amp2 * math.sin(frac * math.pi * 4 + phase + 1.0) + amp2 * 0.3)),
                        y2,
                    ]
                )

            lw = max(0.6, 2.5 - i * 0.3)
            for pts in [pts_top, pts_bottom, pts_left, pts_right]:
                if len(pts) >= 4:
                    self.canvas.create_line(pts, fill=col, width=lw, smooth=True)

        # Scanner line (sweeping horizontal scan)
        self._scanner_x = (self._scanner_x + alpha * 8) % (sw * 1.2)
        scan_alpha = alpha * 0.3 * (0.5 + 0.5 * math.sin(t * 2))
        self.canvas.create_line(
            self._scanner_x - 40, 0, self._scanner_x + 40, sh,
            fill=_rgb(*c1, scan_alpha * 0.3), width=1
        )
        self.canvas.create_line(
            self._scanner_x, 0, self._scanner_x + 2, sh,
            fill=_rgb(*c1, scan_alpha), width=1
        )

        # Corner glow accents
        self._pulse_phase += 0.05
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        corner_r = 15 + 12 * pulse
        glow_a = alpha * 0.95
        for cx, cy in [(0, 0), (sw, 0), (0, sh), (sw, sh)]:
            self.canvas.create_oval(
                cx - corner_r - 12, cy - corner_r - 12,
                cx + corner_r + 12, cy + corner_r + 12,
                outline=_rgb(*c2, glow_a * 0.5), width=1
            )
            self.canvas.create_oval(
                cx - corner_r, cy - corner_r, cx + corner_r, cy + corner_r,
                outline=_rgb(*c1, glow_a * pulse), width=2.5
            )

        # Data stream particles
        for p in self._particles:
            p["x"] += p["vx"] * p["speed"] * alpha
            p["y"] += p["vy"] * p["speed"] * alpha
            p["life"] -= 0.003 * alpha

            if p["life"] <= 0 or p["x"] < -20 or p["x"] > sw + 20 or p["y"] < -20 or p["y"] > sh + 20:
                p["x"] = random.uniform(0, sw)
                p["y"] = random.uniform(0, sh)
                p["life"] = random.uniform(0.5, 1.0)

            pa = alpha * p["life"] * 0.8
            sz = p["size"] * (0.5 + 0.5 * math.sin(t * 2 + p["x"]))
            self.canvas.create_oval(
                p["x"] - sz, p["y"] - sz, p["x"] + sz, p["y"] + sz,
                fill=_rgb(*c1, pa), outline=""
            )
            # Particle trail
            self.canvas.create_line(
                p["x"] - p["vx"] * 8, p["y"] - p["vy"] * 8,
                p["x"], p["y"],
                fill=_rgb(*c2, pa * 0.3), width=0.5
            )

        # Digital data lines (vertical rain on edges)
        if alpha > 0.3:
            for side_x in [12, sw - 12]:
                for row in range(0, sh, 22):
                    char = random.choice("01アイウエオ")
                    da = alpha * 0.2 * (0.5 + 0.5 * math.sin(t * 2 + row * 0.1))
                    self.canvas.create_text(
                        side_x, row, text=char,
                        fill=_rgb(*c1, da), font=("Courier New", 7)
                    )

        # Status labels
        pulse2 = 0.5 + 0.5 * math.sin(t * 3)
        self.canvas.create_text(
            sw // 2, 22,
            text="◈  A.I.D.O  ACTIVE  ◈",
            fill=_rgb(*c1, alpha * pulse2),
            font=("Courier New", 12, "bold"),
        )
        self.canvas.create_text(
            sw // 2, sh - 18,
            text="SYSTEM  INTEGRATION  ENGAGED",
            fill=_rgb(*c2, alpha * 0.5),
            font=("Courier New", 8),
        )


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    overlay = AIDOOverlay(root, color_mode="cyan")
    overlay.show()
    root.mainloop()
