# gui/app.py
# RV32I Assembler - Tkinter GUI

import os
import tkinter as tk
from tkinter import filedialog

from core import Assembler
from gui.theme import Theme
from gui.widgets import make_btn
from gui.components.editor import EditorPanel
from gui.components.output_tabs import OutputTabsPanel
from gui.components.console import ConsolePanel

class RV32IAssemblerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.assembler = Assembler()
        self._current_file = None

        self._setup_window()
        self._build_ui()
        self._insert_sample()

    def _setup_window(self):
        self.root.title("RV32I Assembler  —  PicoRV")
        self.root.configure(bg=Theme.BG)
        self.root.geometry("1300x820")
        self.root.minsize(900, 600)
        Theme.setup_ttk_styles()

    def _build_ui(self):
        # ── Başlık ──
        header = tk.Frame(self.root, bg=Theme.ACCENT, height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header,
                 text="    RV32I Assembler  |  PicoRV Alt Kümesi",
                 bg=Theme.ACCENT, fg="#FFFFFF",
                 font=("Consolas", 13, "bold")).pack(side=tk.LEFT, padx=10)

        # ── Araç çubuğu ──
        toolbar = tk.Frame(self.root, bg=Theme.BG2, height=48)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        self._btn_assemble = make_btn(
            toolbar, "▶  Assemble", self._on_assemble,
            bg=Theme.ACCENT, fg="#FFFFFF", hover_bg="#C5602A",
            font_cfg=("Consolas", 10, "bold"), padx=16, pady=6)
        self._btn_assemble.pack(side=tk.LEFT, padx=(10, 4), pady=8)

        for text, cmd in [
            ("📂 Aç",       self._open_file),
            ("💾 Kaydet",   self._save_file),
            ("🗑  Temizle", self._clear_all),
            ("📋 Örnek Kod", self._insert_sample),
        ]:
            make_btn(toolbar, text, cmd,
                      bg=Theme.BG3, fg=Theme.FG, hover_bg="#4A4A6A",
                      font_cfg=("Consolas", 10)).pack(side=tk.LEFT, padx=4, pady=8)

        # Sağda bilgi etiketi
        self._status_lbl = tk.Label(toolbar, text="Hazır",
                                    bg=Theme.BG2, fg=Theme.FG2,
                                    font=("Consolas", 10))
        self._status_lbl.pack(side=tk.RIGHT, padx=16)

        # ── Ana içerik: sol + sağ ──
        content = tk.Frame(self.root, bg=Theme.BG)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))

        # Sol: Editör
        self.editor_panel = EditorPanel(content)

        # Ayırıcı
        tk.Frame(content, bg=Theme.BORDER, width=2).pack(
            side=tk.LEFT, fill=tk.Y, padx=4)

        # Sağ: Çıktı sekmeleri
        self.output_tabs = OutputTabsPanel(content)

        # ── Alt: Hata/Uyarı paneli ──
        self.console = ConsolePanel(self.root)

    # ─────────────────────────────────────────
    # Buton aksiyonları
    # ─────────────────────────────────────────
    def _on_assemble(self):
        source = self.editor_panel.get_code().strip()
        if not source:
            self.console.log("Editör boş.", "warning")
            return

        self.console.log("Assembly başlatıldı...", "info")
        self._status_lbl.config(text="⏳ Derleniyor...")
        self.root.update()

        prog_name = os.path.splitext(os.path.basename(self._current_file))[0] if self._current_file else "PROG"
        ok = self.assembler.assemble(source, prog_name)

        if ok:
            self._status_lbl.config(text=f"✓ Başarılı  |  {len(self.assembler.object_code)} komut")
            self.console.log(f"✓ Assembly başarılı — {len(self.assembler.object_code)} komut/veri üretildi.", "success")
            self._fill_outputs()
        else:
            self._status_lbl.config(text="✗ Hata")
            self.console.log(f"✗ {len(self.assembler.errors)} hata bulundu:", "error")
            for err in self.assembler.errors:
                self.console.log(f"   {err}", "error")

    def _fill_outputs(self):
        self.output_tabs.set_content(
            hex_out=self.assembler.get_hex_output(),
            listing_out=self.assembler.get_listing(),
            symtab_out=self.assembler.get_symtab_str(),
            object_out=self.assembler.get_object_record()
        )

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Assembly Dosyası Aç",
            filetypes=[("Assembly", "*.asm *.s"), ("Tümü", "*.*")])
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor_panel.set_code(content)
            self._current_file = path
            self.console.log(f"Dosya açıldı: {path}", "info")

    def _save_file(self):
        path = self._current_file or filedialog.asksaveasfilename(
            title="Kaydet",
            defaultextension=".asm",
            filetypes=[("Assembly", "*.asm"), ("Tümü", "*.*")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.editor_panel.get_code())
            self._current_file = path
            self.console.log(f"Kaydedildi: {path}", "success")

    def _clear_all(self):
        self.editor_panel.clear()
        self.output_tabs.clear()
        self.console.clear()
        self._status_lbl.config(text="Hazır")

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
        self.editor_panel.set_code(sample)

if __name__ == '__main__':
    root = tk.Tk()
    app  = RV32IAssemblerGUI(root)
    root.mainloop()
