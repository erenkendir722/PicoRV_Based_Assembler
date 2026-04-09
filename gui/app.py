# gui/app.py
# RV32I Assembler + Linker — Ana Pencere
#
# Akış:
#   1. Sol panel: dosya ekle, linker script ayarla
#   2. Ortada: seçili dosyanın editörü
#   3. Sağda: çıktı sekmeleri (hex, listing, sembol, link map, .mem)
#   4. "Assemble & Link" → tüm dosyaları derle, link et, çıktıları doldur

import os
import tkinter as tk
from tkinter import ttk, filedialog

from core import Assembler, ObjectFile, Linker, LinkerScriptError
from gui.theme import Theme
from gui.widgets import make_btn
from gui.components.editor import EditorPanel
from gui.components.output_tabs import OutputTabsPanel
from gui.components.console import ConsolePanel
from gui.components.project_panel import ProjectPanel


class RV32IAssemblerGUI:
    def __init__(self, root: tk.Tk):
        self.root   = root
        self._linker: Linker | None = None

        # Editörde açık dosyanın yolu (kaydetmek için)
        self._editor_path: str | None = None
        # Editörde unsaved değişiklik var mı
        self._dirty = False
        # Açık proje klasörü
        self._project_folder: str | None = None

        self._setup_window()
        self._build_ui()

    # ─────────────────────────────────────────
    # Pencere
    # ─────────────────────────────────────────
    def _setup_window(self):
        self.root.title("RV32I Assembler & Linker  —  PicoRV")
        self.root.configure(bg=Theme.BG)
        self.root.geometry("1600x900")
        self.root.minsize(1200, 680)
        Theme.setup_ttk_styles()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────
    def _build_ui(self):
        # ── Başlık ──
        header = tk.Frame(self.root, bg=Theme.ACCENT, height=46)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header,
                 text="    RV32I Assembler & Linker  |  PicoRV",
                 bg=Theme.ACCENT, fg="#FFFFFF",
                 font=("Consolas", 13, "bold")).pack(side=tk.LEFT, padx=10)

        # ── Konsol (en alta yerleşsin diye önce pack et) ──
        self.console = ConsolePanel(self.root)

        # ── Gövde (başlık ile konsol arasını kaplar) ──
        body = tk.Frame(self.root, bg=Theme.BG)
        body.pack(fill=tk.BOTH, expand=True,
                  before=self.console.frame)

        # ── Sol: Proje paneli ──
        self.project = ProjectPanel(
            body,
            on_build=self._on_build,
            on_file_select=self._open_file_in_editor)
        self.project.export_mem_cb  = self._export_mem
        self.project.export_hex_cb  = self._export_hex
        self.project.on_folder_opened = self._on_folder_opened
        # Editör içeriğini proje paneline bağla (build sırasında kullanılır)
        self.project.get_editor_code = lambda: self.editor.get_code()
        self.project.get_editor_name = lambda: (
            os.path.basename(self._editor_path) if self._editor_path else "editör")

        tk.Frame(body, bg=Theme.BORDER, width=2).pack(side=tk.LEFT, fill=tk.Y)

        # ── Orta: Editör ──
        editor_wrap = tk.Frame(body, bg=Theme.BG)
        editor_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Editör araç çubuğu
        ebar = tk.Frame(editor_wrap, bg=Theme.BG2, height=36)
        ebar.pack(fill=tk.X)
        ebar.pack_propagate(False)

        self._file_lbl = tk.Label(ebar, text="  —",
                                  bg=Theme.BG2, fg=Theme.FG2,
                                  font=("Consolas", 10))
        self._file_lbl.pack(side=tk.LEFT, padx=8)

        for text, cmd in [
            ("📥 İmport",      self._import_file),
            ("💾 Kaydet",      self._save_file),
            ("💾 Farklı Kaydet", self._save_file_as),
            ("📄 Yeni",        self._new_file),
        ]:
            make_btn(ebar, text, cmd,
                     bg=Theme.BG2, fg=Theme.FG2, hover_bg=Theme.BG3,
                     font_cfg=("Consolas", 9), padx=8, pady=4
                     ).pack(side=tk.RIGHT, padx=2, pady=4)

        self.editor = EditorPanel(editor_wrap)

        tk.Frame(body, bg=Theme.BORDER, width=2).pack(side=tk.LEFT, fill=tk.Y)

        # ── Sağ: Çıktı ──
        self.output = OutputTabsPanel(body)

    # ─────────────────────────────────────────
    # Build: Assemble & Link
    # ─────────────────────────────────────────
    def _on_build(self):
        # Önce editördeki içeriği kaydet (dosyaya bağlıysa)
        self._autosave()

        checked = self.project.get_checked_indices()
        if not checked:
            self.console.log("Build için en az bir dosyayı işaretleyin (✔).", "warning")
            return

        files = self.project.files
        self.console.log(f"─── Build başladı ({len(checked)} dosya) ───", "info")
        self.root.update()

        # ── Adım 1: İşaretli dosyaları assemble et ──
        objects = []
        all_ok  = True
        for idx in checked:
            path, _ = files[idx]
            if path is None:
                # Editördeki kod
                source = self.editor.get_code()
                name   = (os.path.splitext(os.path.basename(self._editor_path))[0]
                          if self._editor_path else "editor")
            else:
                name = os.path.splitext(os.path.basename(path))[0]
                try:
                    source = open(path, 'r', encoding='utf-8').read()
                except OSError as e:
                    self.console.log(f"✗ {name}: dosya okunamadı — {e}", "error")
                    self.project.set_file_status(idx, 'error')
                    all_ok = False
                    continue

            if not source.strip():
                self.console.log(f"  ⚠ {name}: boş dosya, atlandı.", "warning")
                self.project.set_file_status(idx, 'idle')
                continue

            asm = Assembler()
            ok  = asm.assemble(source, name)
            if ok:
                obj = ObjectFile.from_assembler(asm, name)
                self.project.set_file_object(idx, obj)
                self.project.set_file_status(idx, 'ok')
                objects.append(obj)
                self.console.log(
                    f"  ✓ {name}.asm  "
                    f"{len(obj.text)}t/{len(obj.data)}d word  "
                    f"globals={list(obj.globals)}  "
                    f"externs={list(obj.externs)}", "success")
            else:
                self.project.set_file_status(idx, 'error')
                self.console.log(f"  ✗ {name}.asm:", "error")
                for err in asm.errors:
                    self.console.log(f"      {err}", "error")
                all_ok = False

        if not all_ok:
            self.console.log("Build durduruldu: assembly hataları var.", "error")
            return

        # ── Adım 2: Linker script ──
        result = self.project.read_script()
        if isinstance(result, tuple):
            _, err_msg = result
            self.console.log(f"✗ Linker script hatası: {err_msg}", "error")
            return
        script = self.project.script

        # ── Adım 3: Link ──
        if len(objects) == 1:
            # Tek dosya → sadece assemble çıktısını göster, link map boş
            path0, _ = files[checked[0]]
            if path0 is None:
                source = self.editor.get_code()
                name   = (os.path.splitext(os.path.basename(self._editor_path))[0]
                          if self._editor_path else "editor")
            else:
                source = open(path0, 'r', encoding='utf-8').read()
                name   = os.path.splitext(os.path.basename(path0))[0]
            asm_single = Assembler()
            asm_single.assemble(source, name)
            self.output.set_content(
                hex_out     = asm_single.get_hex_output(),
                listing_out = asm_single.get_listing(),
                symtab_out  = asm_single.get_symtab_str(),
                object_out  = asm_single.get_object_record(),
                map_out     = "(tek dosya — link map yok)",
                mem_out     = self._asm_to_mem(asm_single),
            )
            self.output.show_tab('hex')
            if objects[0].externs:
                self.console.log(
                    f"⚠ Çözülmemiş extern semboller: {list(objects[0].externs)}  "
                    f"— tam link için bu sembolleri tanımlayan dosyaları da işaretleyin.",
                    "warning")
            else:
                self.console.log("✓ Assemble başarılı.", "success")
            return

        linker = Linker(text_base=script.text_base,
                        data_base=script.data_base)
        ok = linker.link(objects)

        if not ok:
            self.console.log("✗ Link hatası:", "error")
            for err in linker.errors:
                self.console.log(f"   {err}", "error")
            return

        self._linker = linker
        self.console.log(
            f"✓ Link başarılı  —  {len(linker.linked_code)} word  "
            f"| {len(linker.global_symtab)} global sembol  "
            f"| text=0x{script.text_base:08X}  data=0x{script.data_base:08X}",
            "success")

        checked_files = [files[i] for i in checked]
        self.output.set_content(
            hex_out     = linker.get_hex_output(),
            listing_out = self._combined_listing(checked_files),
            symtab_out  = self._combined_symtab(objects),
            object_out  = self._objects_summary(checked_files, objects),
            map_out     = linker.get_link_map(),
            mem_out     = linker.get_mem_output(),
        )
        self.output.show_tab('map')

    # ─────────────────────────────────────────
    # Editör — dosya açma / kaydetme
    # ─────────────────────────────────────────
    def _open_file_in_editor(self, path: str | None):
        """Proje listesinden tıklandığında editörde aç.
        path=None ise editör girdisi — dosya okuma yapma, sadece odaklan."""
        if path is None:
            # Editör girdisine tıklandı — zaten orada, sadece odak ver
            self.editor._editor.focus_set()
            return
        if self._dirty and not self._confirm_discard():
            return False
        try:
            content = open(path, 'r', encoding='utf-8').read()
        except OSError as e:
            self.console.log(f"Dosya okunamadı: {e}", "error")
            return
        self.editor.set_code(content)
        self._editor_path = path
        self._dirty = False
        self._file_lbl.config(text=f"  {os.path.basename(path)}")
        self.editor._editor.edit_modified(False)
        self.editor._editor.bind('<<Modified>>', self._on_editor_modified)

    def _on_editor_modified(self, _=None):
        if self.editor._editor.edit_modified():
            self._dirty = True
            name = os.path.basename(self._editor_path) if self._editor_path else "yeni dosya"
            self._file_lbl.config(text=f"  {name}  *")
            self.editor._editor.edit_modified(False)

    def _on_folder_opened(self, folder: str):
        self._project_folder = folder
        self._file_lbl.config(text=f"  📁 {os.path.basename(folder)}")

    def _new_file(self):
        """İsim sor, boş dosyayı diske kaydet, editörde ve listede aç."""
        if not self._project_folder:
            self.console.log("Önce sol panelden bir klasör açın.", "warning")
            return
        if self._dirty and not self._confirm_discard():
            return
        path = filedialog.asksaveasfilename(
            title="Yeni Dosya Oluştur",
            initialdir=self._project_folder,
            defaultextension=".asm",
            filetypes=[("Assembly", "*.asm *.s"), ("Tümü", "*.*")])
        if not path:
            return
        # Boş dosyayı diske oluştur
        with open(path, 'w', encoding='utf-8') as f:
            f.write("")
        # Editörde aç
        self.editor.set_code("")
        self._editor_path = path
        self._dirty = False
        self._file_lbl.config(text=f"  {os.path.basename(path)}")
        self.editor._editor.edit_modified(False)
        self.editor._editor.bind('<<Modified>>', self._on_editor_modified)
        # Proje listesine ekle ve seç
        if not any(p == path for p, _ in self.project.files):
            self.project.add_file_entry(path, checked=True)
        for i, (p, _) in enumerate(self.project.files):
            if p == path:
                self.project.select_index(i)
                break

    def _import_file(self):
        """Dışarıdan bir .asm dosyası seç, proje klasörüne kopyala, listeye ekle."""
        import shutil
        if not self._project_folder:
            self.console.log("Önce sol panelden bir klasör açın.", "warning")
            return
        src = filedialog.askopenfilename(
            title="İmport Edilecek Dosyayı Seç",
            filetypes=[("Assembly", "*.asm *.s"), ("Tümü", "*.*")])
        if not src:
            return
        dest = os.path.join(self._project_folder, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(dest):
            if os.path.exists(dest):
                from tkinter import messagebox
                if not messagebox.askyesno("Üzerine Yaz",
                        f"{os.path.basename(dest)} zaten var. Üzerine yazılsın mı?"):
                    return
            shutil.copy2(src, dest)
            self.console.log(f"İmport edildi: {os.path.basename(dest)}", "success")
        # Listeye ekle ve editörde aç
        if not any(p == dest for p, _ in self.project.files):
            self.project.add_file_entry(dest, checked=True)
        self._open_file_in_editor(dest)
        for i, (p, _) in enumerate(self.project.files):
            if p == dest:
                self.project.select_index(i)
                break

    def _save_file(self):
        """Kaydet — bağlı dosyaya yaz. Bağlı dosya yoksa Farklı Kaydet'e düş."""
        if not self._editor_path:
            self._save_file_as()
            return
        with open(self._editor_path, 'w', encoding='utf-8') as f:
            f.write(self.editor.get_code())
        self._dirty = False
        self._file_lbl.config(text=f"  {os.path.basename(self._editor_path)}")
        self.console.log(f"Kaydedildi: {self._editor_path}", "success")

    def _save_file_as(self):
        """Her zaman dialog aç, farklı isimle kaydet."""
        if not self._project_folder:
            self.console.log("Önce sol panelden bir klasör açın.", "warning")
            return
        path = filedialog.asksaveasfilename(
            title="Farklı Kaydet",
            initialdir=self._project_folder,
            defaultextension=".asm",
            filetypes=[("Assembly", "*.asm *.s"), ("Tümü", "*.*")])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.editor.get_code())
        old_path = self._editor_path
        self._editor_path = path
        self._dirty = False
        self._file_lbl.config(text=f"  {os.path.basename(path)}")
        self.console.log(f"Farklı kaydedildi: {path}", "success")
        # Listede eski path varsa güncelle, yoksa ekle
        for idx, (p, obj) in enumerate(self.project.files):
            if p == old_path:
                self.project.files[idx] = (path, obj)
                self.project.set_file_status(idx, 'idle')
                return
        if not any(p == path for p, _ in self.project.files):
            self.project.add_file_entry(path, checked=True)

    def _autosave(self):
        """Editörde değişiklik varsa ve dosyaya bağlıysa otomatik kaydet.
        Editör girdisi proje listesindeyse kaydetmeye gerek yok — build direkt okur."""
        if self._dirty and self._editor_path:
            with open(self._editor_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.get_code())
            self._dirty = False
            self._file_lbl.config(
                text=f"  {os.path.basename(self._editor_path)}")

    def _load_sample(self):
        sample = """\
# Örnek: 1'den 5'e toplam = 15
.global MAIN
.text
.org 0x0

MAIN:   addi  x1, x0, 0      # toplam = 0
        addi  x2, x0, 1      # sayac  = 1
        addi  x3, x0, 5      # limit  = 5

LOOP:   add   x1, x1, x2     # toplam += sayac
        addi  x2, x2, 1      # sayac++
        bge   x3, x2, LOOP   # sayac <= 5 → devam

        lui   x4, 1           # x4 = 0x1000
        sw    x1, 0(x4)       # sonucu belleğe yaz
        ebreak

.data
.org 0x1000
SONUC:  .word 0
"""
        self.editor.set_code(sample)
        self._editor_path = None
        self._dirty = False
        self._file_lbl.config(text="  örnek kod  (kaydedilmedi)")

    # ─────────────────────────────────────────
    # Dışa aktarma
    # ─────────────────────────────────────────
    def _export_mem(self):
        if not self._linker:
            self.console.log("Önce Assemble & Link çalıştırın.", "warning")
            return
        self._export_to_file(".mem", "mem Dosyası", self._linker.get_mem_output())

    def _export_hex(self):
        if not self._linker:
            self.console.log("Önce Assemble & Link çalıştırın.", "warning")
            return
        self._export_to_file(".hex", "Hex Dosyası", self._linker.get_hex_output())

    def _export_to_file(self, ext: str, label: str, content: str):
        path = filedialog.asksaveasfilename(
            title=f"{label} Kaydet",
            defaultextension=ext,
            filetypes=[(label, f"*{ext}"), ("Tümü", "*.*")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.console.log(f"Kaydedildi: {path}", "success")

    # ─────────────────────────────────────────
    # Yardımcılar
    # ─────────────────────────────────────────
    def _combined_listing(self, files) -> str:
        lines = []
        for path, _ in files:
            if path is None:
                source = self.editor.get_code()
                name   = (os.path.splitext(os.path.basename(self._editor_path))[0]
                          if self._editor_path else "editor")
            else:
                name   = os.path.splitext(os.path.basename(path))[0]
                source = open(path, 'r', encoding='utf-8').read()
            asm = Assembler()
            asm.assemble(source, name)
            lines.append(f"── {name} ──")
            lines.append(asm.get_listing())
            lines.append("")
        return "\n".join(lines)

    def _combined_symtab(self, objects) -> str:
        lines = ["Birleşik Sembol Tablosu", "─" * 45]
        for obj in objects:
            lines.append(f"  [{obj.name}]")
            for label, addr in sorted(obj.symtab.items(), key=lambda x: x[1]):
                g = " (global)" if label in obj.globals else ""
                lines.append(f"    {label:<20} → 0x{addr:08X}{g}")
        return "\n".join(lines)

    def _objects_summary(self, files, objects) -> str:
        lines = ["Object Dosyaları", "─" * 50]
        for (path, _), obj in zip(files, objects):
            fname = os.path.basename(path) if path else "[editör]"
            lines += [
                f"  {fname}",
                f"    text  : {len(obj.text)} word",
                f"    data  : {len(obj.data)} word",
                f"    global: {list(obj.globals.keys()) or '—'}",
                f"    extern: {list(obj.externs) or '—'}",
                f"    reloc : {len(obj.relocations)}",
                "",
            ]
        return "\n".join(lines)

    @staticmethod
    def _asm_to_mem(asm: Assembler) -> str:
        """Tek dosya için $readmemh formatı."""
        lines = []
        prev  = None
        for addr, word, size in asm.object_code:
            if size != 4:
                continue
            if prev is None or addr != prev + 4:
                lines.append(f"@{addr // 4:08X}")
            lines.append(f"{word:08X}")
            prev = addr
        return "\n".join(lines)

    def _confirm_discard(self) -> bool:
        from tkinter import messagebox
        return messagebox.askyesno(
            "Kaydedilmemiş Değişiklik",
            "Editördeki değişiklikler kaydedilmedi. Devam edilsin mi?")

    def _on_close(self):
        if self._dirty and not self._confirm_discard():
            return
        self.root.destroy()


# ─────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = RV32IAssemblerGUI(root)
    root.mainloop()
