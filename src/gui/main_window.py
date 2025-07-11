from gui.control_menu import ControlMenu
from gui.config_menu import ConfigMenu
from gui.serial_monitor import SerialMonitor
import customtkinter as ctk
from utils.logger import bring_to_front_and_center
from core.config import load_config, save_config
from core.serial_manager import serial_manager

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FNSS Arduino Control Project")
        self.geometry("480x400")
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        # Uygulama ikonu
        try:
            import tkinter as tk
            import os
            logo_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
            logo_path_png = os.path.normpath(os.path.join(logo_dir, "logo.png"))
            logo_path_ico = os.path.normpath(os.path.join(logo_dir, "indir.ico"))

            if os.path.exists(logo_path_ico):
                # Windows .ico format (en sağlam yol)
                self.iconbitmap(default=logo_path_ico)
            elif os.path.exists(logo_path_png):
                # PNG yolunu tkinter.PhotoImage ile dene (Tk >=8.6 gerektirir)
                try:
                    icon_img = tk.PhotoImage(file=logo_path_png)
                    self.iconphoto(False, icon_img)
                except Exception as e:
                    print(f"iconphoto PNG yüklenemedi: {e}")
        except Exception:
            pass
        bring_to_front_and_center(self)

        # Port seçici kaldırıldı – otomatik algılama kullanılıyor

        # Auto serial connect if enabled in config
        self.after(100, self._init_serial)

    def _init_serial(self):
        # Otomatik port tarama kaldırıldı; yalnızca config'teki port denenir
        cfg = load_config()

        port = cfg.get("serial_port")
        baud = cfg.get("baudrate", 9600)

        serial_manager.connect(port, baud)

        self.serial_monitor = None
        self._build_menu()


    def _build_menu(self):
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=40, pady=40)

        frame.grid_rowconfigure((0,1,2,3,4), weight=0)
        frame.grid_columnconfigure(0, weight=1)

        # Logo – assets/logo.png varsa
        import os
        try:
            from PIL import Image
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            if os.path.exists(logo_path):
                logo_img = ctk.CTkImage(light_image=Image.open(logo_path), size=(152, 40))
                ctk.CTkLabel(frame, image=logo_img, text="").grid(row=0, column=0, pady=(20, 25), sticky="n")
            else:
                raise FileNotFoundError
        except Exception:
            ctk.CTkLabel(frame, text="FNSS", font=("Arial", 24, "bold")).grid(row=0, column=0, pady=(20, 25), sticky="n")

        btn_ctrl = ctk.CTkButton(frame, text="Kontrol Modu", font=("Arial", 16), height=48, width=220, command=self.open_control_mode)
        btn_ctrl.grid(row=1, column=0, pady=12, sticky="n")

        btn_config = ctk.CTkButton(frame, text="Konfigürasyon Modu", font=("Arial", 16), height=48, width=220, command=self.open_config_mode)
        btn_config.grid(row=2, column=0, pady=12, sticky="n")

        btn_serial = ctk.CTkButton(frame, text="Serial Monitor", font=("Arial", 16), height=48, width=220, command=self.open_serial_monitor)
        btn_serial.grid(row=3, column=0, pady=12, sticky="n")

    def open_control_mode(self):
        ControlMenu(self)

    def open_config_mode(self):
        ConfigMenu(self)

    def open_serial_monitor(self):
        if self.serial_monitor is None or not self.serial_monitor.winfo_exists():
            self.serial_monitor = SerialMonitor(self)
        else:
            self.serial_monitor.lift()
            self.serial_monitor.focus_force()

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
