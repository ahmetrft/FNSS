from gui.control_menu import ControlMenu
from gui.config_menu import ConfigMenu
from gui.serial_monitor import SerialMonitor
import customtkinter as ctk
from utils.logger import bring_to_front_and_center
from core.config import load_config, save_config
from core.serial_manager import serial_manager
import threading
import tkinter.messagebox as messagebox
import os
import sys

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "src", "assets", filename)
    else:
        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", filename))

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FNSS Arduino Control Project")
        self.geometry("480x420")  # Orijinal boyuta döndürdüm
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        # Uygulama ikonu
        try:
            import tkinter as tk
            logo_path_png = get_asset_path("logo.png")
            logo_path_ico = get_asset_path("indir.ico")

            if os.path.exists(logo_path_ico):
                self.iconbitmap(default=logo_path_ico)
            elif os.path.exists(logo_path_png):
                try:
                    icon_img = tk.PhotoImage(file=logo_path_png)
                    self.iconphoto(False, icon_img)
                except Exception as e:
                    print(f"iconphoto PNG yüklenemedi: {e}")
        except Exception:
            pass
        bring_to_front_and_center(self)

        self.connection_status_label = None
        self.arduino_found = False
        self.serial_monitor = None

        # Bağlantı callback'ini ekle
        serial_manager.add_connection_callback(self._on_connection_changed)
        serial_manager.add_message_callback(self._on_message_received)

        self.after(100, self._init_serial)

    def _init_serial(self):
        # Otomatik Arduino bağlantısı başlat
        self._auto_connect()

        self.serial_monitor = None
        self._build_menu()

    def _auto_connect(self):
        """Otomatik Arduino bağlantısı"""
        # Thread kullanmadan doğrudan port tarama yap
        arduino_port = serial_manager.find_arduino_port(timeout=3.0)
        if arduino_port:
            # Port bulundu, bağlantı kur
            if serial_manager.connect(arduino_port, serial_manager.baudrate):
                self.arduino_found = True
            else:
                self._show_arduino_error()
        else:
            self._show_arduino_error()

    def _show_arduino_error(self):
        """Arduino bulunamadığında uyarı penceresi göster"""
        messagebox.showwarning(
            "Arduino Bulunamadı",
            "Bağlı portlarda Arduino bulunamadı!\n\n"
            "Lütfen şunları kontrol edin:\n"
            "• Arduino'nun USB kablosu ile bağlı olduğundan emin olun\n"
            "• Arduino kodunun yüklü olduğunu kontrol edin"
        )

    def _on_connection_changed(self, connected: bool):
        # Pencere kapalıysa hata verme
        try:
            if self.connection_status_label:
                stats = serial_manager.get_stats()
                if connected:
                    self.connection_status_label.configure(
                        text=f"✅ Bağlı: {stats['port_name']} ({stats['baudrate']} baud)",
                        text_color="green"
                    )
                else:
                    self.connection_status_label.configure(
                        text="❌ Bağlantı yok",
                        text_color="red"
                    )
        except Exception:
            pass

    def _on_message_received(self, source: str, message: str):
        """Mesaj alındığında çağrılır"""
        if source == "Alınan" and "Bağlantı koptu" in message:
            # Bağlantı koptuğunda durumu güncelle
            if self.connection_status_label:
                self.connection_status_label.configure(
                    text="❌ Bağlantı yok",
                    text_color="red"
                )

    def _build_menu(self):
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both", padx=40, pady=40)

        frame.grid_rowconfigure((0,1,2,3,4,5), weight=0)
        frame.grid_columnconfigure(0, weight=1)

        # Logo – assets/logo.png varsa
        import os
        try:
            from PIL import Image
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            if os.path.exists(logo_path):
                logo_img = ctk.CTkImage(light_image=Image.open(logo_path), size=(152, 40))
                ctk.CTkLabel(frame, image=logo_img, text="").grid(row=0, column=0, pady=(20, 15), sticky="n")
            else:
                raise FileNotFoundError
        except Exception:
            ctk.CTkLabel(frame, text="FNSS", font=("Arial", 24, "bold")).grid(row=0, column=0, pady=(20, 15), sticky="n")

        btn_ctrl = ctk.CTkButton(frame, text="Kontrol Modu", font=("Arial", 16), height=48, width=220, command=self.open_control_mode)
        btn_ctrl.grid(row=1, column=0, pady=12, sticky="n")

        btn_config = ctk.CTkButton(frame, text="Konfigürasyon Modu", font=("Arial", 16), height=48, width=220, command=self.open_config_mode)
        btn_config.grid(row=2, column=0, pady=12, sticky="n")

        btn_serial = ctk.CTkButton(frame, text="Serial Monitor", font=("Arial", 16), height=48, width=220, command=self.open_serial_monitor)
        btn_serial.grid(row=3, column=0, pady=12, sticky="n")

        # Bağlantı durumu en alta alındı
        stats = serial_manager.get_stats()
        if stats['is_connected']:
            status_text = f"✅ Bağlı: {stats['port_name']} ({stats['baudrate']} baud)"
            status_color = "green"
        else:
            status_text = "❌ Bağlantı yok"
            status_color = "red"
        self.connection_status_label = ctk.CTkLabel(
            frame, 
            text=status_text, 
            font=("Arial", 12),
            text_color=status_color
        )
        self.connection_status_label.grid(row=5, column=0, pady=(20, 0), sticky="s")

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
