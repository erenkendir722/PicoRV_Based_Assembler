import tkinter as tk
from tkinter import ttk
from gui.highlighter import Highlighter
from gui.theme import Theme
from core import Assembler

class EditorPanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(self.frame, text=" Assembly Kodu",
                 bg=Theme.BG2, fg=Theme.ACCENT2,
                 font=("Consolas", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X)

        edit_frame = tk.Frame(self.frame, bg=Theme.EDITOR_BG)
        edit_frame.pack(fill=tk.BOTH, expand=True)

        self._line_nums = tk.Text(edit_frame,
                                   width=4, state=tk.DISABLED,
                                   bg=Theme.BG2, fg=Theme.LINE_NUM,
                                   font=("Consolas", 11),
                                   relief=tk.FLAT, bd=0,
                                   padx=4, pady=6,
                                   selectbackground=Theme.BG2)
        self._line_nums.pack(side=tk.LEFT, fill=tk.Y)

        self._editor = tk.Text(edit_frame,
                                bg=Theme.EDITOR_BG, fg=Theme.FG,
                                font=("Consolas", 11),
                                insertbackground=Theme.ACCENT2,
                                relief=tk.FLAT, bd=0,
                                padx=8, pady=6,
                                undo=True,
                                selectbackground=Theme.ACCENT,
                                wrap=tk.NONE)
        self._editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(edit_frame, command=self._sync_scroll)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._editor.config(yscrollcommand=scroll_y.set)
        self._line_nums.config(yscrollcommand=scroll_y.set)

        scroll_x = tk.Scrollbar(self.frame, orient=tk.HORIZONTAL,
                                 command=self._editor.xview,
                                 bg=Theme.BG3)
        scroll_x.pack(fill=tk.X)
        self._editor.config(xscrollcommand=scroll_x.set)

        self._highlighter = Highlighter(self._editor)
        self._editor.tag_configure("error", underline=True, underlinefg="red", background="#4a1c1c")

        self._lint_timer = None

        self._editor.bind('<KeyRelease>', self._on_key_release)
        self._editor.bind('<MouseWheel>', self._on_mousewheel)

    def get_code(self):
        return self._editor.get("1.0", tk.END)

    def set_code(self, content):
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", content)
        self.update_line_numbers()
        self._highlighter.apply()
        
    def clear(self):
        self._editor.delete("1.0", tk.END)
        self.update_line_numbers()

    def _on_key_release(self, _event=None):
        self.update_line_numbers()
        self._highlighter.apply()
        
        if self._lint_timer is not None:
            self.frame.after_cancel(self._lint_timer)
        self._lint_timer = self.frame.after(400, self._lint_code)

    def _lint_code(self):
        source = self.get_code()
        self._editor.tag_remove("error", "1.0", tk.END)
        if not source.strip():
            return
            
        asm = Assembler()
        asm.assemble(source)
        for err in asm.errors:
            if err.startswith("Satır "):
                parts = err.split(":", 1)
                try:
                    line_no = int(parts[0].replace("Satır ", "").strip())
                    self._editor.tag_add("error", f"{line_no}.0", f"{line_no}.end")
                except ValueError:
                    pass

    def _sync_scroll(self, *args):
        self._editor.yview(*args)
        self._line_nums.yview(*args)

    def _on_mousewheel(self, event):
        units = int(-1 * (event.delta / 120))
        # Handle platform-specific scrolling correctly
        if hasattr(event, 'delta') and event.delta != 0:
            self._editor.yview_scroll(units, "units")
            self._line_nums.yview_scroll(units, "units")

    def update_line_numbers(self, event=None):
        content = self._editor.get("1.0", tk.END)
        count = content.count('\n')
        nums = "\n".join(str(i) for i in range(1, count + 1))
        self._line_nums.config(state=tk.NORMAL)
        self._line_nums.delete("1.0", tk.END)
        self._line_nums.insert("1.0", nums)
        self._line_nums.config(state=tk.DISABLED)
