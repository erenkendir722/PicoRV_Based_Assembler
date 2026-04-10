# gui/components/project_panel.py
# Proje paneli — sol kenar
#
# Dosya listesi + linker script + "Assemble & Link" butonu
# Callback'ler app.py tarafından bağlanır.

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from gui.theme import Theme
from gui.widgets import make_btn
from core import LinkerScript, LinkerScriptError


# Dosya durumunu gösteren ikonlar
_ICON = {
    'idle':    '○',
    'ok':      '●',
    'error':   '✗',
}


class ProjectPanel:
    """
    Sol kenar paneli.

    Dışa açık:
        files           → [(path, ObjectFile | None)]
        script          → LinkerScript
        on_build        → çağrıldığında app.py build tetikler
        set_file_status(idx, 'ok'|'error'|'idle')
        get_selected_path() → seçili dosyanın yolu
        get_checked_indices() → build'e girecek dosyaların index listesi
    """

    def __init__(self, parent: tk.Widget, on_build, on_file_select):
        self._on_build       = on_build
        self._on_file_select = on_file_select
        self.files: list[tuple[str, object]] = []   # [(path, ObjectFile|None)]
        self._checks: list[tk.BooleanVar] = []       # her dosya için checkbox var
        self._check_widgets: list[tk.Widget] = []    # checkbox widget referansları
        self._selected_idx: int | None = None        # tek tıklamayla seçili satır
        self.script = LinkerScript.default()

        self.frame = tk.Frame(parent, bg=Theme.BG, width=300)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)
        self.frame.pack_propagate(False)

        self._build_ui()

    # ─────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────
    def _build_ui(self):
        # Başlık
        tk.Label(self.frame, text="  Proje",
                 bg=Theme.BG2, fg=Theme.ACCENT2,
                 font=("Consolas", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X)

        # ── Dosya listesi ──
        list_outer = tk.Frame(self.frame, bg=Theme.EDITOR_BG)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # Canvas + scrollbar (checkbox listesi için)
        self._canvas = tk.Canvas(list_outer, bg=Theme.EDITOR_BG,
                                 highlightthickness=0, bd=0)
        sb = tk.Scrollbar(list_outer, orient=tk.VERTICAL,
                          command=self._canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._list_frame = tk.Frame(self._canvas, bg=Theme.EDITOR_BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")

        self._list_frame.bind("<Configure>", self._on_list_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Tüm seç / hiçbiri seçme
        sel_row = tk.Frame(self.frame, bg=Theme.BG2)
        sel_row.pack(fill=tk.X)
        make_btn(sel_row, "✔ Tümü", self._check_all,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9), padx=6, pady=3
                 ).pack(side=tk.LEFT, padx=4, pady=3)
        make_btn(sel_row, "✖ Hiçbiri", self._uncheck_all,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9), padx=6, pady=3
                 ).pack(side=tk.LEFT, padx=2, pady=3)

        # Dosya butonları
        fbtn = tk.Frame(self.frame, bg=Theme.BG2)
        fbtn.pack(fill=tk.X)
        make_btn(fbtn, "📁 Klasör Aç", self._add_folder,
                 bg=Theme.ACCENT, fg="#FFFFFF", hover_bg="#C5602A",
                 font_cfg=("Consolas", 9, "bold"), padx=8, pady=4
                 ).pack(side=tk.LEFT, padx=4, pady=4)
                 
        make_btn(fbtn, "🗑 Sil", self._remove_file,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9), padx=8, pady=4
                 ).pack(side=tk.LEFT, padx=4, pady=4)

        # app.py tarafından bağlanan callback'ler
        self.get_editor_code: callable = lambda: ""
        self.get_editor_name: callable = lambda: "editör"
        self.on_new_file_created: callable = lambda path: None
        self.on_folder_opened: callable = lambda folder: None  # app.py bağlar

        # ── Linker Script ──
        tk.Label(self.frame, text="  Linker Script",
                 bg=Theme.BG2, fg=Theme.ACCENT2,
                 font=("Consolas", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X, pady=(8, 0))

        sframe = tk.Frame(self.frame, bg=Theme.BG3)
        sframe.pack(fill=tk.X, padx=4, pady=(2, 0))

        for label, attr in [("text_base", "text_base"), ("data_base", "data_base")]:
            row = tk.Frame(sframe, bg=Theme.BG3)
            row.pack(fill=tk.X, padx=6, pady=3)
            tk.Label(row, text=f"{label}:", bg=Theme.BG3, fg=Theme.FG2,
                     font=("Consolas", 9), width=11, anchor=tk.W).pack(side=tk.LEFT)
            entry = tk.Entry(row, bg=Theme.EDITOR_BG, fg=Theme.FG,
                             font=("Consolas", 10), relief=tk.FLAT,
                             insertbackground=Theme.ACCENT2, width=13)
            entry.pack(side=tk.LEFT, padx=(4, 0))
            entry.insert(0, f"0x{getattr(self.script, attr):08X}")
            setattr(self, f"_entry_{attr}", entry)

        sbtn = tk.Frame(sframe, bg=Theme.BG3)
        sbtn.pack(fill=tk.X, padx=6, pady=(2, 6))
        make_btn(sbtn, "📂 Yükle", self._load_script,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9), padx=8, pady=3
                 ).pack(side=tk.LEFT, padx=(0, 4))
        make_btn(sbtn, "💾 Kaydet", self._save_script,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9), padx=8, pady=3
                 ).pack(side=tk.LEFT)

        # ── Build butonu ──
        make_btn(self.frame, "▶  Assemble & Link", self._on_build,
                 bg=Theme.ACCENT, fg="#FFFFFF", hover_bg="#C5602A",
                 font_cfg=("Consolas", 11, "bold"), padx=16, pady=10
                 ).pack(fill=tk.X, padx=4, pady=(10, 4))

        # Dışa aktar
        make_btn(self.frame, "💾 .mem Dışa Aktar", self._on_export_mem,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9)).pack(fill=tk.X, padx=4, pady=2)
        make_btn(self.frame, "💾 .hex Dışa Aktar", self._on_export_hex,
                 bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                 font_cfg=("Consolas", 9)).pack(fill=tk.X, padx=4, pady=2)

        # Callback referansları (app.py bağlar)
        self.export_mem_cb = None
        self.export_hex_cb = None

    # ─────────────────────────────────────────
    # Canvas scroll ayarı
    # ─────────────────────────────────────────
    def _on_list_configure(self, _=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        if event:
            self._canvas.itemconfig(self._canvas_window, width=event.width)

    # ─────────────────────────────────────────
    # Dosya listesi — iç metodlar
    # ─────────────────────────────────────────
    def _add_row(self, path: str | None, checked: bool = True) -> int:
        """Listeye yeni satır ekle, index döndür."""
        idx = len(self._check_widgets)  # widget sayısı = mevcut satır sayısı
        var = tk.BooleanVar(value=checked)
        self._checks.append(var)

        row = tk.Frame(self._list_frame, bg=Theme.EDITOR_BG, cursor="hand2")
        row.pack(fill=tk.X, padx=2, pady=1)

        cb = tk.Checkbutton(row, variable=var,
                            bg=Theme.EDITOR_BG, fg=Theme.FG,
                            selectcolor=Theme.BG3,
                            activebackground=Theme.EDITOR_BG,
                            relief=tk.FLAT, bd=0,
                            highlightthickness=0)
        cb.pack(side=tk.LEFT)

        icon_lbl = tk.Label(row, text=_ICON['idle'],
                            bg=Theme.EDITOR_BG, fg=Theme.FG2,
                            font=("Consolas", 9))
        icon_lbl.pack(side=tk.LEFT)

        name = os.path.basename(path) if path else self.get_editor_name() + "  [editör]"
        name_lbl = tk.Label(row, text=f"  {name}",
                            bg=Theme.EDITOR_BG, fg=Theme.FG,
                            font=("Consolas", 10), anchor=tk.W)
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Tıklayınca dosyayı editörde aç
        for widget in (row, icon_lbl, name_lbl, cb):
            widget.bind("<Button-1>", lambda e, i=idx: self._on_row_click(i))

        self._check_widgets.append((row, icon_lbl, name_lbl, cb))
        self._highlight_row(idx, selected=False)
        return idx

    def _on_row_click(self, idx: int):
        prev_idx = self._selected_idx
        # Önce highlight'ı değiştir
        self._selected_idx = idx
        for i in range(len(self._check_widgets)):
            self._highlight_row(i, selected=(i == idx))
        path, _ = self.files[idx]
        # Callback "hayır" dönerse eski seçime geri dön
        accepted = self._on_file_select(path)
        if accepted is False:
            self._selected_idx = prev_idx
            for i in range(len(self._check_widgets)):
                self._highlight_row(i, selected=(i == prev_idx))

    def _highlight_row(self, idx: int, selected: bool):
        if idx >= len(self._check_widgets):
            return
        row, icon_lbl, name_lbl, cb = self._check_widgets[idx]
        bg = Theme.ACCENT if selected else Theme.EDITOR_BG
        fg = "#FFFFFF" if selected else Theme.FG
        for w in (row, icon_lbl, name_lbl):
            w.config(bg=bg)
        name_lbl.config(fg=fg)
        icon_lbl.config(fg="#FFFFFF" if selected else Theme.FG2)
        cb.config(bg=bg, activebackground=bg)

    def _rebuild_list(self):
        """Tüm checkbox satırlarını yeniden çiz."""
        for w, *_ in self._check_widgets:
            w.destroy()
        self._check_widgets.clear()
        old_checks = [v.get() for v in self._checks]
        self._checks.clear()
        for i, (path, _) in enumerate(self.files):
            checked = old_checks[i] if i < len(old_checks) else True
            self._add_row(path, checked)
        # Seçimi koru
        if self._selected_idx is not None and self._selected_idx < len(self.files):
            self._highlight_row(self._selected_idx, selected=True)

    # ─────────────────────────────────────────
    # Dosya listesi — dışa açık metodlar
    # ─────────────────────────────────────────
    def add_file_entry(self, path: str | None, checked: bool = True):
        """Dışarıdan (app.py) dosya eklemek için."""
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
        """İşaretli dosyaların index listesini döndür."""
        return [i for i, var in enumerate(self._checks) if var.get()]

    def get_selected_path(self) -> str | None:
        if self._selected_idx is not None and self._selected_idx < len(self.files):
            return self.files[self._selected_idx][0]
        return None

    def select_index(self, idx: int):
        """Belirtilen index'i seçili yap (highlight)."""
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
        icon_lbl.config(text=_ICON[status])
        selected = (idx == self._selected_idx)
        if selected:
            icon_lbl.config(fg="#FFFFFF")
        else:
            color = {"ok": "#4EC9B0", "error": "#F44747", "idle": Theme.FG2}[status]
            icon_lbl.config(fg=color)

    def _row_text(self, path: str | None, status: str) -> str:
        """Geriye dönük uyumluluk için (app.py bazı yerlerde kullanıyor)."""
        if path is None:
            name = self.get_editor_name()
            return f"{_ICON[status]}  {name}  [editör]"
        return f"{_ICON[status]}  {os.path.basename(path)}"

    # ─────────────────────────────────────────
    # Linker Script
    # ─────────────────────────────────────────
    def read_script(self) -> LinkerScript | None:
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
