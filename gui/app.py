# gui/app.py
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
        self._editor_path: str | None = None
        self._dirty = False
        self._project_folder: str | None = None

        self._setup_window()
        self._build_ui()

    # ── Pencere ───────────────────────────────────────────────────
    def _setup_window(self):
        self.root.title("RV32I Assembler & Linker")
        self.root.configure(bg=Theme.BG)
        self.root.geometry("1440x860")
        self.root.minsize(1100, 640)
        Theme.setup_ttk_styles()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Üst toolbar ──
        toolbar = tk.Frame(self.root, bg=Theme.BG4, height=40)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # Sol: uygulama adı
        tk.Label(toolbar, text="  RV32I  Assembler & Linker",
                 bg=Theme.BG4, fg=Theme.FG2,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)

        # Sağ: dosya adı + editör aksiyonları
        self._file_lbl = tk.Label(toolbar, text="",
                                   bg=Theme.BG4, fg=Theme.FG3,
                                   font=("Segoe UI", 9))
        self._file_lbl.pack(side=tk.LEFT, padx=(16, 0))

        for text, cmd in [
            ("Yeni",          self._new_file),
            ("İmport",        self._import_file),
            ("Kaydet",        self._save_file),
            ("Farklı Kaydet", self._save_file_as),
        ]:
            make_btn(toolbar, text, cmd,
                     bg=Theme.BG4, fg=Theme.FG2, hover_bg=Theme.BG3,
                     font_cfg=("Segoe UI", 9), padx=10, pady=6
                     ).pack(side=tk.RIGHT, padx=1)

        # ── Gövde (Resizable Panes) ──
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                                   bg=Theme.BORDER, sashwidth=2, sashrelief=tk.FLAT)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Sol: Proje paneli
        self.project = ProjectPanel(
            self.paned,
            on_build=self._on_build,
            on_file_select=self._open_file_in_editor)
        self.project.export_mem_cb    = self._export_mem
        self.project.export_hex_cb    = self._export_hex
        self.project.on_folder_opened = self._on_folder_opened
        self.project.get_editor_code  = lambda: self.editor.get_code()
        self.project.get_editor_name  = lambda: (
            os.path.basename(self._editor_path) if self._editor_path else "editör")
        self.paned.add(self.project.frame, width=260, minsize=200)

        # Orta: Editör
        editor_wrap = tk.Frame(self.paned, bg=Theme.EDITOR_BG)
        self.editor = EditorPanel(editor_wrap)
        self.paned.add(editor_wrap, stretch="always", minsize=400)

        # Sağ: Çıktı sekmeleri
        self.output = OutputTabsPanel(self.paned)
        self.output.get_bin_data = self._get_bin_data
        self.paned.add(self.output.frame, width=380, minsize=300)

        # Alt: Konsol
        self.console = ConsolePanel(self.root)
        self.output.log = self.console.log

    # ── Build ─────────────────────────────────────────────────────
    def _on_build(self):
        self._autosave()

        checked = self.project.get_checked_indices()
        if not checked:
            self.console.log("Build için en az bir dosyayı işaretleyin.", "warning")
            return

        files = self.project.files
        self.console.log(f"─── Build başladı ({len(checked)} dosya) ───", "info")
        self.root.update()

        objects      = []
        assemblies   = []   # linker listing için assembler nesnelerini sakla
        all_ok  = True
        for idx in checked:
            path, _ = files[idx]
            if path is None:
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
                assemblies.append(asm)
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

        result = self.project.read_script()
        if isinstance(result, tuple):
            _, err_msg = result
            self.console.log(f"✗ Linker script hatası: {err_msg}", "error")
            return
        script = self.project.script

        if len(objects) == 1:
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
                    f"⚠ Çözülmemiş extern semboller: {list(objects[0].externs)}",
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
            listing_out = linker.get_listing(objects, assemblies),
            symtab_out  = self._combined_symtab(objects),
            object_out  = self._objects_summary(checked_files, objects),
            map_out     = linker.get_link_map(),
            mem_out     = linker.get_mem_output(),
        )
        self.output.show_tab('map')

    # ── Editör — dosya işlemleri ──────────────────────────────────
    def _open_file_in_editor(self, path: str | None):
        if path is None:
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
        self._file_lbl.config(text=f"{os.path.basename(path)}")
        self.editor._editor.edit_modified(False)
        self.editor._editor.bind('<<Modified>>', self._on_editor_modified)

    def _on_editor_modified(self, _=None):
        if self.editor._editor.edit_modified():
            self._dirty = True
            name = os.path.basename(self._editor_path) if self._editor_path else "yeni dosya"
            self._file_lbl.config(text=f"{name}  ●")
            self.editor._editor.edit_modified(False)

    def _on_folder_opened(self, folder: str):
        self._project_folder = folder
        self._file_lbl.config(text=f"{os.path.basename(folder)}/")

    def _new_file(self):
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
        with open(path, 'w', encoding='utf-8') as f:
            f.write("")
        self.editor.set_code("")
        self._editor_path = path
        self._dirty = False
        self._file_lbl.config(text=f"{os.path.basename(path)}")
        self.editor._editor.edit_modified(False)
        self.editor._editor.bind('<<Modified>>', self._on_editor_modified)
        if not any(p == path for p, _ in self.project.files):
            self.project.add_file_entry(path, checked=True)
        for i, (p, _) in enumerate(self.project.files):
            if p == path:
                self.project.select_index(i)
                break

    def _import_file(self):
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
        if not any(p == dest for p, _ in self.project.files):
            self.project.add_file_entry(dest, checked=True)
        self._open_file_in_editor(dest)
        for i, (p, _) in enumerate(self.project.files):
            if p == dest:
                self.project.select_index(i)
                break

    def _save_file(self):
        if not self._editor_path:
            self._save_file_as()
            return
        with open(self._editor_path, 'w', encoding='utf-8') as f:
            f.write(self.editor.get_code())
        self._dirty = False
        self._file_lbl.config(text=f"{os.path.basename(self._editor_path)}")
        self.console.log(f"Kaydedildi: {self._editor_path}", "success")

    def _save_file_as(self):
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
        self._file_lbl.config(text=f"{os.path.basename(path)}")
        self.console.log(f"Farklı kaydedildi: {path}", "success")
        for idx, (p, obj) in enumerate(self.project.files):
            if p == old_path:
                self.project.files[idx] = (path, obj)
                self.project.set_file_status(idx, 'idle')
                return
        if not any(p == path for p, _ in self.project.files):
            self.project.add_file_entry(path, checked=True)

    def _autosave(self):
        if self._dirty and self._editor_path:
            with open(self._editor_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.get_code())
            self._dirty = False
            self._file_lbl.config(text=f"{os.path.basename(self._editor_path)}")

    # ── Dışa aktarma ──────────────────────────────────────────────
    def _export_mem(self):
        if not self._linker:
            self.console.log("Önce Build çalıştırın.", "warning")
            return
        self._export_to_file(".mem", "mem Dosyası", self._linker.get_mem_output())

    def _export_hex(self):
        if not self._linker:
            self.console.log("Önce Build çalıştırın.", "warning")
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

    # ── Yardımcılar ───────────────────────────────────────────────
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

    def _objects_summary(self, files, objects, assemblies=None) -> str:
        blocks = []
        for (path, _), obj in zip(files, objects):
            fname = os.path.basename(path) if path else "[editör]"
            header = f"── {fname} " + "─" * max(0, 50 - len(fname))
            blocks.append(header)
            blocks.append(obj.get_object_record())
            blocks.append("")
        return "\n".join(blocks)

    @staticmethod
    def _asm_to_mem(asm: Assembler) -> str:
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

    def _get_bin_data(self) -> bytes | None:
        if not self._linker or not self._linker.linked_code:
            return None
        # linked_code: [(addr, word, size), ...] — sadece 4-byte word'ler, sıralı
        words = sorted(
            ((addr, word) for addr, word, size in self._linker.linked_code if size == 4),
            key=lambda x: x[0]
        )
        if not words:
            return None
        return b"".join(w.to_bytes(4, "little") for _, w in words)

    def _confirm_discard(self) -> bool:
        from tkinter import messagebox
        return messagebox.askyesno(
            "Kaydedilmemiş Değişiklik",
            "Editördeki değişiklikler kaydedilmedi. Devam edilsin mi?")

    def _on_close(self):
        if self._dirty and not self._confirm_discard():
            return
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app  = RV32IAssemblerGUI(root)
    root.mainloop()
