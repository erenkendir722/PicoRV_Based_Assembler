import glob
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk
from gui.theme import Theme


class OutputTabsPanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Theme.BG2, width=520)
        self.frame.pack_propagate(False)

        inner = tk.Frame(self.frame, bg=Theme.BG2)
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(inner)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._tab_hex     = self._make_tab("Hex")
        self._tab_listing = self._make_tab("Listing")
        self._tab_symtab  = self._make_tab("Semboller")
        self._tab_object  = self._make_tab("Object")
        self._tab_map     = self._make_tab("Link Map")
        self._tab_mem     = self._make_tab(".mem")
        self._build_fpga_tab()

        # app.py tarafından bağlanır
        self.get_bin_data: callable = lambda: None
        self.log: callable = lambda msg, tag="info": None

    # ── FPGA sekmesi ──────────────────────────────────────────────────

    def _build_fpga_tab(self):
        frame = tk.Frame(self._notebook, bg=Theme.EDITOR_BG)
        self._notebook.add(frame, text="  FPGA  ")

        # Başlık
        header = tk.Frame(frame, bg=Theme.BG4)
        header.pack(fill=tk.X)
        tk.Label(header, text="Bağlı FPGA / Seri Portlar",
                 bg=Theme.BG4, fg=Theme.FG2,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        tk.Button(header, text="⟳  Yenile",
                  bg=Theme.BG3, fg=Theme.ACCENT2,
                  activebackground=Theme.BORDER, activeforeground=Theme.FG,
                  font=("Segoe UI", 9), relief=tk.FLAT, bd=0,
                  cursor="hand2", padx=10, pady=4,
                  command=self._refresh_fpga).pack(side=tk.RIGHT, padx=8, pady=6)
        tk.Frame(frame, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        # Port listesi
        self._fpga_list_frame = tk.Frame(frame, bg=Theme.EDITOR_BG)
        self._fpga_list_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # Alt kontrol şeridi
        ctrl = tk.Frame(frame, bg=Theme.BG4)
        ctrl.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(ctrl, bg=Theme.BORDER, height=1).pack(fill=tk.X)

        inner_ctrl = tk.Frame(ctrl, bg=Theme.BG4)
        inner_ctrl.pack(fill=tk.X, padx=12, pady=8)

        tk.Label(inner_ctrl, text="Baud:",
                 bg=Theme.BG4, fg=Theme.FG3,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self._baud_var = tk.StringVar(value="115200")
        tk.Entry(inner_ctrl, textvariable=self._baud_var,
                 width=8, bg=Theme.BG3, fg=Theme.FG,
                 font=("Consolas", 9), relief=tk.FLAT, bd=0,
                 insertbackground=Theme.ACCENT2,
                 highlightthickness=1,
                 highlightbackground=Theme.BORDER,
                 highlightcolor=Theme.ACCENT
                 ).pack(side=tk.LEFT, padx=(4, 16), ipady=3)

        self._upload_btn = tk.Button(
            inner_ctrl, text="▶  FPGA'ye Yükle",
            bg=Theme.ACCENT, fg="#FFFFFF",
            activebackground=Theme.ACCENT_H, activeforeground="#FFFFFF",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, bd=0,
            cursor="hand2", padx=14, pady=5,
            command=self._start_upload)
        self._upload_btn.pack(side=tk.RIGHT)

        self._flash_btn = tk.Button(
            inner_ctrl, text="⚡  Loader'ı Karta Yaz",
            bg=Theme.BG3, fg=Theme.YELLOW,
            activebackground=Theme.BORDER, activeforeground=Theme.YELLOW,
            font=("Segoe UI", 9), relief=tk.FLAT, bd=0,
            cursor="hand2", padx=12, pady=5,
            command=self._flash_loader)
        self._flash_btn.pack(side=tk.RIGHT, padx=(0, 8))

        self._selected_port = tk.StringVar(value="")
        self._refresh_fpga()

    def _refresh_fpga(self):
        for w in self._fpga_list_frame.winfo_children():
            w.destroy()

        ports = self._scan_ports()

        if not ports:
            tk.Label(self._fpga_list_frame,
                     text="Bağlı port bulunamadı.",
                     bg=Theme.EDITOR_BG, fg=Theme.FG3,
                     font=("Consolas", 10)).pack(anchor="w", pady=4)
            self._selected_port.set("")
            return

        if self._selected_port.get() not in {p for p, _ in ports}:
            self._selected_port.set(ports[0][0])

        for port, desc in ports:
            row = tk.Frame(self._fpga_list_frame, bg=Theme.BG3, padx=12, pady=8)
            row.pack(fill=tk.X, pady=3)

            tk.Radiobutton(row, variable=self._selected_port, value=port,
                           bg=Theme.BG3, activebackground=Theme.BG3,
                           selectcolor=Theme.ACCENT, relief=tk.FLAT,
                           highlightthickness=0, cursor="hand2"
                           ).pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(row, text="●", bg=Theme.BG3, fg=Theme.GREEN,
                     font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0, 8))

            tk.Label(row, text=port,
                     bg=Theme.BG3, fg=Theme.FG,
                     font=("Consolas", 10, "bold")).pack(side=tk.LEFT)

            tk.Label(row, text=f"  {desc}",
                     bg=Theme.BG3, fg=Theme.FG3,
                     font=("Segoe UI", 9)).pack(side=tk.LEFT)

            row.bind("<Button-1>", lambda _ev, p=port: self._selected_port.set(p))

    def _flash_loader(self):
        port = self._selected_port.get()
        if not port:
            self.log("FPGA: Önce bir port seçin.", "warning")
            return
        self._flash_btn.config(state=tk.DISABLED, text="Çalışıyor…")
        threading.Thread(target=self._flash_worker, args=(port,), daemon=True).start()

    def _find_bitstream(self) -> str | None:
        """loader/rtl altinda hazir .fs bitstream'ini bulur (en yeni)."""
        rtl = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "loader", "rtl"))
        candidates = sorted(
            glob.glob(os.path.join(rtl, "*.fs")),
            key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0] if candidates else None

    def _flash_worker(self, port: str):
        import subprocess, shutil

        def log(msg, tag="info"):
            self.frame.after(0, lambda: self.log(msg, tag))

        def done():
            self.frame.after(0, lambda: self._flash_btn.config(
                state=tk.NORMAL, text="⚡  Loader'ı Karta Yaz"))

        openfpga = shutil.which("openFPGALoader")
        if not openfpga:
            log("openFPGALoader bulunamadı (brew install openFPGALoader).", "error")
            done(); return

        fs = self._find_bitstream()
        if not fs:
            log("Bitstream (.fs) bulunamadı — loader/rtl altina .fs koyun "
                "(Gowin EDA ile uretilir).", "error")
            done(); return

        log(f"─── Loader bitstream karta yaziliyor ───", "info")
        log(f"Bitstream: {os.path.basename(fs)}", "info")

        # Once kalici (flash), olmazsa gecici (SRAM) yukle
        flash_cmd = f'{openfpga} -b tangnano9k -f "{fs}"'
        r = subprocess.run(flash_cmd, shell=True, capture_output=True, text=True)
        mode = "flash (kalici)"
        if r.returncode != 0:
            log("Flash modu basarisiz, SRAM (gecici) deneniyor…", "warning")
            flash_cmd = f'{openfpga} -b tangnano9k "{fs}"'
            r = subprocess.run(flash_cmd, shell=True, capture_output=True, text=True)
            mode = "SRAM (gecici)"

        if r.returncode != 0:
            log("Karta yazma hatasi:\n" + (r.stderr or r.stdout)[-500:], "error")
            done(); return

        log(f"✓ Loader karta yuklendi ({mode}). Artik ▶ FPGA'ye Yukle kullanabilirsin.",
            "success")
        done()

    def _start_upload(self):
        port = self._selected_port.get()
        if not port:
            self.log("FPGA: Önce bir port seçin.", "warning")
            return

        bin_data = self.get_bin_data()
        if bin_data is None:
            self.log("FPGA: Önce Build çalıştırın.", "warning")
            return

        try:
            baud = int(self._baud_var.get())
        except ValueError:
            self.log("FPGA: Geçersiz baud değeri.", "warning")
            return

        self._upload_btn.config(state=tk.DISABLED, text="Yükleniyor…")
        threading.Thread(target=self._upload_worker,
                         args=(port, baud, bin_data),
                         daemon=True).start()

    def _upload_worker(self, port: str, baud: int, bin_data: bytes):
        def log(msg, tag="info"):
            self.frame.after(0, lambda: self.log(msg, tag))

        def done(ok: bool):
            label = "▶  FPGA'ye Yükle"
            self.frame.after(0, lambda: self._upload_btn.config(
                state=tk.NORMAL, text=label))

        try:
            import serial
        except ImportError:
            log("FPGA: pyserial bulunamadı — pip install pyserial", "error")
            done(False)
            return

        SYNC0, SYNC1 = 0xAA, 0x55
        CMD_WRITE, CMD_RUN = 0x01, 0x02
        ACK, NACK_BYTE = 0x06, 0x15
        CHUNK = 64
        RETRIES = 5
        TIMEOUT = 2.0

        def crc16(data: bytes) -> int:
            crc = 0xFFFF
            for b in data:
                crc ^= b << 8
                for _ in range(8):
                    crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
                crc &= 0xFFFF
            return crc

        def build_write(addr: int, words: list) -> bytes:
            body = bytearray([CMD_WRITE])
            body += addr.to_bytes(4, "big")
            body.append(len(words))
            for w in words:
                body += (w & 0xFFFFFFFF).to_bytes(4, "big")
            crc = crc16(bytes(body))
            return bytes([SYNC0, SYNC1]) + bytes(body) + crc.to_bytes(2, "big")

        def build_run() -> bytes:
            crc = crc16(bytes([CMD_RUN]))
            return bytes([SYNC0, SYNC1, CMD_RUN]) + crc.to_bytes(2, "big")

        def send(ser, pkt: bytes) -> bool:
            for attempt in range(1, RETRIES + 1):
                ser.reset_input_buffer()
                ser.write(pkt)
                ser.flush()
                import time
                deadline = time.time() + TIMEOUT
                while time.time() < deadline:
                    resp = ser.read(1)
                    if resp and resp[0] == ACK:
                        return True
                    if resp and resp[0] == NACK_BYTE:
                        log(f"  NACK — yeniden gönderiliyor ({attempt}/{RETRIES})", "warning")
                        break
                else:
                    log(f"  Zaman aşımı ({attempt}/{RETRIES})", "warning")
            return False

        # .bin → word listesi (little-endian)
        data = bin_data
        if len(data) % 4:
            data += b"\x00" * (4 - len(data) % 4)
        words = [int.from_bytes(data[i:i+4], "little") for i in range(0, len(data), 4)]

        log(f"─── FPGA yükleme başladı → {port} @ {baud} ───", "info")
        log(f"Program: {len(words)} word / {len(words)*4} byte", "info")

        try:
            ser = serial.Serial(port, baud, timeout=0.1)
        except serial.SerialException as e:
            log(f"FPGA: Port açılamadı — {e}", "error")
            done(False)
            return

        import time
        time.sleep(0.2)

        sent = 0
        ok = True
        for i in range(0, len(words), CHUNK):
            chunk = words[i:i + CHUNK]
            addr  = i * 4
            pkt   = build_write(addr, chunk)
            if not send(ser, pkt):
                log(f"FPGA: 0x{addr:08X} adresine yazılamadı (ACK yok).", "error")
                if i == 0:
                    log("İpucu: Kart önceki programı çalıştırıyor olabilir. "
                        "Karttaki S1 reset butonuna basıp tekrar yükleyin.", "warning")
                ok = False
                break
            sent += len(chunk)
            log(f"  WRITE @0x{addr:08X}  {len(chunk):>3} word → ACK  ({sent}/{len(words)})", "success")

        if ok:
            if send(ser, build_run()):
                log("RUN → ACK  ✓  CPU çalışmaya başladı (PC=0x0)", "success")
            else:
                log("FPGA: RUN onaylanamadı.", "error")
                ok = False

        ser.close()
        done(ok)

    # ── Port tarama ───────────────────────────────────────────────────

    @staticmethod
    def _scan_ports() -> list[tuple[str, str]]:
        results = []

        if sys.platform.startswith("win"):
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"HARDWARE\DEVICEMAP\SERIALCOMM")
                i = 0
                while True:
                    try:
                        _, val, _ = winreg.EnumValue(key, i)
                        results.append((val, ""))
                        i += 1
                    except OSError:
                        break
            except Exception:
                pass
        else:
            patterns = ["/dev/tty.usbserial-*", "/dev/tty.usbmodem*",
                        "/dev/ttyUSB*", "/dev/ttyACM*"]
            seen: set[str] = set()
            for pat in patterns:
                for path in sorted(glob.glob(pat)):
                    if path in seen:
                        continue
                    seen.add(path)
                    name = os.path.basename(path)
                    if "usbserial" in name:
                        desc = "USB-Serial (FTDI / Tang Nano)"
                    elif "usbmodem" in name:
                        desc = "USB Modem"
                    elif "ttyUSB" in name:
                        desc = "USB-Serial"
                    elif "ttyACM" in name:
                        desc = "USB CDC/ACM"
                    else:
                        desc = ""
                    results.append((path, desc))

        try:
            from serial.tools import list_ports
            serial_map = {p.device: p.description for p in list_ports.comports()}
            enriched = []
            for port, desc in results:
                enriched.append((port, serial_map.get(port, desc) or desc))
            return enriched
        except ImportError:
            return results

    # ── Metin sekmeleri ───────────────────────────────────────────────

    def _make_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self._notebook, bg=Theme.EDITOR_BG)
        self._notebook.add(frame, text=f"  {title}  ")

        text = tk.Text(frame,
                       bg=Theme.EDITOR_BG, fg=Theme.FG,
                       font=("Consolas", 10),
                       relief=tk.FLAT, bd=0,
                       padx=14, pady=10,
                       state=tk.DISABLED,
                       selectbackground=Theme.ACCENT,
                       selectforeground=Theme.FG,
                       insertbackground=Theme.ACCENT2,
                       wrap=tk.NONE,
                       spacing1=1, spacing3=1)

        text.tag_config("addr",    foreground=Theme.FG2)
        text.tag_config("hex",     foreground=Theme.ACCENT2)
        text.tag_config("section", foreground=Theme.PURPLE, font=("Consolas", 10, "bold"))
        text.tag_config("label",   foreground=Theme.YELLOW)
        text.tag_config("sep",     foreground=Theme.FG3)

        sy = ttk.Scrollbar(frame, command=text.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=text.xview)
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
        tabs = {'hex': 0, 'listing': 1, 'symtab': 2,
                'object': 3, 'map': 4, 'mem': 5, 'fpga': 6}
        if name in tabs:
            self._notebook.select(tabs[name])

    def clear(self):
        self.set_content()

    def _set_text(self, widget: tk.Text, content: str):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state=tk.DISABLED)
