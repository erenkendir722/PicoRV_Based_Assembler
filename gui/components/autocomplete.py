import re
import tkinter as tk
from gui.theme import Theme
from core.opcode_table import OPTAB, REGISTERS, DIRECTIVES

class AutocompleteHelper:
    def __init__(self, editor: tk.Text, parent_frame: tk.Frame, on_completion_inserted=None):
        self._editor = editor
        self.frame = parent_frame
        self.on_completion_inserted = on_completion_inserted
        
        self.vocab = sorted(list(OPTAB.keys()) + list(REGISTERS.keys()) + list(DIRECTIVES))
        self.vocab = [v.lower() for v in self.vocab]
        
        self._popup_win = tk.Toplevel(self.frame)
        self._popup_win.wm_overrideredirect(True)
        self._popup_win.attributes("-topmost", True)
        self._popup_win.withdraw()
        
        self._popup = tk.Listbox(self._popup_win, bg=Theme.BG2, fg=Theme.FG,
                                 font=("Consolas", 11), selectbackground=Theme.ACCENT,
                                 activestyle="none", borderwidth=1, relief=tk.SOLID)
        self._popup.pack(fill=tk.BOTH, expand=True)
        self._popup_visible = False
        self._current_word_len = 0
        
        # We use add='+' to ensure we do not overwrite other potential bindings
        self._editor.bind('<Up>', self._on_up)
        self._editor.bind('<Down>', self._on_down)
        self._editor.bind('<Tab>', self._on_tab)
        self._editor.bind('<Return>', self._on_return)
        self._editor.bind('<Button-1>', self.hide_popup, add='+')
        self._popup.bind('<ButtonRelease-1>', self._on_popup_click)

    def check_autocomplete(self):
        index = self._editor.index(tk.INSERT)
        line, col = map(int, index.split('.'))
        
        line_text = self._editor.get(f"{line}.0", f"{line}.{col}")
        match = re.search(r'[\w\.]+$', line_text)
        
        if not match:
            self.hide_popup()
            return

        current_word = match.group(0).lower()
        if len(current_word) == 0:
            self.hide_popup()
            return
            
        suggestions = [w for w in self.vocab if w.startswith(current_word) and w != current_word]
        
        if suggestions:
            self._show_popup(suggestions, current_word)
        else:
            self.hide_popup()

    def _show_popup(self, suggestions, current_word):
        self._popup.delete(0, tk.END)
        for s in suggestions[:8]:
            self._popup.insert(tk.END, s)
            
        self._popup.config(height=min(len(suggestions), 8))
        self._popup.selection_set(0)
        self._popup_visible = True
        self._current_word_len = len(current_word)
        
        bbox = self._editor.bbox("insert")
        if bbox:
            x, y, width, height = bbox
            x += self._editor.winfo_rootx()
            y += self._editor.winfo_rooty() + height
            self._popup_win.geometry(f"+{x}+{y}")
            self._popup_win.deiconify()
            self._popup_win.lift()
            
    def hide_popup(self, _event=None):
        if self._popup_visible:
            self._popup_win.withdraw()
            self._popup.delete(0, tk.END)
            self._popup_visible = False

    def _on_up(self, event):
        if self._popup_visible:
            sel = self._popup.curselection()
            if sel:
                index = sel[0]
                if index > 0:
                    self._popup.selection_clear(0, tk.END)
                    self._popup.selection_set(index - 1)
                    self._popup.see(index - 1)
            return "break"

    def _on_down(self, event):
        if self._popup_visible:
            sel = self._popup.curselection()
            if sel:
                index = sel[0]
                if index < self._popup.size() - 1:
                    self._popup.selection_clear(0, tk.END)
                    self._popup.selection_set(index + 1)
                    self._popup.see(index + 1)
            return "break"
            
    def _on_tab(self, event):
        if self._popup_visible:
            self._insert_completion()
            return "break"
            
    def _on_return(self, event):
        if self._popup_visible:
            self._insert_completion()
            return "break"
            
    def _on_popup_click(self, event):
        self._insert_completion()
        self._editor.focus_set()

    def _insert_completion(self):
        sel = self._popup.curselection()
        if not sel:
            return
            
        word = self._popup.get(sel[0])
        index = self._editor.index(tk.INSERT)
        start_index = f"{index} - {self._current_word_len} chars"
        self._editor.delete(start_index, index)
        self._editor.insert(tk.INSERT, word)
        
        self.hide_popup()
        if self.on_completion_inserted:
            self.on_completion_inserted()
