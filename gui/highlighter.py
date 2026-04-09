# highlighter.py
# RV32I Assembler - Syntax Highlighter
# Bir tk.Text widget'ına bağlanır ve RV32I assembly kodunu renklendirir.

import re
import tkinter as tk
from core.opcode_table import OPTAB, DIRECTIVES, REGISTERS


# ─────────────────────────────────────────
# Renk sabitleri
# ─────────────────────────────────────────
COLORS = {
    "mnemonic":  "#569CD6",   # mavi       – ADD, ADDI, LW …
    "directive": "#C586C0",   # mor        – .text, .data, .word …
    "register":  "#9CDCFE",   # açık mavi  – x0..x31, zero, sp, ra …
    "label":     "#DCDCAA",   # sarı       – LOOP:, MAIN: …
    "number":    "#B5CEA8",   # yeşil      – 10, 0xFF, -1 …
    "comment":   "#6A9955",   # koyu yeşil – # … veya ; …
}

# Tag isimleri (widget üzerindeki tag'lerle eşleşir)
TAG = {k: f"hl_{k}" for k in COLORS}

# ─────────────────────────────────────────
# Derleme-zamanı sabitler (OPTAB'tan türetilir)
# ─────────────────────────────────────────
_MNEMONICS  = frozenset(OPTAB.keys())                        # uppercase
_DIRECTIVES = frozenset(d.upper().lstrip('.') for d in DIRECTIVES)
_REGISTERS  = frozenset(REGISTERS.keys())                   # lowercase

_RE_NUMBER  = re.compile(r'\b(0[xX][0-9A-Fa-f]+|0[bB][01]+|-?\d+)\b')
_RE_LABEL   = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', re.MULTILINE)
_RE_COMMENT = re.compile(r'[#;].*$', re.MULTILINE)


class Highlighter:
    """
    Verilen tk.Text widget'ına RV32I assembly syntax highlighting uygular.

    Kullanım:
        hl = Highlighter(editor_widget)
        hl.apply()          # tüm içeriği renklendir
    """

    def __init__(self, widget: tk.Text):
        self._w = widget
        self._configure_tags()

    # ─────────────────────────────────────────
    # Tag konfigürasyonu (bir kez yapılır)
    # ─────────────────────────────────────────
    def _configure_tags(self):
        font_normal = ("Consolas", 11)
        font_italic = ("Consolas", 11, "italic")
        self._w.tag_config(TAG["mnemonic"],  foreground=COLORS["mnemonic"],  font=font_normal)
        self._w.tag_config(TAG["directive"], foreground=COLORS["directive"],  font=font_normal)
        self._w.tag_config(TAG["register"],  foreground=COLORS["register"],   font=font_normal)
        self._w.tag_config(TAG["label"],     foreground=COLORS["label"],      font=font_normal)
        self._w.tag_config(TAG["number"],    foreground=COLORS["number"],     font=font_normal)
        self._w.tag_config(TAG["comment"],   foreground=COLORS["comment"],    font=font_italic)

    # ─────────────────────────────────────────
    # Ana metot
    # ─────────────────────────────────────────
    def apply(self):
        """Widget içeriğini baştan sona renklendirir."""
        self._clear_tags()
        content = self._w.get("1.0", tk.END)
        comment_spans = self._apply_comments(content)
        self._apply_labels(content, comment_spans)
        self._apply_numbers(content, comment_spans)
        self._apply_tokens(content, comment_spans)

    # ─────────────────────────────────────────
    # Adım 1: Yorumlar
    # ─────────────────────────────────────────
    def _apply_comments(self, content: str) -> list[tuple[int, int]]:
        """Yorum aralıklarını işaretler; diğer adımların üzerine basmaması için döndürür."""
        spans = []
        for m in _RE_COMMENT.finditer(content):
            self._w.tag_add(TAG["comment"],
                            self._pos(content, m.start()),
                            self._pos(content, m.end()))
            spans.append((m.start(), m.end()))
        return spans

    # ─────────────────────────────────────────
    # Adım 2: Label tanımları
    # ─────────────────────────────────────────
    def _apply_labels(self, content: str, comment_spans: list):
        for m in _RE_LABEL.finditer(content):
            if not _in_spans(m.start(1), comment_spans):
                self._w.tag_add(TAG["label"],
                                self._pos(content, m.start(1)),
                                self._pos(content, m.end(1)))

    # ─────────────────────────────────────────
    # Adım 3: Sayılar
    # ─────────────────────────────────────────
    def _apply_numbers(self, content: str, comment_spans: list):
        for m in _RE_NUMBER.finditer(content):
            if not _in_spans(m.start(), comment_spans):
                self._w.tag_add(TAG["number"],
                                self._pos(content, m.start()),
                                self._pos(content, m.end()))

    # ─────────────────────────────────────────
    # Adım 4: Token bazlı (mnemonic, direktif, register)
    # ─────────────────────────────────────────
    def _apply_tokens(self, content: str, comment_spans: list):
        line_start = 0
        for lineno, line in enumerate(content.split('\n'), start=1):
            clean  = re.split(r'[#;]', line)[0]   # yorum öncesi
            tokens = clean.split()

            # Label ise ilk token(lar)ı atla
            skip = 0
            if tokens and tokens[0].endswith(':'):
                skip = 1
            elif len(tokens) > 1 and tokens[1] == ':':
                skip = 2

            col_cursor = 0
            for i, tok in enumerate(tokens):
                # Token'ın satır içi sütununu bul
                col = clean.find(tok, col_cursor)
                col_cursor = col + len(tok)
                abs_pos = line_start + col

                if _in_spans(abs_pos, comment_spans):
                    continue

                tag = _classify_token(tok, i, skip)
                if tag:
                    tok_clean = tok.rstrip(',')
                    self._w.tag_add(tag,
                                    f"{lineno}.{col}",
                                    f"{lineno}.{col + len(tok_clean)}")

            line_start += len(line) + 1   # +1 for '\n'

    # ─────────────────────────────────────────
    # Yardımcılar
    # ─────────────────────────────────────────
    def _clear_tags(self):
        for tag in TAG.values():
            self._w.tag_remove(tag, "1.0", tk.END)

    @staticmethod
    def _pos(content: str, offset: int) -> str:
        """Karakter offset'ini 'satır.sütun' indeksine çevirir."""
        line = content[:offset].count('\n') + 1
        col  = offset - content[:offset].rfind('\n') - 1
        return f"{line}.{col}"


# ─────────────────────────────────────────
# Modül düzeyinde yardımcılar
# ─────────────────────────────────────────

def _in_spans(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def _classify_token(tok: str, index: int, mnemonic_index: int) -> str | None:
    """
    Bir token için uygun tag adını döndürür; eşleşme yoksa None.

    index           : token'ın satır içindeki sırası (0-tabanlı)
    mnemonic_index  : bu satırda mnemonic'in beklenen indeksi (label atlandıktan sonra)
    """
    tok_bare  = tok.rstrip(',')
    tok_upper = tok_bare.upper().lstrip('.')
    tok_lower = tok_bare.lower()

    if index == mnemonic_index:
        if tok_upper in _DIRECTIVES:
            return TAG["directive"]
        if tok_upper in _MNEMONICS:
            return TAG["mnemonic"]

    if tok_lower in _REGISTERS:
        return TAG["register"]

    return None
