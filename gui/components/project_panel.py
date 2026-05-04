# gui/components/project_panel.py
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from gui.theme import Theme
from gui.widgets import make_btn
from core import LinkerScript, LinkerScriptError


_ICON = {
    'idle':  '·',
    'ok':    '✓',
    'error': '✗',
}
_ICON_COLOR = {
    'idle':  Theme.FG3,
    'ok':    Theme.GREEN,
    'error': Theme.RED,
}


class ProjectPanel:
    def __init__(self, parent: tk.Widget, on_build, on_file_select):
        self._on_build       = on_build
        self._on_file_select = on_file_select
        self.files: list[tuple[str, object]] = []
        self._checks: list[tk.BooleanVar]    = []
        self._check_widgets: list[tk.Widget] = []
        self._selected_idx: int | None       = None
        self.script = LinkerScript.default()

        self.frame = tk.Frame(parent, bg=Theme.BG2, width=240)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)
        self.frame.pack_propagate(False)

        # İnce sağ kenarlık
        tk.Frame(parent, bg=Theme.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        self._build_ui()

    def _build_ui(self):
        # ── EXPLORER başlığı ──
        hdr = tk.Frame(self.frame, bg=Theme.BG2, height=36)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  EXPLORER",
                 bg=Theme.BG2, fg=Theme.FG2,
                 font=("Segoe UI", 8, "bold"),
                 anchor=tk.W).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Klasör aç ikonu (sağda)
        make_btn(hdr, "＋", self._add_folder,
                 bg=Theme.BG2, fg=Theme.FG2, hover_bg=Theme.BG3,
                 font_cfg=("Segoe UI", 13), padx=6, pady=0
                 ).pack(side=tk.RIGHT, padx=4, pady=4)

        tk.Frame(self.frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # ── Dosya listesi ──
        list_outer = tk.Frame(self.frame, bg=Theme.BG2)
        list_outer.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(list_outer, bg=Theme.BG2,
                                  highlightthickness=0, bd=0)
        sb = tk.Scrollbar(list_outer, orient=tk.VERTICAL,
                           command=self._canvas.yview, width=6)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._list_frame = tk.Frame(self._canvas, bg=Theme.BG2)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")

        self._list_frame.bind("<Configure>", self._on_list_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        tk.Frame(self.frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # ── Tümü / Hiçbiri ──
        sel_row = tk.Frame(self.frame, bg=Theme.BG2)
        sel_row.pack(fill=tk.X, padx=6, pady=4)
        make_btn(sel_row, "Tümünü Seç", self._check_all,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg=Theme.BORDER,
                 font_cfg=("Segoe UI", 8), padx=8, pady=3
                 ).pack(side=tk.LEFT, padx=(0, 4))
        make_btn(sel_row, "Temizle", self._uncheck_all,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg=Theme.BORDER,
                 font_cfg=("Segoe UI", 8), padx=8, pady=3
                 ).pack(side=tk.LEFT)
        make_btn(sel_row, "🗑", self._remove_file,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg="#3D1A1A",
                 font_cfg=("Segoe UI", 10), padx=6, pady=2
                 ).pack(side=tk.RIGHT)

        tk.Frame(self.frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # app.py tarafından bağlanan callback'ler
        self.get_editor_code: callable = lambda: ""
        self.get_editor_name: callable = lambda: "editör"
        self.on_new_file_created: callable = lambda path: None
        self.on_folder_opened: callable = lambda folder: None

        # ── Linker Script ──
        ls_hdr = tk.Frame(self.frame, bg=Theme.BG2, height=30)
        ls_hdr.pack(fill=tk.X)
        ls_hdr.pack_propagate(False)
        tk.Label(ls_hdr, text="  LINKER SCRIPT",
                 bg=Theme.BG2, fg=Theme.FG2,
                 font=("Segoe UI", 8, "bold"),
                 anchor=tk.W).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        tk.Frame(self.frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        sframe = tk.Frame(self.frame, bg=Theme.BG2)
        sframe.pack(fill=tk.X, padx=8, pady=6)

        for lbl_text, attr in [("text_base", "text_base"), ("data_base", "data_base")]:
            row = tk.Frame(sframe, bg=Theme.BG2)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=lbl_text,
                     bg=Theme.BG2, fg=Theme.FG3,
                     font=("Segoe UI", 8), width=10, anchor=tk.W
                     ).pack(side=tk.LEFT)
            entry = tk.Entry(row,
                             bg=Theme.BG3, fg=Theme.FG,
                             font=("Consolas", 9),
                             relief=tk.FLAT, bd=0,
                             insertbackground=Theme.ACCENT2,
                             highlightthickness=1,
                             highlightbackground=Theme.BORDER,
                             highlightcolor=Theme.ACCENT,
                             width=13)
            entry.pack(side=tk.LEFT, padx=(4, 0), ipady=3)
            entry.insert(0, f"0x{getattr(self.script, attr):08X}")
            setattr(self, f"_entry_{attr}", entry)

        sbtn = tk.Frame(sframe, bg=Theme.BG2)
        sbtn.pack(fill=tk.X, pady=(4, 0))
        make_btn(sbtn, "Yükle", self._load_script,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg=Theme.BORDER,
                 font_cfg=("Segoe UI", 8), padx=10, pady=3
                 ).pack(side=tk.LEFT, padx=(0, 4))
        make_btn(sbtn, "Kaydet", self._save_script,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg=Theme.BORDER,
                 font_cfg=("Segoe UI", 8), padx=10, pady=3
                 ).pack(side=tk.LEFT)

        tk.Frame(self.frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # ── Build butonu ──
        build_wrap = tk.Frame(self.frame, bg=Theme.BG2)
        build_wrap.pack(fill=tk.X, padx=8, pady=8)
        make_btn(build_wrap, "▶  Build",
                 self._on_build,
                 bg=Theme.ACCENT, fg="#FFFFFF", hover_bg=Theme.ACCENT_H,
                 font_cfg=("Segoe UI", 10, "bold"), padx=16, pady=8
                 ).pack(fill=tk.X)

        # ── Dışa aktarma ──
        exp_frame = tk.Frame(self.frame, bg=Theme.BG2)
        exp_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        make_btn(exp_frame, "Dışa Aktar  .mem",
                 self._on_export_mem,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg=Theme.BORDER,
                 font_cfg=("Segoe UI", 8), padx=8, pady=4
                 ).pack(fill=tk.X, pady=(0, 3))
        make_btn(exp_frame, "Dışa Aktar  .hex",
                 self._on_export_hex,
                 bg=Theme.BG3, fg=Theme.FG2, hover_bg=Theme.BORDER,
                 font_cfg=("Segoe UI", 8), padx=8, pady=4
                 ).pack(fill=tk.X)

        self.export_mem_cb = None
        self.export_hex_cb = None

    # ── Canvas scroll ──────────────────────────────────────────────
    def _on_list_configure(self, _=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        if event:
            self._canvas.itemconfig(self._canvas_window, width=event.width)

    # ── Dosya listesi ──────────────────────────────────────────────
    def _add_row(self, path: str | None, checked: bool = True) -> int:
        idx = len(self._check_widgets)
        var = tk.BooleanVar(value=checked)
        self._checks.append(var)

        row = tk.Frame(self._list_frame, bg=Theme.BG2, cursor="hand2", height=28)
        row.pack(fill=tk.X)
        row.pack_propagate(False)

        cb = tk.Checkbutton(row, variable=var,
                             bg=Theme.BG2, fg=Theme.FG,
                             selectcolor=Theme.ACCENT,
                             activebackground=Theme.BG2,
                             activeforeground=Theme.FG,
                             relief=tk.FLAT, bd=0,
                             highlightthickness=0,
                             cursor="hand2")
        cb.pack(side=tk.LEFT, padx=(6, 0))

        icon_lbl = tk.Label(row, text=_ICON['idle'],
                             bg=Theme.BG2, fg=Theme.FG3,
                             font=("Consolas", 9))
        icon_lbl.pack(side=tk.LEFT, padx=(2, 0))

        name = os.path.basename(path) if path else (self.get_editor_name() + "  [editör]")
        name_lbl = tk.Label(row, text=f" {name}",
                             bg=Theme.BG2, fg=Theme.FG,
                             font=("Segoe UI", 9), anchor=tk.W)
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        for widget in (row, icon_lbl, name_lbl):
            widget.bind("<Button-1>", lambda e, i=idx: self._on_row_click(i))

        self._check_widgets.append((row, icon_lbl, name_lbl, cb))
        self._highlight_row(idx, selected=False)
        return idx

    def _on_row_click(self, idx: int):
        prev_idx = self._selected_idx
        self._selected_idx = idx
        for i in range(len(self._check_widgets)):
            self._highlight_row(i, selected=(i == idx))
        path, _ = self.files[idx]
        accepted = self._on_file_select(path)
        if accepted is False:
            self._selected_idx = prev_idx
            for i in range(len(self._check_widgets)):
                self._highlight_row(i, selected=(i == prev_idx))

    def _highlight_row(self, idx: int, selected: bool):
        if idx >= len(self._check_widgets):
            return
        row, icon_lbl, name_lbl, cb = self._check_widgets[idx]
        bg = Theme.BG3 if selected else Theme.BG2
        fg = Theme.FG  if selected else Theme.FG
        for w in (row, icon_lbl, name_lbl):
            w.config(bg=bg)
        name_lbl.config(fg=Theme.ACCENT2 if selected else Theme.FG)
        cb.config(bg=bg, activebackground=bg)

    def _rebuild_list(self):
        for w, *_ in self._check_widgets:
            w.destroy()
        self._check_widgets.clear()
        old_checks = [v.get() for v in self._checks]
        self._checks.clear()
        for i, (path, _) in enumerate(self.files):
            checked = old_checks[i] if i < len(old_checks) else True
            self._add_row(path, checked)
        if self._selected_idx is not None and self._selected_idx < len(self.files):
            self._highlight_row(self._selected_idx, selected=True)

    # ── Dışa açık metodlar ─────────────────────────────────────────
    def add_file_entry(self, path: str | None, checked: bool = True):
        self.files.append((path, None))
        self._add_row(path, checked)

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Klasör Seç")
        if not folder:
            return
        self.on_folder_opened(folder)
        import glob as _glob
        asm_files = sorted(
            _glob.glob(os.path.join(folder, "*.asm")) +
            _glob.glob(os.path.join(folder, "*.s"))
        )
        for path in asm_files:
            if any(p == path for p, _ in self.files):
                continue
            self.files.append((path, None))
            self._add_row(path, checked=True)

    def _remove_file(self):
        if self._selected_idx is None:
            return
        idx = self._selected_idx
        if idx >= len(self.files):
            return
        path, _ = self.files[idx]
        if not messagebox.askyesno("Sil", f"{os.path.basename(path)} silinsin mi?"):
            return
        try:
            os.remove(path)
        except OSError as e:
            messagebox.showerror("Hata", str(e))
            return
        self.files.pop(idx)
        self._checks.pop(idx)
        self._selected_idx = None
        self._rebuild_list()

    def _check_all(self):
        for var in self._checks:
            var.set(True)

    def _uncheck_all(self):
        for var in self._checks:
            var.set(False)

    def get_checked_indices(self) -> list[int]:
        return [i for i, var in enumerate(self._checks) if var.get()]

    def get_selected_path(self) -> str | None:
        if self._selected_idx is not None and self._selected_idx < len(self.files):
            return self.files[self._selected_idx][0]
        return None

    def select_index(self, idx: int):
        if idx < 0 or idx >= len(self.files):
            return
        self._selected_idx = idx
        for i in range(len(self._check_widgets)):
            self._highlight_row(i, selected=(i == idx))
        self._canvas.yview_moveto(idx / max(len(self.files), 1))

    def set_file_object(self, idx: int, obj):
        path = self.files[idx][0]
        self.files[idx] = (path, obj)

    def set_file_status(self, idx: int, status: str):
        if idx >= len(self._check_widgets):
            return
        _, icon_lbl, _, _ = self._check_widgets[idx]
        selected = (idx == self._selected_idx)
        icon_lbl.config(text=_ICON[status])
        icon_lbl.config(fg="#FFFFFF" if selected else _ICON_COLOR[status])

    def _row_text(self, path, status):
        if path is None:
            return f"{_ICON[status]}  {self.get_editor_name()}  [editör]"
        return f"{_ICON[status]}  {os.path.basename(path)}"

    # ── Linker Script ──────────────────────────────────────────────
    def read_script(self):
        raw_text = self._entry_text_base.get().strip()
        raw_data = self._entry_data_base.get().strip()
        try:
            self.script = LinkerScript.from_string(
                f"MEMORY {{ text_base={raw_text}; data_base={raw_data}; }}")
            return self.script
        except LinkerScriptError as e:
            return None, str(e)

    def _load_script(self):
        path = filedialog.askopenfilename(
            title="Linker Script Aç",
            filetypes=[("Linker Script", "*.ld"), ("Tümü", "*.*")])
        if not path:
            return
        try:
            self.script = LinkerScript.from_file(path)
            self._entry_text_base.delete(0, tk.END)
            self._entry_text_base.insert(0, f"0x{self.script.text_base:08X}")
            self._entry_data_base.delete(0, tk.END)
            self._entry_data_base.insert(0, f"0x{self.script.data_base:08X}")
        except LinkerScriptError:
            pass

    def _save_script(self):
        result = self.read_script()
        if isinstance(result, tuple):
            return
        path = filedialog.asksaveasfilename(
            title="Linker Script Kaydet",
            defaultextension=".ld",
            filetypes=[("Linker Script", "*.ld"), ("Tümü", "*.*")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.script.to_string())

    def _on_export_mem(self):
        if self.export_mem_cb:
            self.export_mem_cb()

    def _on_export_hex(self):
        if self.export_hex_cb:
            self.export_hex_cb()
