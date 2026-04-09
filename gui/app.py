# gui.py
# RV32I Assembler - Tkinter GUI

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from core import Assembler
from .highlighter import Highlighter


def _make_btn(parent, text, command, bg, fg, hover_bg, font_cfg, padx=14, pady=6):
    """macOS'ta tk.Button renkleri çalışmadığı için Label tabanlı custom buton."""
    frame = tk.Frame(parent, bg=bg, cursor="hand2")
    lbl = tk.Label(frame, text=text, bg=bg, fg=fg,
                   font=font_cfg, padx=padx, pady=pady, cursor="hand2")
    lbl.pack()

    def on_enter(_):
        frame.config(bg=hover_bg)
        lbl.config(bg=hover_bg)

    def on_leave(_):
        frame.config(bg=bg)
        lbl.config(bg=bg)

    def on_click(_):
        command()

    for widget in (frame, lbl):
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        widget.bind("<Button-1>", on_click)

    return frame


class RV32IAssemblerGUI:

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

    def __init__(self, root: tk.Tk):
        self.root = root
        self.assembler = Assembler()
        self._current_file = None

        self._setup_window()
        self._build_ui()
        self._insert_sample()

    # ─────────────────────────────────────────
    # Pencere ayarları
    # ─────────────────────────────────────────
    def _setup_window(self):
        self.root.title("RV32I Assembler  —  PicoRV")
        self.root.configure(bg=self.BG)
        self.root.geometry("1300x820")
        self.root.minsize(900, 600)

        # ttk stili
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",
                        background=self.BG2, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=self.BG3, foreground=self.FG2,
                        padding=[14, 6], font=("Consolas", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", self.ACCENT)],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("TFrame", background=self.BG)
        style.configure("Vertical.TScrollbar",
                        background=self.BG3, troughcolor=self.BG2,
                        arrowcolor=self.FG2)

    # ─────────────────────────────────────────
    # Arayüz bileşenleri
    # ─────────────────────────────────────────
    def _build_ui(self):
        # ── Başlık ──
        header = tk.Frame(self.root, bg=self.ACCENT, height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header,
                 text="    RV32I Assembler  |  PicoRV Alt Kümesi",
                 bg=self.ACCENT, fg="#FFFFFF",
                 font=("Consolas", 13, "bold")).pack(side=tk.LEFT, padx=10)

        # ── Araç çubuğu ──
        toolbar = tk.Frame(self.root, bg=self.BG2, height=48)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        self._btn_assemble = _make_btn(
            toolbar, "▶  Assemble", self._on_assemble,
            bg=self.ACCENT, fg="#FFFFFF", hover_bg="#C5602A",
            font_cfg=("Consolas", 10, "bold"), padx=16, pady=6)
        self._btn_assemble.pack(side=tk.LEFT, padx=(10, 4), pady=8)

        for text, cmd in [
            ("📂 Aç",       self._open_file),
            ("💾 Kaydet",   self._save_file),
            ("🗑  Temizle", self._clear_all),
            ("📋 Örnek Kod", self._insert_sample),
        ]:
            _make_btn(toolbar, text, cmd,
                      bg=self.BG3, fg=self.FG, hover_bg="#4A4A6A",
                      font_cfg=("Consolas", 10)).pack(side=tk.LEFT, padx=4, pady=8)

        # Sağda bilgi etiketi
        self._status_lbl = tk.Label(toolbar, text="Hazır",
                                    bg=self.BG2, fg=self.FG2,
                                    font=("Consolas", 10))
        self._status_lbl.pack(side=tk.RIGHT, padx=16)

        # ── Ana içerik: sol + sağ ──
        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))

        # Sol: Editör
        self._build_editor(content)

        # Ayırıcı
        tk.Frame(content, bg=self.BORDER, width=2).pack(
            side=tk.LEFT, fill=tk.Y, padx=4)

        # Sağ: Çıktı sekmeleri
        self._build_output(content)

        # ── Alt: Hata/Uyarı paneli ──
        self._build_console()

    # ─────────────────────────────────────────
    # Sol panel: Assembly editörü
    # ─────────────────────────────────────────
    def _build_editor(self, parent):
        frame = tk.Frame(parent, bg=self.BG)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(frame, text=" Assembly Kodu",
                 bg=self.BG2, fg=self.ACCENT2,
                 font=("Consolas", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X)

        edit_frame = tk.Frame(frame, bg=self.EDITOR_BG)
        edit_frame.pack(fill=tk.BOTH, expand=True)

        # Satır numaraları
        self._line_nums = tk.Text(edit_frame,
                                   width=4, state=tk.DISABLED,
                                   bg=self.BG2, fg=self.LINE_NUM,
                                   font=("Consolas", 11),
                                   relief=tk.FLAT, bd=0,
                                   padx=4, pady=6,
                                   selectbackground=self.BG2)
        self._line_nums.pack(side=tk.LEFT, fill=tk.Y)

        # Editör
        self._editor = tk.Text(edit_frame,
                                bg=self.EDITOR_BG, fg=self.FG,
                                font=("Consolas", 11),
                                insertbackground=self.ACCENT2,
                                relief=tk.FLAT, bd=0,
                                padx=8, pady=6,
                                undo=True,
                                selectbackground=self.ACCENT,
                                wrap=tk.NONE)
        self._editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(edit_frame, command=self._sync_scroll)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._editor.config(yscrollcommand=scroll_y.set)
        self._line_nums.config(yscrollcommand=scroll_y.set)

        scroll_x = tk.Scrollbar(frame, orient=tk.HORIZONTAL,
                                 command=self._editor.xview,
                                 bg=self.BG3)
        scroll_x.pack(fill=tk.X)
        self._editor.config(xscrollcommand=scroll_x.set)

        self._highlighter = Highlighter(self._editor)

        self._editor.bind('<KeyRelease>', self._on_key_release)
        self._editor.bind('<MouseWheel>', self._on_mousewheel)

    def _on_key_release(self, _event=None):
        self._update_line_numbers()
        self._highlighter.apply()

    def _sync_scroll(self, *args):
        self._editor.yview(*args)
        self._line_nums.yview(*args)

    def _on_mousewheel(self, event):
        units = int(-1 * (event.delta / 120))
        self._editor.yview_scroll(units, "units")
        self._line_nums.yview_scroll(units, "units")

    def _update_line_numbers(self, event=None):
        content = self._editor.get("1.0", tk.END)
        count = content.count('\n')
        nums = "\n".join(str(i) for i in range(1, count + 1))
        self._line_nums.config(state=tk.NORMAL)
        self._line_nums.delete("1.0", tk.END)
        self._line_nums.insert("1.0", nums)
        self._line_nums.config(state=tk.DISABLED)

    # ─────────────────────────────────────────
    # Sağ panel: Çıktı sekmeleri
    # ─────────────────────────────────────────
    def _build_output(self, parent):
        frame = tk.Frame(parent, bg=self.BG)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(frame)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # Sekme 1: Hex Output
        self._tab_hex = self._make_tab("🔢 Hex Çıktı")
        # Sekme 2: Listing
        self._tab_listing = self._make_tab("📄 Listing")
        # Sekme 3: Symbol Table
        self._tab_symtab = self._make_tab("🔖 Sembol Tablosu")
        # Sekme 4: H/T/E Object
        self._tab_object = self._make_tab("📦 Object Record")

    def _make_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self._notebook, bg=self.BG)
        self._notebook.add(frame, text=title)

        text = tk.Text(frame,
                        bg=self.EDITOR_BG, fg=self.FG,
                        font=("Consolas", 10),
                        relief=tk.FLAT, bd=0,
                        padx=10, pady=8,
                        state=tk.DISABLED,
                        selectbackground=self.ACCENT,
                        wrap=tk.NONE)

        sy = ttk.Scrollbar(frame, command=text.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = tk.Scrollbar(frame, orient=tk.HORIZONTAL,
                           command=text.xview, bg=self.BG3)
        sx.pack(side=tk.BOTTOM, fill=tk.X)
        text.config(yscrollcommand=sy.set, xscrollcommand=sx.set)
        text.pack(fill=tk.BOTH, expand=True)
        return text

    # ─────────────────────────────────────────
    # Alt panel: Konsol / Hata mesajları
    # ─────────────────────────────────────────
    def _build_console(self):
        frame = tk.Frame(self.root, bg=self.BG2, height=140)
        frame.pack(fill=tk.X, padx=8, pady=6)
        frame.pack_propagate(False)

        header = tk.Frame(frame, bg=self.BG3)
        header.pack(fill=tk.X)
        tk.Label(header, text=" 🖥  Konsol / Hatalar",
                 bg=self.BG3, fg=self.ACCENT2,
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
        _make_btn(header, "Temizle", self._clear_console,
                  bg=self.BG3, fg=self.FG2, hover_bg="#4A4A6A",
                  font_cfg=("Consolas", 9), padx=8, pady=2).pack(side=tk.RIGHT, padx=8)

        self._console = tk.Text(frame,
                                 bg="#0D0D1A", fg=self.FG,
                                 font=("Consolas", 10),
                                 relief=tk.FLAT, bd=0,
                                 padx=8, pady=4,
                                 state=tk.DISABLED,
                                 height=6)
        self._console.tag_config("error",   foreground=self.ERROR)
        self._console.tag_config("success", foreground=self.SUCCESS)
        self._console.tag_config("warning", foreground=self.WARNING)
        self._console.tag_config("info",    foreground=self.ACCENT2)

        sy = ttk.Scrollbar(frame, command=self._console.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.config(yscrollcommand=sy.set)
        self._console.pack(fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────
    # Buton aksiyonları
    # ─────────────────────────────────────────
    def _on_assemble(self):
        source = self._editor.get("1.0", tk.END).strip()
        if not source:
            self._log("Editör boş.", "warning")
            return

        self._log("Assembly başlatıldı...", "info")
        self._status_lbl.config(text="⏳ Derleniyor...")
        self.root.update()

        import os
        prog_name = os.path.splitext(os.path.basename(self._current_file))[0] if self._current_file else "PROG"
        ok = self.assembler.assemble(source, prog_name)

        if ok:
            self._status_lbl.config(text=f"✓ Başarılı  |  {len(self.assembler.object_code)} komut")
            self._log(f"✓ Assembly başarılı — {len(self.assembler.object_code)} komut/veri üretildi.", "success")
            self._fill_outputs()
        else:
            self._status_lbl.config(text="✗ Hata")
            self._log(f"✗ {len(self.assembler.errors)} hata bulundu:", "error")
            for err in self.assembler.errors:
                self._log(f"   {err}", "error")

    def _fill_outputs(self):
        self._set_text(self._tab_hex,     self.assembler.get_hex_output())
        self._set_text(self._tab_listing, self.assembler.get_listing())
        self._set_text(self._tab_symtab,  self.assembler.get_symtab_str())
        self._set_text(self._tab_object,  self.assembler.get_object_record())

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Assembly Dosyası Aç",
            filetypes=[("Assembly", "*.asm *.s"), ("Tümü", "*.*")])
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._editor.delete("1.0", tk.END)
            self._editor.insert("1.0", content)
            self._update_line_numbers()
            self._highlighter.apply()
            self._current_file = path
            self._log(f"Dosya açıldı: {path}", "info")

    def _save_file(self):
        path = self._current_file or filedialog.asksaveasfilename(
            title="Kaydet",
            defaultextension=".asm",
            filetypes=[("Assembly", "*.asm"), ("Tümü", "*.*")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._editor.get("1.0", tk.END))
            self._current_file = path
            self._log(f"Kaydedildi: {path}", "success")

    def _clear_all(self):
        self._editor.delete("1.0", tk.END)
        for tab in (self._tab_hex, self._tab_listing,
                    self._tab_symtab, self._tab_object):
            self._set_text(tab, "")
        self._clear_console()
        self._update_line_numbers()
        self._status_lbl.config(text="Hazır")

    def _clear_console(self):
        self._console.config(state=tk.NORMAL)
        self._console.delete("1.0", tk.END)
        self._console.config(state=tk.DISABLED)

    # ─────────────────────────────────────────
    # Yardımcı metodlar
    # ─────────────────────────────────────────
    def _log(self, msg: str, tag: str = "info"):
        self._console.config(state=tk.NORMAL)
        self._console.insert(tk.END, msg + "\n", tag)
        self._console.see(tk.END)
        self._console.config(state=tk.DISABLED)

    def _set_text(self, widget: tk.Text, content: str):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state=tk.DISABLED)

    def _insert_sample(self):
        sample = """\
# 1'den 5'e kadar toplama: toplam = 1+2+3+4+5 = 15
#
# Registerlar:
#   x1 = sayac (1..5)   x2 = toplam   x3 = sinir (5)
#
.text
.org 0x0

MAIN:   addi  x1, x0, 1      # x1 = 1 (sayac)
        addi  x2, x0, 0      # x2 = 0 (toplam)
        addi  x3, x0, 5      # x3 = 5 (sinir)

LOOP:   add   x2, x2, x1     # toplam += sayac
        addi  x1, x1, 1      # sayac++
        bge   x3, x1, LOOP   # x3 >= x1 ise devam et (sayac <= 5)
        lui   x4, 1           # x4 = 0x1000 (veri bolumu)
        sw    x2, 0(x4)       # sonucu belleğe yaz
        ebreak                # dur

.data
.org 0x1000
SONUC:  .word 0               # toplam buraya yazilir
"""
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", sample)
        self._update_line_numbers()
        self._highlighter.apply()


# ─────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = RV32IAssemblerGUI(root)
    root.mainloop()
