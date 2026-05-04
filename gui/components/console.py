import tkinter as tk
from tkinter import ttk
from gui.theme import Theme
from gui.widgets import make_btn


class ConsolePanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Theme.BG, height=150)
        self.frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.frame.pack_propagate(False)

        # İnce üst kenarlık
        tk.Frame(self.frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # Başlık çubuğu
        header = tk.Frame(self.frame, bg=Theme.BG2, height=30)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="  TERMINAL",
                 bg=Theme.BG2, fg=Theme.FG2,
                 font=("Segoe UI", 8, "bold"),
                 anchor=tk.W).pack(side=tk.LEFT, padx=10)

        make_btn(header, "Temizle", self.clear,
                 bg=Theme.BG2, fg=Theme.FG2, hover_bg=Theme.BG3,
                 font_cfg=("Segoe UI", 8), padx=8, pady=2
                 ).pack(side=tk.RIGHT, padx=6, pady=4)

        # Konsol metni
        self._console = tk.Text(
            self.frame,
            bg=Theme.EDITOR_BG, fg=Theme.FG,
            font=("Cascadia Code", 10) if self._font_exists("Cascadia Code")
                 else ("Consolas", 10),
            relief=tk.FLAT, bd=0,
            padx=12, pady=6,
            state=tk.DISABLED,
        )
        self._console.tag_config("error",   foreground=Theme.RED)
        self._console.tag_config("success", foreground=Theme.GREEN)
        self._console.tag_config("warning", foreground=Theme.YELLOW)
        self._console.tag_config("info",    foreground=Theme.FG2)
        self._console.tag_config("dim",     foreground=Theme.FG3)

        sy = ttk.Scrollbar(self.frame, command=self._console.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.config(yscrollcommand=sy.set)
        self._console.pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _font_exists(name: str) -> bool:
        try:
            import tkinter.font as tkfont
            return name in tkfont.families()
        except Exception:
            return False

    def log(self, msg: str, tag: str = "info"):
        self._console.config(state=tk.NORMAL)
        self._console.insert(tk.END, msg + "\n", tag)
        self._console.see(tk.END)
        self._console.config(state=tk.DISABLED)

    def clear(self):
        self._console.config(state=tk.NORMAL)
        self._console.delete("1.0", tk.END)
        self._console.config(state=tk.DISABLED)
