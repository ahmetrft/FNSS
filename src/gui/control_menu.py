"""gui.control_menu
WriteMenu + ReadMenu birleşimi: Aktif pinleri hem gösterebilen hem kontrol edebilen tek pencere.
PinManager ile haberleşir, Scheduler ile periyodik okuma gerçekleştirir.
"""
import customtkinter as ctk
from functools import partial
from typing import Dict
import os

from utils.logger import bring_to_front_and_center, get_asset_path
from core.config import load_config, DIGITAL_PINS, ANALOG_PINS, PWM_DIGITAL_PINS
from core.pin_manager import pin_manager
from core.scheduler import scheduler
from core.serial_manager import serial_manager


class ControlMenu(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Kontrol Modu - Arduino Pin Yönetimi")
        # İkonu ayarla
        try:
            ico_path = get_asset_path("indir.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(default=ico_path)
        except Exception:
            pass
        # Dinamik yükseklik hesapla (sabit üst+alt alan + pin başına 28px)
        est_row_h = 28
        total_pin_rows = len([p for p in DIGITAL_PINS if load_config()["pins"].get(str(p), {}).get("mode", "output") != "pas"]) + \
                         len([a for a in ANALOG_PINS if load_config()["pins"].get(a, {}).get("mode", "input") != "pas"])
        base_height = 360  # başlıklar, butonlar vb.
        self.geometry(f"580x{base_height + est_row_h * total_pin_rows}")
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Konfigürasyon
        self.config_data = load_config()
        self.active_pins_digital = [p for p in DIGITAL_PINS if self.config_data["pins"].get(str(p), {}).get("mode", "output") != "pas"]
        self.active_pins_analog = [a for a in ANALOG_PINS if self.config_data["pins"].get(a, {}).get("mode", "input") != "pas"]

        # --- Okuma tipine göre gruplar ---
        #   • self.digital_read_pins : Dijital okuma yapılacak pin numaraları (int)
        #   • self.analog_read_pins  : Analog okuma yapılacak analog pin isimleri ("A0" ... "A5")
        self.digital_read_pins: list[int] = []
        self.analog_read_pins: list[str] = []
        # Dijital pinler (2-13)
        for p in self.active_pins_digital:
            p_conf = self.config_data["pins"].get(str(p), {})
            if p_conf.get("mode", "output") == "input":
                # Dijital pinler sadece dijital okunabilir
                self.digital_read_pins.append(p)
        # Analog pinler (A0-A5)
        for a_name in self.active_pins_analog:
            a_conf = self.config_data["pins"].get(a_name, {})
            if a_conf.get("mode", "input") != "input":
                continue
            if a_conf.get("type", "analog") == "analog":
                # Analog tipinde okuma → analog değere gidecek
                self.analog_read_pins.append(a_name)
            else:
                # 'digital' tipinde okuma → dijital gruba
                pin_num = 14 + ANALOG_PINS.index(a_name)
                self.digital_read_pins.append(pin_num)

        # Dahili widget tabloları
        self.toggle_widgets: Dict[int, ctk.CTkSwitch] = {}
        self.slider_widgets: Dict[int, ctk.CTkSlider] = {}
        # PWM debounce helpers {pin: after_id}
        self._pwm_after_ids: Dict[int, str] = {}
        self._pending_pwm_vals: Dict[int, int] = {}

        # Gösterge tabloları
        self.digital_indicators: Dict[int, ctk.CTkLabel] = {}
        self.analog_num_labels: Dict[str, ctk.CTkLabel] = {}
        self.analog_indicators: Dict[int, ctk.CTkLabel] = {}

        # Renkler
        self._color_green = "#34C759"
        self._color_red = "#FF3B30"
        self._color_gray = "#8E8E93"
        # Toggle renkleri için standart renkler
        self._toggle_on_color = "#34C759"   # Yeşil (açık)
        self._toggle_off_color = "#FF3B30"  # Kırmızı (kapalı)

        # Debug helper: border around each widget to visualize alignment
        def _dbg(w):
            try:
                import customtkinter as _ctk
                if isinstance(w, _ctk.CTkLabel):
                    w.configure(border_width=3, border_color="#5E5E5E")
            except Exception:
                pass
        self._dbg = _dbg

        # UI kurulum
        self._build_layout()

        # Konfigürasyondaki pin modlarını Arduino'ya uygula (tek merkezden)
        try:
            pin_manager.apply_config(self.config_data)
        except Exception:
            pass

        # --- Serial mesaj kuyruğunu arka planda boşalt ---
        try:
            scheduler.add_job("serial_poll", serial_manager.poll_messages, 0.1)
        except Exception:
            pass


        # Bu sürümde pin modlarını doğrudan Kontrol Menüsü açılırken uyguluyoruz.

        # PinManager dinleyicileri
        pin_manager.add_listener("pin_state", self._on_pin_state)
        pin_manager.add_listener("analog_value", self._on_analog_value)

        # Pencere kapatma protokolü
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Pencere tamamen oluşturulduktan sonra öne getir ve odakla
        bring_to_front_and_center(self)

    # ---------------- UI ----------------
    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        # İki alt çerçeve: Dijital ve Analog
        digital_frame = ctk.CTkFrame(main_frame)
        digital_frame.configure(border_width=2, border_color="#FF9500")
        digital_frame.pack(fill="x", padx=0, pady=(0, 4))

        analog_frame = ctk.CTkFrame(main_frame)
        analog_frame.configure(border_width=2, border_color="#34C759")
        analog_frame.pack(fill="x", padx=0, pady=(0, 4))

        # Başlıkları ortalamak için column configure
        digital_frame.grid_columnconfigure(0, weight=1)
        analog_frame.grid_columnconfigure(0, weight=1)

        # Dijital frame için iç container
        digital_container = ctk.CTkFrame(digital_frame, fg_color="transparent")
        digital_container.pack(fill="both", expand=True, padx=8, pady=2)
        digital_container.grid_columnconfigure(0, weight=0, minsize=90)
        digital_container.grid_columnconfigure(1, weight=0, minsize=150)
        digital_container.grid_columnconfigure(2, weight=1, minsize=0)

        # Dijital başlık
        ctk.CTkLabel(digital_container, text="Dijital Pinler (Yazma / Okuma)", font=("Arial", 15, "bold"))\
            .grid(row=0, column=0, columnspan=3, pady=(2, 2), sticky="ew")
        
        # Dijital kolon başlıkları (I/O birleşik)
        digital_headers = ["Pin", "I/O", "PWM"]
        for i, h1 in enumerate(digital_headers):
            px = 100 if i == 1 else 0
            ctk.CTkLabel(digital_container, text=h1, font=("Arial", 13, "bold"), anchor="center")\
                .grid(row=1, column=i, padx=px, pady=1, sticky="ew")

        # Dijital pin satırları (yalnızca aktif pinler)
        row_ptr = 2
        toggle_width = 100  # Toggle butonlarının genişliğiyle aynı olmalı, sütun minsize ile eşit
        for pin in self.active_pins_digital:
            pin_conf = self.config_data["pins"].get(str(pin), {})
            p_type = pin_conf.get("type", "digital")
            p_mode = pin_conf.get("mode", "output")

            ctk.CTkLabel(digital_container, text=str(pin), anchor="center", font=("Arial", 12)).grid(row=row_ptr, column=0, padx=0, pady=1, sticky="nsew")

            # I/O hücresi
            if p_mode == "output":
                # Toggle (yazma)
                toggle = ctk.CTkSwitch(digital_container, text="", command=partial(self._on_toggle, pin), width=toggle_width)
                toggle.grid(row=row_ptr, column=1, padx=(100, 0), sticky="ew")
                self.toggle_widgets[pin] = toggle
                self._dbg(toggle)
            else:
                # Giriş gösterimi
                lbl = ctk.CTkLabel(digital_container, text="●", text_color=self._color_gray)
                lbl.grid(row=row_ptr, column=1, padx=0)
                self.digital_indicators[pin] = lbl
                self._dbg(lbl)

            # PWM slider (sadece PWM pin ve OUTPUT)
            if p_mode == "output" and p_type == "pwm":
                slider = ctk.CTkSlider(digital_container, from_=0, to=255, number_of_steps=255, width=120,
                                       command=partial(self._on_pwm_change, pin))
                slider.grid(row=row_ptr, column=2)
                self.slider_widgets[pin] = slider
                self._dbg(slider)
            else:
                ctk.CTkLabel(digital_container, text="").grid(row=row_ptr, column=2)

            row_ptr += 1
        # Dijital frame altına boşluk için dummy satır

        # Analog frame için iç container
        analog_container = ctk.CTkFrame(analog_frame, fg_color="transparent")
        analog_container.pack(fill="both", expand=True, padx=8, pady=2)
        analog_container.grid_columnconfigure(0, weight=0, minsize=90)
        analog_container.grid_columnconfigure(1, weight=0, minsize=150)
        analog_container.grid_columnconfigure(2, weight=1, minsize=0)

        # Analog başlık
        ctk.CTkLabel(analog_container, text="Analog Pinler", font=("Arial", 15, "bold"))\
            .grid(row=0, column=0, columnspan=3, pady=(2, 2), sticky="ew")
        a_row_ptr = 1

        # Analog başlıklar: Pin | Çıkış | Değer | Giriş
        analog_headers = ["Pin", "I/O", ""]
        for j, h2 in enumerate(analog_headers):
            px = 100 if j == 1 else 0
            ctk.CTkLabel(analog_container, text=h2, font=("Arial", 13, "bold"), anchor="center")\
                .grid(row=a_row_ptr, column=j, padx=px, pady=1, sticky="ew")
        a_row_ptr += 1

        for name in self.active_pins_analog:
            pin_num = 14 + ANALOG_PINS.index(name)
            pin_conf = self.config_data["pins"].get(name, {})
            p_mode = pin_conf.get("mode", "input")
            p_type = pin_conf.get("type", "analog")

            ctk.CTkLabel(analog_container, text=name, anchor="center", font=("Arial", 12)).grid(row=a_row_ptr, column=0, padx=0, pady=1, sticky="nsew")

            # I/O hücresi
            if p_mode == "output":
                a_toggle = ctk.CTkSwitch(analog_container, text="", command=partial(self._on_toggle, pin_num), width=toggle_width)
                a_toggle.grid(row=a_row_ptr, column=1, padx=(100, 0), sticky="ew")
                self.toggle_widgets[pin_num] = a_toggle
                self._dbg(a_toggle)
            elif p_mode == "input" and p_type == "analog":
                lbl = ctk.CTkLabel(analog_container, text="0")
                lbl.grid(row=a_row_ptr, column=1, padx=0)
                self.analog_num_labels[name] = lbl
                self._dbg(lbl)
            else:
                # Dijital giriş olarak kullanılıyorsa
                lbl = ctk.CTkLabel(analog_container, text="●", text_color=self._color_gray)
                lbl.grid(row=a_row_ptr, column=1, padx=0)
                self.analog_indicators[pin_num] = lbl
                self._dbg(lbl)

            # Boş hücre (PWM sütunu hizası için)
            ctk.CTkLabel(analog_container, text="").grid(row=a_row_ptr, column=2)

            a_row_ptr += 1
        # Analog frame altına boşluk için dummy satır

        # --- Kontrol Butonları (Okuma & Pattern) ---
        ctrl_frame = ctk.CTkFrame(main_frame)
        ctrl_frame.configure(border_width=2, border_color="#007AFF")
        ctrl_frame.pack(fill="x", padx=0, pady=(0, 2))
        ctrl_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Sol taraf: Okuma kontrolleri
        read_frame = ctk.CTkFrame(ctrl_frame)
        read_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        # Başlık
        ctk.CTkLabel(read_frame, text="Okuma", font=("Arial", 13, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 6))

        # Dijital okuma ayarları
        ctk.CTkLabel(read_frame, text="Dijital (ms):").grid(row=1, column=0, padx=5)
        self.d_interval_entry = ctk.CTkEntry(read_frame, width=80)
        self.d_interval_entry.insert(0, "300")
        self.d_interval_entry.grid(row=1, column=1, padx=5)
        self.d_switch = ctk.CTkSwitch(read_frame, command=self._toggle_digital_poll, text="")
        self.d_switch.grid(row=1, column=2, padx=10)

        # Analog okuma ayarları
        ctk.CTkLabel(read_frame, text="Analog (ms):").grid(row=2, column=0, padx=5)
        self.a_interval_entry = ctk.CTkEntry(read_frame, width=80)
        self.a_interval_entry.insert(0, "500")
        self.a_interval_entry.grid(row=2, column=1, padx=5)
        self.a_switch = ctk.CTkSwitch(read_frame, command=self._toggle_analog_poll, text="")
        self.a_switch.grid(row=2, column=2, padx=10)

        # Okuma tipine göre toggle'ları aktif/pasif yap
        if not self.digital_read_pins:
            self.d_switch.configure(state="disabled")
        if not self.analog_read_pins:
            self.a_switch.configure(state="disabled")

        # Sağ taraf: Yazma pattern kontrolleri
        pattern_frame = ctk.CTkFrame(ctrl_frame)
        pattern_frame.grid(row=0, column=3, columnspan=3, padx=10, pady=10, sticky="e")

        ctk.CTkLabel(pattern_frame, text="Okuma", font=("Arial", 13, "bold")).grid(row=0, column=0, columnspan=4, pady=(0, 6))

        # Pattern yönetimi
        self.pattern_stop_events = {}
        # Hem dijital hem analog çıkış pinlerini dahil et
        pins = self.active_pins_digital.copy()
        # Analog pinleri de ekle (14-19 arası pin numaraları)
        for name in self.active_pins_analog:
            pin_conf = self.config_data["pins"].get(name, {})
            if pin_conf.get("mode", "input") == "output":
                pin_num = 14 + ANALOG_PINS.index(name)
                pins.append(pin_num)

        import threading, time

        def _start_pattern(name: str, worker, switch):
            # diğer patternleri kapat
            for n, sw in pattern_switches.items():
                if n != name and sw.get():
                    sw.deselect()
                    _stop_pattern(n)
            _stop_pattern(name)  # güvenlik: varsa durdur
            stop_event = threading.Event()
            self.pattern_stop_events[name] = stop_event
            threading.Thread(target=worker, args=(stop_event,), daemon=True).start()

        def _stop_pattern(name: str):
            ev = self.pattern_stop_events.get(name)
            if ev:
                ev.set()

        # helpers
        def get_ms(entry: ctk.CTkEntry, default: int):
            try:
                v = int(entry.get())
                return max(10, v)
            except ValueError:
                return default

        pattern_switches = {}

        # Row definitions
        # Sıralı
        ctk.CTkLabel(pattern_frame, text="Sıralı (ms)").grid(row=1, column=0, padx=4)
        seq_entry = ctk.CTkEntry(pattern_frame, width=60)
        seq_entry.insert(0, "100")
        seq_entry.grid(row=1, column=1, padx=4)
        seq_switch = ctk.CTkSwitch(pattern_frame, text="", width=60)
        seq_switch.grid(row=1, column=2, padx=4)
        pattern_switches["seq"] = seq_switch

        def seq_worker(stop_event):
            while not stop_event.is_set():
                step = get_ms(seq_entry, 100) / 1000.0
                for p in pins:
                    if stop_event.is_set():
                        break
                    self._on_toggle_pattern(p, 1)
                    time.sleep(step)
                for p in pins:
                    if stop_event.is_set():
                        break
                    self._on_toggle_pattern(p, 0)
                    time.sleep(step)

        seq_switch.configure(command=lambda: _start_pattern("seq", seq_worker, seq_switch) if seq_switch.get() else _stop_pattern("seq"))

        # Blink
        ctk.CTkLabel(pattern_frame, text="Blink (ms)").grid(row=2, column=0, padx=4)
        blink_entry = ctk.CTkEntry(pattern_frame, width=60)
        blink_entry.insert(0, "200")
        blink_entry.grid(row=2, column=1, padx=4)
        blink_switch = ctk.CTkSwitch(pattern_frame, text="", width=60)
        blink_switch.grid(row=2, column=2, padx=4)
        pattern_switches["blink"] = blink_switch

        def blink_worker(stop_event):
            while not stop_event.is_set():
                delay = get_ms(blink_entry, 200) / 1000.0
                # Her pin için sırayla aç-kapat yap
                for p in pins:
                    if stop_event.is_set():
                        break
                    # Pin'i aç
                    self._on_toggle_pattern(p, 1)
                    time.sleep(delay)
                    if stop_event.is_set():
                        break
                    # Pin'i kapat
                    self._on_toggle_pattern(p, 0)
                    time.sleep(delay)

        blink_switch.configure(command=lambda: _start_pattern("blink", blink_worker, blink_switch) if blink_switch.get() else _stop_pattern("blink"))

        # Döngü Hepsi Yak/Söndür
        ctk.CTkLabel(pattern_frame, text="Hepsi (ms)").grid(row=3, column=0, padx=4)
        all_entry = ctk.CTkEntry(pattern_frame, width=60)
        all_entry.insert(0, "500")
        all_entry.grid(row=3, column=1, padx=4)
        all_switch = ctk.CTkSwitch(pattern_frame, text="", width=60)
        all_switch.grid(row=3, column=2, padx=4)
        pattern_switches["all"] = all_switch

        def all_worker(stop_event):
            while not stop_event.is_set():
                delay = get_ms(all_entry, 500) / 1000.0
                self.after(0, self._all_on)
                time.sleep(delay)
                if stop_event.is_set():
                    break
                self.after(0, self._all_off)
                time.sleep(delay)

        all_switch.configure(command=lambda: _start_pattern("all", all_worker, all_switch) if all_switch.get() else _stop_pattern("all"))

        # Tek seferlik Hepsi Açık / Kapalı butonları
        single_frame = ctk.CTkFrame(pattern_frame)
        single_frame.grid(row=4, column=0, columnspan=3, pady=(8, 0))

        ctk.CTkButton(single_frame, text="Hepsi Açık", width=80, command=self._all_on).grid(row=0, column=0, padx=4)
        ctk.CTkButton(single_frame, text="Hepsi Kapalı", width=80, command=self._all_off).grid(row=0, column=1, padx=4)

        # --- YAZMA MENÜSÜ TAMAMEN DEVRE DIŞI BIRAKMA ---
        # Eğer hiç yazılabilir pin yoksa (toggle ve slider yoksa), pattern ve toplu butonları devre dışı bırak
        if not self.toggle_widgets and not self.slider_widgets:
            # Pattern switch'leri ve entry'leri devre dışı bırak
            for sw in pattern_switches.values():
                sw.configure(state="disabled")
            seq_entry.configure(state="disabled")
            blink_entry.configure(state="disabled")
            all_entry.configure(state="disabled")
            # Hepsi Açık/Kapalı butonlarını devre dışı bırak
            for child in single_frame.winfo_children():
                try:
                    child.configure(state="disabled")
                except Exception:
                    pass

    # ---------------- Pin Mode Config ----------------
    def _apply_pin_modes(self):
        for pin in DIGITAL_PINS:
            conf = self.config_data["pins"].get(str(pin), {})
            m_str = conf.get("mode", "output")
            if m_str == "pas":
                continue
            mode = 1 if m_str == "output" else 0
            pin_manager.set_mode(pin, mode)
        # Analog pinler
        for idx, name in enumerate(ANALOG_PINS):
            conf = self.config_data["pins"].get(name, {})
            m_str = conf.get("mode", "input")
            if m_str == "pas":
                continue
            if m_str == "output":
                pin_manager.set_mode(14 + idx, 1)

    # ---------------- Event Handlers ----------------
    def _on_toggle(self, pin: int):
        val = self.toggle_widgets[pin].get()
        pin_manager.write_digital(pin, 1 if val else 0)

    def _on_toggle_pattern(self, pin: int, state: int):
        """Pattern worker'ları için toggle metodu - görsel güncelleme yapar"""
        # Toggle widget'ını güncelle
        toggle = self.toggle_widgets.get(pin)
        if toggle is not None:
            if state:
                toggle.select()
                toggle.configure(progress_color=self._toggle_on_color)
            else:
                toggle.deselect()
                toggle.configure(progress_color=self._toggle_off_color)
        # Arduino'ya komut gönder
        pin_manager.write_digital(pin, state)

    def _on_pwm_change(self, pin: int, value: float):
        # Debounce: gönderimi 120 ms ertele; arada gelen değerler sonuncu ile üzerine yazılır
        val = int(value)
        self._pending_pwm_vals[pin] = val

        # Toggle görsel durumu anlık göster
        toggle = self.toggle_widgets[pin]
        if val > 0:
            toggle.select()
            toggle.configure(progress_color=self._toggle_on_color)
        else:
            toggle.deselect()
            toggle.configure(progress_color=self._toggle_off_color)

        # Önceki zamanlayıcıyı iptal et
        prev_id = self._pwm_after_ids.get(pin)
        if prev_id:
            try:
                self.after_cancel(prev_id)
            except Exception:
                pass

        # Yeni zamanlayıcı oluştur
        after_id = self.after(120, lambda p=pin: self._flush_pwm(p))
        self._pwm_after_ids[pin] = after_id

    def _flush_pwm(self, pin: int):
        """Gerçek PWM komutunu seri hatta gönderir (debounce sonrası)."""
        val = self._pending_pwm_vals.get(pin)
        if val is None:
            return
        pin_manager.write_pwm(pin, val)
        # Temizle
        self._pwm_after_ids.pop(pin, None)

    def _on_pin_state(self, data):
        pin = data["pin"]
        val = data["value"]
        # Güncelle toggle
        toggle = self.toggle_widgets.get(pin)
        if toggle is not None:
            toggle.configure(progress_color=self._toggle_on_color if val else self._toggle_off_color)
            if val:
                toggle.select()
            else:
                toggle.deselect()
        # Dijital giriş göstergesi
        ind = self.digital_indicators.get(pin)
        if ind is not None:
            ind.configure(text="●", text_color=(self._color_green if val else self._color_red))

        # Analog pini dijital olarak okuma durumu
        a_ind = self.analog_indicators.get(pin)
        if a_ind is not None:
            a_ind.configure(text="●", text_color=(self._color_green if val else self._color_red))

    def _on_analog_value(self, data):
        name = data["pin"]
        val = data["value"]
        lbl = self.analog_num_labels.get(name)
        if lbl is not None:
            lbl.configure(text=str(val))

    # ---------------- Poll toggles ----------------
    def _get_interval(self, entry, default_ms):
        try:
            v = int(entry.get())
            return max(50, v) / 1000.0
        except ValueError:
            return default_ms / 1000.0

    def _toggle_digital_poll(self):
        # Dijital okuma pinimiz yoksa hiçbir şey yapma
        if not self.digital_read_pins:
            return
        if self.d_switch.get():
            interval = self._get_interval(self.d_interval_entry, 300)
            scheduler.add_job("digital_poll", pin_manager.request_digital_read, interval)
            # İlk veriyi bekletmeden iste
            pin_manager.request_digital_read()
        else:
            scheduler.remove_job("digital_poll")

            # --- Göstergeleri varsayılan duruma sıfırla ---
            for lbl in self.digital_indicators.values():
                lbl.configure(text="●", text_color=self._color_gray)
            for lbl in self.analog_indicators.values():
                lbl.configure(text="●", text_color=self._color_gray)

    def _toggle_analog_poll(self):
        # Analog okuma pinimiz yoksa hiçbir şey yapma
        if not self.analog_read_pins:
            return
        if self.a_switch.get():
            interval = self._get_interval(self.a_interval_entry, 500)
            scheduler.add_job("analog_poll", pin_manager.request_analog_read, interval)
            pin_manager.request_analog_read()
        else:
            scheduler.remove_job("analog_poll")

            # --- Analog değerleri ve göstergeleri sıfırla ---
            for lbl in self.analog_num_labels.values():
                lbl.configure(text="0")
            for lbl in self.analog_indicators.values():
                lbl.configure(text="●", text_color=self._color_gray)

    # ---------------- Cleanup ----------------
    def _all_on(self):
        """Tüm çıkış pinlerini aç ve toggle tuşlarını güncelle"""
        # Arduino'ya komut gönder
        serial_manager.send_all_command(1)
        # Toggle tuşlarını anında güncelle
        for pin, toggle in self.toggle_widgets.items():
            toggle.select()
            toggle.configure(progress_color=self._toggle_on_color)

    def _all_off(self):
        """Tüm çıkış pinlerini kapat ve toggle tuşlarını güncelle"""
        # Arduino'ya komut gönder
        serial_manager.send_all_command(0)
        # Toggle tuşlarını anında güncelle
        for pin, toggle in self.toggle_widgets.items():
            toggle.deselect()
            toggle.configure(progress_color=self._toggle_off_color)

    def _on_closing(self):
        scheduler.remove_job("digital_poll")
        scheduler.remove_job("analog_poll")
        # Serial polling'i kaldır
        scheduler.remove_job("serial_poll")
        pin_manager.remove_listener("pin_state", self._on_pin_state)
        pin_manager.remove_listener("analog_value", self._on_analog_value)
        self.destroy() 