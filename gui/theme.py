# gui/theme.py
import tkinter.ttk as ttk

class Theme:
    # ─────────────────────────────────────────
    # Renkler & Stiller
    # ─────────────────────────────────────────
    BG        = "#1E1E2E"
    BG2       = "#2A2A3E"
    BG3       = "#313145"
    ACCENT    = "#ED793A"
    ACCENT2   = "#CECBD6"
    SUCCESS   = "#22C55E"
    ERROR     = "#EF4444"
    WARNING   = "#F59E0B"
    FG        = "#E2E8F0"
    FG2       = "#94A3B8"
    BORDER    = "#3F3F5F"
    EDITOR_BG = "#12121E"
    LINE_NUM  = "#4B5563"

    @classmethod
    def setup_ttk_styles(cls):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",
                        background=cls.BG2, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=cls.BG3, foreground=cls.FG2,
                        padding=[14, 6], font=("Consolas", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", cls.ACCENT)],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("TFrame", background=cls.BG)
        style.configure("Vertical.TScrollbar",
                        background=cls.BG3, troughcolor=cls.BG2,
                        arrowcolor=cls.FG2)
