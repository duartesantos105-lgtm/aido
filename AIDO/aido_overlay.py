"""Full-screen transparent overlay with animated pulsing wave borders for AIDO."""
import math
import tkinter as tk

_ACCENT  = (0, 229, 255)
_ACCENT2 = (0, 136, 187)
_PURPLE  = (123, 94, 167)
_SUCCESS = (0, 255, 170)
_DANGER  = (255, 58, 74)


def _rgb(r, g, b, a=1.0):
    """Convert (r,g,b,a) to hex colour string with alpha scaling."""
    r = max(0, min(255, int(r * a)))
    g = max(0, min(255, int(g * a)))
    b = max(0, min(255, int(b * a)))
    return f"#{r:02x}{g:02x}{b:02x}"


class AIDOOverlay:
    """
    Full-screen transparent overlay with pulsing wave borders.
    Modes: cyan (default), danger, success.
    """

    MODES = {
        "cyan":    (_ACCENT, _ACCENT2, _PURPLE),
        "danger":  (_DANGER, (200, 20, 30), (150, 0, 20)),
        "success": (_SUCCESS, (0, 180, 120), (0, 100, 80)),
    }

    def __init__(self, master, color_mode="cyan", wave_layers=5, fps=40):
        self.master = master
        self.wave_layers = wave_layers
        self.fps = fps
        self._job = None
        self._tick = 0
        self._visible = False
        self._alpha = 0.0
        self._fade_dir = 0
        self.set_mode(color_mode)
        self._build()

    # ── Public API ────────────────────────────────────────────────────────

    def show(self, mode=None):
        if mode:
            self.set_mode(mode)
        if not self._visible:
            self._visible = True
            self._fade_dir = 1
            self.win.deiconify()
            self._animate()

    def hide(self):
        if self._visible:
            self._fade_dir = -1

    def set_mode(self, mode: str):
        self.colors = self.MODES.get(mode, self.MODES["cyan"])

    def destroy(self):
        if self._job:
            self.master.after_cancel(self._job)
        self.win.destroy()

    # ── Internal ──────────────────────────────────────────────────────────

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

        self.canvas = tk.Canvas(self.win, width=sw, height=sh, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()

    def _animate(self):
        if not self._visible and self._fade_dir == 0:
            return

        fade_speed = 0.06
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
        """Render the animated wave border."""
        self.canvas.delete("all")
        t = self._tick * 0.04
        sw, sh = self._sw, self._sh
        c1, c2, _ = self.colors
        n, depth = self.wave_layers, 90

        for i in range(n):
            phase = t + i * (math.pi * 2 / n)
            i_frac = i / n
            amp = depth * (1 - i_frac) * (0.5 + 0.5 * math.sin(phase * 1.3))
            amp2 = max(0.01, amp)
            layer_alpha = self._alpha * (1.0 - i_frac * 0.75) * 0.65
            mix = (math.sin(t * 0.5 + i * 0.8) + 1) / 2
            col = _rgb(c1[0] * (1 - mix) + c2[0] * mix,
                       c1[1] * (1 - mix) + c2[1] * mix,
                       c1[2] * (1 - mix) + c2[2] * mix, layer_alpha)

            seg = 60
            pts_top, pts_bottom, pts_left, pts_right = [], [], [], []

            for s in range(seg + 1):
                frac = s / seg
                wave = amp * math.sin(frac * math.pi * 4 + phase)
                wave2 = amp * math.sin(frac * math.pi * 4 + phase + 1.0) + amp * 0.3

                x = frac * sw
                pts_top.extend([x, max(0, wave + amp * 0.3)])
                pts_bottom.extend([x, min(sh, sh - (wave2 + amp * 0.3))])

                y2 = frac * sh
                pts_left.extend([max(0, amp2 * math.sin(frac * math.pi * 4 + phase + 1.0) + amp2 * 0.3), y2])
                pts_right.extend([min(sw, sw - (amp2 * math.sin(frac * math.pi * 4 + phase + 1.0) + amp2 * 0.3)), y2])

            lw = max(0.6, 2.5 - i * 0.35)
            if len(pts_top) >= 4:
                self.canvas.create_line(pts_top, fill=col, width=lw, smooth=True)
            if len(pts_bottom) >= 4:
                self.canvas.create_line(pts_bottom, fill=col, width=lw, smooth=True)
            if len(pts_left) >= 4:
                self.canvas.create_line(pts_left, fill=col, width=lw, smooth=True)
            if len(pts_right) >= 4:
                self.canvas.create_line(pts_right, fill=col, width=lw, smooth=True)

        # Corner glows
        corner_r = 12 + 6 * math.sin(t * 2)
        glow_a = self._alpha * 0.9
        glow_col = _rgb(*c2, glow_a * 0.9)
        for cx, cy in [(0, 0), (sw, 0), (0, sh), (sw, sh)]:
            self.canvas.create_oval(cx - corner_r - 10, cy - corner_r - 10,
                                    cx + corner_r + 10, cy + corner_r + 10,
                                    outline=_rgb(*c2, glow_a * 0.4), width=1)
            self.canvas.create_oval(cx - corner_r, cy - corner_r, cx + corner_r, cy + corner_r,
                                    outline=glow_col, width=2)

        # Labels
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        self.canvas.create_text(sw // 2, 22, text="◈  A.I.D.O  CONTROL  MODE  ACTIVE  ◈",
                                fill=_rgb(*c1, self._alpha * pulse), font=("Courier New", 11, "bold"))
        self.canvas.create_text(sw // 2, sh - 18, text="SAY  'RELEASE'  TO  RETURN  CONTROL",
                                fill=_rgb(*c2, self._alpha * 0.6), font=("Courier New", 9))


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    overlay = AIDOOverlay(root, color_mode="cyan")
    overlay.show()
    root.mainloop()
