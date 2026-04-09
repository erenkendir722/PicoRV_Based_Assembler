import tkinter as tk
from tkinter import ttk
from gui.theme import Theme


class OutputTabsPanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(self.frame)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._tab_hex     = self._make_tab("🔢 Hex")
        self._tab_listing = self._make_tab("📄 Listing")
        self._tab_symtab  = self._make_tab("🔖 Semboller")
        self._tab_object  = self._make_tab("📦 Object")
        self._tab_map     = self._make_tab("🗺  Link Map")
        self._tab_mem     = self._make_tab("🔲 .mem")

    def _make_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self._notebook, bg=Theme.BG)
        self._notebook.add(frame, text=title)

        text = tk.Text(frame,
                       bg=Theme.EDITOR_BG, fg=Theme.FG,
                       font=("Consolas", 10),
                       relief=tk.FLAT, bd=0,
                       padx=10, pady=8,
                       state=tk.DISABLED,
                       selectbackground=Theme.ACCENT,
                       wrap=tk.NONE)
        sy = ttk.Scrollbar(frame, command=text.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = tk.Scrollbar(frame, orient=tk.HORIZONTAL,
                          command=text.xview, bg=Theme.BG3)
        sx.pack(side=tk.BOTTOM, fill=tk.X)
        text.config(yscrollcommand=sy.set, xscrollcommand=sx.set)
        text.pack(fill=tk.BOTH, expand=True)
        return text

    def set_content(self, hex_out="", listing_out="", symtab_out="",
                    object_out="", map_out="", mem_out=""):
        self._set_text(self._tab_hex,     hex_out)
        self._set_text(self._tab_listing, listing_out)
        self._set_text(self._tab_symtab,  symtab_out)
        self._set_text(self._tab_object,  object_out)
        self._set_text(self._tab_map,     map_out)
        self._set_text(self._tab_mem,     mem_out)

    def show_tab(self, name: str):
        """'hex' | 'listing' | 'symtab' | 'object' | 'map' | 'mem'"""
        tabs = {'hex': 0, 'listing': 1, 'symtab': 2,
                'object': 3, 'map': 4, 'mem': 5}
        if name in tabs:
            self._notebook.select(tabs[name])

    def clear(self):
        self.set_content()

    def _set_text(self, widget: tk.Text, content: str):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state=tk.DISABLED)
