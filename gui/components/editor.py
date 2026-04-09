import tkinter as tk
from tkinter import ttk
from gui.highlighter import Highlighter
from gui.theme import Theme
from core import Assembler
from gui.components.autocomplete import AutocompleteHelper

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

        self.autocompleter = AutocompleteHelper(self._editor, self.frame, self._on_manual_completion)
        
        # Soft-Tab & Auto-Indent Behaviors
        self._editor.bind('<Tab>', self._on_editor_tab, add='+')
        self._editor.bind('<Return>', self._on_editor_return, add='+')
        self._editor.bind('<BackSpace>', self._on_editor_backspace, add='+')

    def _on_editor_backspace(self, event):
        if self._editor.tag_ranges(tk.SEL):
            return None
            
        index = self._editor.index(tk.INSERT)
        line, col = index.split('.')
        
        if int(col) == 0:
            return None
            
        text_before = self._editor.get(f"{line}.0", index)
        # Eğer satır tamamen boşluklardan oluşuyorsa tek silmede hepsini temizle
        if text_before and text_before.strip() == "":
            self._editor.delete(f"{line}.0", index)
            self.update_line_numbers()
            self._highlighter.apply()
            return "break"
            
        # Eğer normal kod yazılıyken arkasında 4 boşluk (soft tab) varsa, tekte 4 sil
        if text_before.endswith("    "):
            self._editor.delete(f"{index} - 4 chars", index)
            self.update_line_numbers()
            self._highlighter.apply()
            return "break"
            
        return None

    def _on_editor_tab(self, event):
        self._editor.insert(tk.INSERT, "    ")
        return "break"

    def _on_editor_return(self, event):
        index = self._editor.index(tk.INSERT)
        line, _ = index.split('.')
        line_text = self._editor.get(f"{line}.0", f"{line}.end")
        
        indent = ""
        for char in line_text:
            if char in (" ", "\t"):
                indent += char
            else:
                break
                
        self._editor.insert(tk.INSERT, "\n" + indent)
        self.update_line_numbers()
        self._highlighter.apply()
        return "break"

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

    def _on_manual_completion(self):
        self.update_line_numbers()
        self._highlighter.apply()
        if self._lint_timer is not None:
            self.frame.after_cancel(self._lint_timer)
        self._lint_timer = self.frame.after(10, self._lint_code)

    def _on_key_release(self, _event=None):
        self.update_line_numbers()
        self._highlighter.apply()
        
        if self._lint_timer is not None:
            self.frame.after_cancel(self._lint_timer)
        self._lint_timer = self.frame.after(400, self._lint_code)

        if _event and _event.keysym in ('Up', 'Down', 'Return', 'Tab', 'Escape', 'Shift_L', 'Shift_R'):
            if _event.keysym == 'Escape':
                self.autocompleter.hide_popup()
            return
            
        self.autocompleter.check_autocomplete()

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
