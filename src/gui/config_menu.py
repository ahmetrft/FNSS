import customtkinter as ctk
from utils.logger import bring_to_front_and_center, get_asset_path
import serial
import serial.tools.list_ports
# PinManager'ı da ekle
from core.config import load_config, save_config, DIGITAL_PINS, ANALOG_PINS, PWM_DIGITAL_PINS
from core.pin_manager import pin_manager
import os

class ConfigMenu(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Konfigürasyon Modu - Arduino Pin Kontrol")
        self.geometry("700x600")  # genişletildi
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        # İkonu ayarla
        try:
            ico_path = get_asset_path("indir.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(default=ico_path)
        except Exception:
            pass
        # Konfigürasyonu çek
        self.config_data = load_config()
        self._build_layout()
        bring_to_front_and_center(self)

        # Pencere açılırken Arduino'ya komut gönderme – kullanıcı Kaydet dediğinde gönderilecek.

    # load_config ve save_config artık core.config üzerinden geliyor

    def get_available_ports(self):
        """Kullanılabilir seri portları listeler."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # Başlık
        ctk.CTkLabel(main_frame, text="Konfigürasyon Ayarları", font=("Arial", 20, "bold")).grid(row=0, column=0, pady=(0, 20))

        # (Seri Port Ayarları bölümü kaldırıldı)

        # --- Pin Ayarları ---
        pin_cfg_frame = ctk.CTkFrame(main_frame)
        pin_cfg_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=20)
        pin_cfg_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pin_cfg_frame, text="Pin Ayarları", font=("Arial", 16, "bold"), anchor="center", justify="center").grid(row=0, column=0, pady=(10, 15), sticky="ew")

        # Scrollable area
        scroll = ctk.CTkScrollableFrame(pin_cfg_frame, height=220)
        scroll.grid(row=1, column=0, sticky="ew")
        scroll.grid_columnconfigure((0,1,2,3), weight=1)

        ctk.CTkLabel(scroll, text="Pin (Aktif)", font=("Arial", 13, "bold")).grid(row=0, column=0, padx=10)
        ctk.CTkLabel(scroll, text="Mod", font=("Arial", 13, "bold")).grid(row=0, column=1, padx=10)
        ctk.CTkLabel(scroll, text="Tür", font=("Arial", 13, "bold")).grid(row=0, column=2, padx=10)

        self.pin_widgets = {}

        def add_pin_row(pin_name, default):
            r = len(self.pin_widgets)+1
            # Aktif toggle (switch) – metni pin adı şeklinde
            active_var = ctk.BooleanVar(value=(default.get("mode", "output") != "pas"))
            active_switch = ctk.CTkSwitch(scroll, text=f"{pin_name}", variable=active_var, width=60)
            active_switch.grid(row=r, column=0, padx=(70, 4), pady=6, sticky="w")

            # "pas" kullanıcıya gösterilmeyecek, sadece toggle ile pasif yapılacak
            init_mode = default.get("mode", "output")
            if init_mode == "pas":
                init_mode = "output"  # OptionMenu'de gösterilecek değer

            mode_var = ctk.StringVar(value=init_mode)
            mode_opt = ctk.CTkOptionMenu(scroll, variable=mode_var, values=["input", "output"], width=80)
            mode_opt.grid(row=r, column=1, padx=10)

            # --- Tür seçenekleri ---
            # Dijital pinler
            if pin_name.isdigit():
                if int(pin_name) in PWM_DIGITAL_PINS:
                    base_values = ["digital", "pwm"]
                else:
                    base_values = ["digital"]
                # Dijital pinlerde INPUT modunda yalnızca 'digital' seçeneği gösterilsin
                def _on_dig_mode_change(*_):
                    m = mode_var.get()
                    if m == "input":
                        type_opt.configure(values=["digital"])
                        type_var.set("digital")
                    else:
                        type_opt.configure(values=base_values)

                def _dig_wrapper(*_):
                    _on_dig_mode_change()
                    self._persist_config()

                mode_var.trace_add("write", _dig_wrapper)
            else:  # Analog pin
                base_values = ["analog", "digital"]

            type_var = ctk.StringVar()
            type_opt = ctk.CTkOptionMenu(scroll, variable=type_var, values=base_values, width=90)
            type_opt.grid(row=r, column=2, padx=10)

            # Varsayılan değer seçimi (geçerli değilse ilk eleman)
            init_val = default.get("type", base_values[0])
            if init_val not in base_values:
                init_val = base_values[0]
            type_var.set(init_val)

            # Analog pinlerde mode değişimine göre tür listesini güncelle
            if not pin_name.isdigit():
                def _on_mode_change(*_):
                    m = mode_var.get()
                    if m == "output":
                        # Sadece dijital
                        type_opt.configure(values=["digital"])
                        type_var.set("digital")
                    else:
                        type_opt.configure(values=["analog", "digital"])
                        if type_var.get() not in ("analog", "digital"):
                            type_var.set("analog")

                def _analog_wrapper(*_):
                    _on_mode_change()
                    self._persist_config()

                mode_var.trace_add("write", _analog_wrapper)
                _on_mode_change()

            # Aktif/pasif switch callback
            def _on_active_change(*_ , pn=pin_name):
                vars_d = self.pin_widgets[pn]
                if vars_d["active"].get():
                    # yeniden etkin – eğer mode 'pas' ise 'output' yap
                    if vars_d["mode"].get() == "pas":
                        vars_d["mode"].set("output")
                    vars_d["mode_opt"].configure(state="normal")
                    vars_d["type_opt"].configure(state="normal")
                else:
                    # Pasif yap – OptionMenu devre dışı, değer kayda alınırken 'pas' olarak kaydedilecek
                    # mode StringVar'ı değiştirmiyoruz, sadece menüyü kapatıyoruz
                    vars_d["mode_opt"].configure(state="disabled")
                    vars_d["type_opt"].configure(state="disabled")

            def _active_wrapper(*_):
                _on_active_change()
                self._persist_config()

            active_var.trace_add("write", _active_wrapper)

            # Başlangıçta pasifse option menüleri disable
            if not active_var.get():
                mode_opt.configure(state="disabled")
                type_opt.configure(state="disabled")

            self.pin_widgets[pin_name] = {
                "active": active_var,
                "mode": mode_var,
                "type": type_var,
                "mode_opt": mode_opt,
                "type_opt": type_opt
            }

        # Add all pins
        pins_order = [str(p) for p in DIGITAL_PINS] + ANALOG_PINS
        for pn in pins_order:
            add_pin_row(pn, self.config_data.get("pins", {}).get(pn, {}))

        # (Bağlantı Testi bölümü kaldırıldı)

        # --- Butonlar ---
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15), padx=20)

        # 6 sütun: 0 ve 5 boşluk (spacer), 1-4 butonlar
        # Sağ ve sol boşlukları eşitlemek için her iki spacer'a da aynı weight veriyoruz
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(5, weight=1)
        for i in range(1, 5):
            button_frame.grid_columnconfigure(i, weight=0)

        save_button = ctk.CTkButton(
            button_frame,
            text="Uygula",
            command=self.apply_settings,
            fg_color="#34C759",
            width=120
        )
        save_button.grid(row=0, column=1, padx=(0, 8), pady=10, sticky="ew")

        reset_button = ctk.CTkButton(
            button_frame,
            text="Varsayılana Döndür",
            command=self.reset_settings,
            fg_color="#FF9500",
            width=140
        )
        reset_button.grid(row=0, column=2, padx=8, pady=10, sticky="ew")

        readall_button = ctk.CTkButton(
            button_frame,
            text="Tümü Okuma",
            command=self.set_all_read_mode,
            fg_color="#5856D6",
            width=120
        )
        readall_button.grid(row=0, column=3, padx=8, pady=10, sticky="ew")

        writeall_button = ctk.CTkButton(
            button_frame,
            text="Tümü Yazma",
            command=self.set_all_write_mode,
            fg_color="#007AFF",
            width=120
        )
        # Son butonun sağında ekstra boşluk olmaması için sağdaki padx'i sıfır yapıyoruz
        writeall_button.grid(row=0, column=4, padx=(8, 0), pady=10, sticky="ew")

        # --- Bilgi ---
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.grid(row=3, column=0, sticky="ew", padx=20)
        
        info_text = """
        Konfigürasyon Ayarları:
        • Bu pencerede pinlerin modlarını ve türlerini ayarlayabilirsiniz
        • Kaydet butonuna bastığınızda değişiklikler anında Arduino'ya gönderilir
        • Varsayılana Döndür butonuna bastığınızda ayarlar varsayılan değerlerine döner
        • Tümü Okuma butonuna bastığınızda tüm pinleri INPUT yapar
        • Tümü Yazma butonuna bastığınızda tüm pinleri OUTPUT yapar
        """
        ctk.CTkLabel(info_frame, text=info_text, font=("Arial", 11), justify="left").grid(row=0, column=0, padx=10, pady=10, sticky="w")

    def test_connection(self):
        """Seri port bağlantısını test eder."""
        from core.serial_manager import serial_manager
        try:
            port = self.port_var.get()
            baudrate = int(self.baudrate_var.get())

            # Eğer zaten bağlıysa ve ayarlar aynıysa başarı kabul et
            if serial_manager.is_connected and serial_manager.port_name == port and serial_manager.baudrate == baudrate:
                self.test_label.configure(text=f"✓ Port {port} zaten bağlı", text_color="#34C759")
                return

            # Bağlıysa ama farklı port ise bağlantıyı kapatıp yeniden dene
            if serial_manager.is_connected:
                serial_manager.disconnect()

            if serial_manager.connect(port, baudrate):
                self.test_label.configure(text=f"✓ Bağlantı başarılı: {port} @ {baudrate} bps", text_color="#34C759")
            else:
                self.test_label.configure(text="✗ Bağlantı hatası", text_color="#FF3B30")

        except Exception as e:
            self.test_label.configure(text=f"✗ Bağlantı hatası: {str(e)}", text_color="#FF3B30")

    # ----------------- Persist Helpers -----------------
    def _collect_pins_config(self):
        """pin_widgets içeriğini sözlük formatında döndürür"""
        pins_cfg = {}
        for pin, vars_ in self.pin_widgets.items():
            if not vars_["active"].get():
                mode_val = "pas"
            else:
                mode_val = vars_["mode"].get()

            t_val = vars_["type"].get()
            # Analog pinler OUTPUT ise type zorunlu olarak 'digital'
            if not pin.isdigit() and mode_val == "output":
                t_val = "digital"

            pins_cfg[pin] = {
                "mode": mode_val,
                "type": t_val
            }
        return pins_cfg

    def _persist_config(self):
        """Anlık widget değerlerini CONFIG'e ve diske kaydeder"""
        from core import config as cfg
        self.config_data["pins"] = self._collect_pins_config()
        cfg.CONFIG = self.config_data
        save_config()

    # ----------------- Apply Button -----------------
    def apply_settings(self):
        """Mevcut konfigürasyonu diske kaydeder ve Arduino'ya uygular."""
        try:
            # Önce konfigürasyonu kalıcı hale getir
            self._persist_config()

            # Bağlantı kontrolü: Arduino seri bağlantısı yoksa ayarları dosyaya kaydedip uyarı göster
            from core.serial_manager import serial_manager
            if not serial_manager.is_connected:
                # Uygulanamadı, sadece kaydedildi bildir
                
                warn_win = ctk.CTkToplevel(self)
                warn_win.title("Bağlantı Yok")
                warn_win.geometry("340x150")
                warn_win.resizable(False, False)
                bring_to_front_and_center(warn_win)

                ctk.CTkLabel(warn_win, text="✗ Arduino bağlantısı bulunamadı!", font=("Arial", 16, "bold"), text_color="#FF3B30").pack(pady=18)
                ctk.CTkLabel(warn_win, text="Bağlanmadan ayarlar Arduino'ya uygulanamaz.\nAyarlar yine de kaydedildi.", font=("Arial", 12), justify="center").pack(pady=4)
                ctk.CTkButton(warn_win, text="Tamam", command=warn_win.destroy).pack(pady=10)
                return

            # Arduino'ya pin modlarını uygula
            pin_manager.apply_config(self.config_data)

            # Başarı mesajı göster – uygulamayı kapatmaya gerek yok
            info_win = ctk.CTkToplevel(self)
            info_win.title("Başarılı")
            info_win.geometry("280x140")
            info_win.resizable(False, False)
            bring_to_front_and_center(info_win)

            ctk.CTkLabel(info_win, text="✓ Ayarlar uygulandı!", font=("Arial", 16, "bold")).pack(pady=18)
            ctk.CTkLabel(info_win, text="Değişiklikler Arduino'ya gönderildi.", font=("Arial", 12)).pack(pady=4)
            ctk.CTkButton(info_win, text="Tamam", command=info_win.destroy).pack(pady=10)
            
        except Exception as e:
            # Hata mesajı göster
            error_window = ctk.CTkToplevel(self)
            error_window.title("Hata")
            error_window.geometry("300x150")
            error_window.resizable(False, False)
            bring_to_front_and_center(error_window)
            
            ctk.CTkLabel(error_window, text="✗ Hata oluştu!", font=("Arial", 16, "bold"), text_color="#FF3B30").pack(pady=20)
            ctk.CTkLabel(error_window, text=f"Hata: {str(e)}", font=("Arial", 12)).pack(pady=10)
            
            ctk.CTkButton(error_window, text="Tamam", command=error_window.destroy).pack(pady=10)

    def reset_settings(self):
        """Ayarları varsayılan değerlere döndürür ve tüm pinleri aktif yapar."""
        import copy
        from core import config as cfg
        from core.config import DIGITAL_PINS, ANALOG_PINS, PWM_DIGITAL_PINS
        old_config = cfg.load_config()
        last_port = old_config.get("last_successful_port")
        self.config_data = copy.deepcopy(cfg.DEFAULT_CONFIG)
        if last_port:
            self.config_data["last_successful_port"] = last_port

        # Tüm pinleri aktif ve default moda getir
        for pin, v in self.pin_widgets.items():
            # Dijital pinler
            if pin.isdigit():
                v["active"].set(True)
                v["mode"].set("output")
                if int(pin) in PWM_DIGITAL_PINS:
                    v["type"].set("pwm")
                else:
                    v["type"].set("digital")
            else:  # Analog pinler
                v["active"].set(True)
                v["mode"].set("input")
                v["type"].set("analog")
            v["mode_opt"].configure(state="normal")
            v["type_opt"].configure(state="normal")

        # Global CONFIG'i güncelle ve kaydet
        cfg.CONFIG = self.config_data
        cfg.save_config()
        
        # Bilgi mesajı göster
        info_window = ctk.CTkToplevel(self)
        info_window.title("Bilgi")
        info_window.geometry("300x150")
        info_window.resizable(False, False)
        bring_to_front_and_center(info_window)
        
        ctk.CTkLabel(info_window, text="✓ Ayarlar sıfırlandı!", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkLabel(info_window, text="Varsayılan ayarlar yüklendi.", font=("Arial", 12)).pack(pady=10)
        
        ctk.CTkButton(info_window, text="Tamam", command=info_window.destroy).pack(pady=10)

    # ---- Helper methods ----

    def _apply_to_all_pins(self, *, mode: str, pwm_as_digital: bool, active: bool = True):
        """Internal utility to update all pin widget variables."""
        for pin, vars_ in self.pin_widgets.items():
            vars_["active"].set(active)
            vars_["mode"].set(mode if active else "pas")
            # Tür mantığı
            if pin.isdigit():
                p_int = int(pin)
                if p_int in PWM_DIGITAL_PINS and not pwm_as_digital:
                    vars_["type"].set("pwm")
                else:
                    vars_["type"].set("digital")
            else:
                # Analog pin
                vars_["type"].set("analog" if mode=="input" else "digital")

    def set_all_read_mode(self):
        """Tüm pinleri INPUT yap."""
        self._apply_to_all_pins(mode="input", pwm_as_digital=True, active=True)
        self._persist_config()

    def set_all_write_mode(self):
        """Tüm dijital/PWM pinlerini OUTPUT yap."""
        self._apply_to_all_pins(mode="output", pwm_as_digital=False, active=True)
        self._persist_config() 