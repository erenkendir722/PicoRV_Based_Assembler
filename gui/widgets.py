# gui/widgets.py
import tkinter as tk

def make_btn(parent, text, command, bg, fg, hover_bg, font_cfg, padx=14, pady=6):
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
