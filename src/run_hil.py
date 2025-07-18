import sys
import os

# src dizinini sys.path'e ekle
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from hil.hil_main import HILMainWindow

if __name__ == "__main__":
    app = HILMainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop() 