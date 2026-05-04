# gui/widgets.py
import tkinter as tk

def make_btn(parent, text, command, bg, fg, hover_bg,
             font_cfg=("Segoe UI", 9), padx=12, pady=5,
             radius=0, border_color=None):
    """
    macOS'ta tk.Button renkleri çalışmadığı için Label tabanlı custom buton.
    Opsiyonel border_color ile ince kenarlık desteklenir.
    """
    outer_bg = border_color if border_color else bg
    frame = tk.Frame(parent, bg=outer_bg, cursor="hand2",
                     padx=1 if border_color else 0,
                     pady=1 if border_color else 0)
    inner = tk.Frame(frame, bg=bg, cursor="hand2")
    inner.pack(fill=tk.BOTH, expand=True)

    lbl = tk.Label(inner, text=text, bg=bg, fg=fg,
                   font=font_cfg, padx=padx, pady=pady, cursor="hand2")
    lbl.pack()

    def on_enter(_):
        inner.config(bg=hover_bg)
        lbl.config(bg=hover_bg)

    def on_leave(_):
        inner.config(bg=bg)
        lbl.config(bg=bg)

    def on_click(_):
        command()

    for widget in (frame, inner, lbl):
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        widget.bind("<Button-1>", on_click)

    return frame


def make_icon_btn(parent, text, command, size=22,
                   bg=None, fg=None, hover_bg=None):
    """Küçük kare ikon butonu."""
    from gui.theme import Theme
    _bg = bg or Theme.BG4
    _fg = fg or Theme.FG2
    _hbg = hover_bg or Theme.BG3

    frame = tk.Frame(parent, bg=_bg, width=size, height=size, cursor="hand2")
    frame.pack_propagate(False)
    lbl = tk.Label(frame, text=text, bg=_bg, fg=_fg,
                   font=("Segoe UI", 10), cursor="hand2")
    lbl.place(relx=0.5, rely=0.5, anchor="center")

    def on_enter(_):
        frame.config(bg=_hbg); lbl.config(bg=_hbg)
    def on_leave(_):
        frame.config(bg=_bg); lbl.config(bg=_bg)
    def on_click(_):
        command()

    for w in (frame, lbl):
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)
        w.bind("<Button-1>", on_click)

    return frame
