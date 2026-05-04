# gui/theme.py
import tkinter.ttk as ttk

class Theme:
    # Ana renkler — koyu mavi/gri bazlı modern tema
    BG        = "#0F1117"   # en koyu, pencere zemini
    BG2       = "#161B22"   # panel arkaplanı
    BG3       = "#1C2333"   # hover / input arkaplanı
    BG4       = "#21262D"   # toolbar, header
    BORDER    = "#30363D"   # ince ayırıcılar

    # Vurgu renkleri
    ACCENT    = "#2F81F7"   # mavi — birincil aksyon
    ACCENT_H  = "#1F6CE0"   # mavi hover
    ACCENT2   = "#58A6FF"   # açık mavi — başlık / etiket
    GREEN     = "#3FB950"   # başarı
    RED       = "#F85149"   # hata
    YELLOW    = "#D29922"   # uyarı
    PURPLE    = "#BC8CFF"   # özel vurgu
    TEAL      = "#39D353"   # ok ikonu

    # Metin
    FG        = "#E6EDF3"   # ana metin
    FG2       = "#7D8590"   # soluk metin
    FG3       = "#8B949E"   # placeholder / pasif

    # Editör
    EDITOR_BG = "#0D1117"
    LINE_NUM  = "#3B434B"

    # Özel
    SUCCESS   = GREEN
    ERROR     = RED
    WARNING   = YELLOW

    @classmethod
    def setup_ttk_styles(cls):
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook (sekmeler)
        style.configure("TNotebook",
                        background=cls.BG2,
                        borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab",
                        background=cls.BG2,
                        foreground=cls.FG2,
                        padding=[16, 7],
                        font=("Segoe UI", 9),
                        borderwidth=0,
                        relief="flat")
        style.map("TNotebook.Tab",
                  background=[("selected", cls.BG4)],
                  foreground=[("selected", cls.FG)])

        style.configure("TFrame", background=cls.BG)

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                        background=cls.BG3,
                        troughcolor=cls.BG,
                        arrowcolor=cls.FG2,
                        borderwidth=0,
                        relief="flat",
                        width=8)
        style.map("Vertical.TScrollbar",
                  background=[("active", cls.BORDER)])

        style.configure("Horizontal.TScrollbar",
                        background=cls.BG3,
                        troughcolor=cls.BG,
                        arrowcolor=cls.FG2,
                        borderwidth=0,
                        relief="flat",
                        width=8)
