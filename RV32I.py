# RV32I.py
# PicoRV İşlemci Alt Kümesi (RV32I) için Assembler
# Ana giriş noktası

import tkinter as tk
from gui import RV32IAssemblerGUI

if __name__ == "__main__":
    root = tk.Tk()
    app  = RV32IAssemblerGUI(root)
    root.mainloop()
