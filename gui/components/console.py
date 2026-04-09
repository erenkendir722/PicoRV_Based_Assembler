import tkinter as tk
from tkinter import ttk
from gui.theme import Theme
from gui.widgets import make_btn

class ConsolePanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Theme.BG2, height=140)
        self.frame.pack(fill=tk.X, padx=8, pady=6)
        self.frame.pack_propagate(False)

        header = tk.Frame(self.frame, bg=Theme.BG3)
        header.pack(fill=tk.X)
        tk.Label(header, text=" 🖥  Konsol / Hatalar",
                 bg=Theme.BG3, fg=Theme.ACCENT2,
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
                 
        make_btn(header, "Temizle", self.clear,
                  bg=Theme.BG3, fg=Theme.FG2, hover_bg="#4A4A6A",
                  font_cfg=("Consolas", 9), padx=8, pady=2).pack(side=tk.RIGHT, padx=8)

        self._console = tk.Text(self.frame,
                                 bg="#0D0D1A", fg=Theme.FG,
                                 font=("Consolas", 10),
                                 relief=tk.FLAT, bd=0,
                                 padx=8, pady=4,
                                 state=tk.DISABLED,
                                 height=6)
        self._console.tag_config("error",   foreground=Theme.ERROR)
        self._console.tag_config("success", foreground=Theme.SUCCESS)
        self._console.tag_config("warning", foreground=Theme.WARNING)
        self._console.tag_config("info",    foreground=Theme.ACCENT2)

        sy = ttk.Scrollbar(self.frame, command=self._console.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.config(yscrollcommand=sy.set)
        self._console.pack(fill=tk.BOTH, expand=True)

    def log(self, msg: str, tag: str = "info"):
        self._console.config(state=tk.NORMAL)
        self._console.insert(tk.END, msg + "\n", tag)
        self._console.see(tk.END)
        self._console.config(state=tk.DISABLED)

    def clear(self):
        self._console.config(state=tk.NORMAL)
        self._console.delete("1.0", tk.END)
        self._console.config(state=tk.DISABLED)
