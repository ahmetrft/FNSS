"""
Hardware in the Loop (HIL) Test Uygulaması
Bu script, Proteus simülasyonu ve gerçek Arduino arasında veri alışverişini sağlayan,
kullanıcıya görsel ve etkileşimli bir arayüz sunan ana dosyadır.
"""

import customtkinter as ctk
import threading
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from core.serial_manager import SerialManager, serial_manager
import serial
import serial.tools.list_ports
import queue
import threading
import time
from core.config import get_config_path
from utils.logger import bring_to_front_and_center
from PIL import Image, ImageTk

ASSET_PATH = os.path.join(os.path.dirname(__file__), "../assets")
def get_asset(filename):
    return os.path.join(ASSET_PATH, filename)

@dataclass
class VehicleState:
    """Araç durumu veri sınıfı"""
    motor_status: bool = False
    climate_status: bool = False
    emergency_status: bool = False
    speed: float = 0.0
    fuel_level: float = 100.0
    speed_limit: float = 80.0
    fuel_critical_level: float = 20.0
    timestamp: str = ""
    motor_blocked: bool = False  # Motor_OFF flag
    ac_blocked: bool = False     # AC_OFF flag
    motor_on_btn: int = 0
    motor_off_btn: int = 0
    ac_on_btn: int = 0
    ac_off_btn: int = 0

class HILSerialConnection:
    """HIL için basit serial bağlantı sınıfı"""
    
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.message_callbacks: List[callable] = []
        
    def connect(self) -> bool:
        """Serial bağlantısını aç"""
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(1)  # Bağlantı stabilizasyonu
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Bağlantı hatası {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Serial bağlantısını kapat"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.is_connected = False
    
    def send_message(self, message: str) -> bool:
        """Mesaj gönder"""
        if not self.is_connected:
            return False
        
        try:
            if not message.endswith('\n'):
                message += '\n'
            self.serial_port.write(message.encode('utf-8'))
            self.serial_port.flush()
            return True
        except Exception as e:
            print(f"Mesaj gönderme hatası: {e}")
            return False
    
    def read_message(self) -> Optional[str]:
        """Mesaj oku"""
        if not self.is_connected:
            return None
        
        try:
            if self.serial_port.in_waiting:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    return line
        except Exception as e:
            print(f"Mesaj okuma hatası: {e}")
        return None
    
    def add_message_callback(self, callback: callable):
        """Mesaj callback'i ekle"""
        if callback not in self.message_callbacks:
            self.message_callbacks.append(callback)
    
    def poll_messages(self):
        """Mesajları oku ve callback'leri çağır"""
        message = self.read_message()
        if message:
            for callback in self.message_callbacks:
                try:
                    callback("Alınan", message)
                except Exception as e:
                    print(f"Callback hatası: {e}")

class HILSerialManager:
    """HIL için özel serial yöneticisi - iki Arduino ile haberleşme"""
    
    def __init__(self):
        self.sim_serial: Optional[HILSerialConnection] = None  # Proteus Arduino
        self.real_serial: Optional[SerialManager] = None  # Gerçek Arduino
        self.sim_port = "COM6"  # Varsayılan Proteus portu
        self.real_port: Optional[str] = None  # Otomatik bulunacak
        
        # Veri kaydetme
        self.log_file = None
        self.log_enabled = True
        
        # Callbacks
        self.state_callbacks: List[callable] = []
        self.message_callbacks: List[callable] = []
        
        # Araç durumu
        self.vehicle_state = VehicleState()
        
        # Mevcut serial manager'ı kullan (gerçek Arduino için)
        self.real_serial = serial_manager
        
        self.motor_on_btn = 0
        self.motor_off_btn = 0
        self.ac_on_btn = 0
        self.ac_off_btn = 0
        self.emergency_latched = False
        
        self.last_outputs = {
            'motor': None,
            'climate': None,
            'emergency': None,
            'speed': None,
            'fuel': None
        }
        
    def connect_sim_arduino(self, port: str = None) -> bool:
        """Proteus Arduino'ya bağlan"""
        if port:
            self.sim_port = port
            
        try:
            # Sim Arduino için HILSerialConnection oluştur
            self.sim_serial = HILSerialConnection(self.sim_port, 9600)
            
            # Bağlantı kur
            if self.sim_serial.connect():
                # Callback'leri ekle
                self.sim_serial.add_message_callback(self._on_sim_message)
                return True
            return False
        except Exception as e:
            print(f"Sim Arduino bağlantı hatası: {e}")
            return False
    
    def connect_real_arduino(self) -> bool:
        """Gerçek Arduino'yu otomatik bul ve bağlan"""
        try:
            # Mevcut SerialManager'ı kullan (zaten başlatılmış)
            # Arduino portunu bul
            self.real_port = self.real_serial.find_arduino_port(timeout=3.0)
            if self.real_port:
                # Callback'leri ekle
                self.real_serial.add_message_callback(self._on_real_message)
                return True
            return False
        except Exception as e:
            print(f"Real Arduino bağlantı hatası: {e}")
            return False
    
    def _on_sim_message(self, source: str, message: str):
        """Proteus'tan gelen mesajları işle"""
        try:
            # Mesajı parse et
            if message.startswith("BUTTON"):
                self._handle_button_message(message)
            elif message.startswith("POT"):
                self._handle_potentiometer_message(message)
            
            # Log'a kaydet
            if self.log_enabled:
                self._log_message("SIM", message)
                
            # Callback'leri çağır
            for callback in self.message_callbacks:
                callback("SIM", message)
                
        except Exception as e:
            print(f"Sim mesaj işleme hatası: {e}")
    
    def _on_real_message(self, source: str, message: str):
        """Gerçek Arduino'dan gelen mesajları işle"""
        try:
            # Log'a kaydet
            if self.log_enabled:
                self._log_message("REAL", message)
                
            # Callback'leri çağır
            for callback in self.message_callbacks:
                callback("REAL", message)
                
        except Exception as e:
            print(f"Real mesaj işleme hatası: {e}")
    
    def _handle_button_message(self, message: str):
        """Buton mesajlarını işle (PLC mantığı: 1=basılı, 0=bırakılmış)"""
        try:
            parts = message.split(":")
            if len(parts) >= 3:
                button_num = int(parts[1])
                state = int(parts[2].strip()) == 1  # PLC mantığı: 1=basılı, 0=bırakılmış
                
                self.vehicle_state.timestamp = datetime.now().strftime("%H:%M:%S")
                
                if button_num == 1:  # Motor Start
                    self.motor_on_btn = int(state)
                elif button_num == 2:  # Motor Stop
                    self.motor_off_btn = int(state)
                elif button_num == 3:  # AC Start
                    self.ac_on_btn = int(state)
                elif button_num == 4:  # AC Stop
                    self.ac_off_btn = int(state)
                elif button_num == 5:  # Emergency
                    if state and not self.emergency_latched:  # Buton basılı ve latch yok
                        self.vehicle_state.emergency_status = True
                        self.emergency_latched = True
                        self._log_event("Emergency (buton basılı - latch)")
                    elif not state:  # Buton bırakıldı
                        self._log_event("Emergency (buton bırakıldı)")
                
                # Motor ve AC durumunu anlık butonlara göre belirle
                self.vehicle_state.motor_status = (self.motor_on_btn == 1 and self.motor_off_btn == 0)
                self.vehicle_state.climate_status = (self.ac_on_btn == 1 and self.ac_off_btn == 0)
                
                # Gerçek Arduino'ya komut gönder
                self._send_commands_to_real_arduino()
                
                # State callback'lerini çağır
                for callback in self.state_callbacks:
                    callback(self.vehicle_state)
                    
        except Exception as e:
            print(f"Buton mesaj işleme hatası: {e}")
    
    def _handle_potentiometer_message(self, message: str):
        """Potansiyometre mesajlarını işle"""
        try:
            parts = message.split(":")
            if len(parts) >= 3:
                pot_num = int(parts[1])
                value = float(parts[2])
                
                self.vehicle_state.timestamp = datetime.now().strftime("%H:%M:%S")
                
                if pot_num == 1:  # Hız
                    self.vehicle_state.speed = value
                elif pot_num == 2:  # Yakıt
                    self.vehicle_state.fuel_level = value
                
                # Gerçek Arduino'ya komut gönder
                self._send_commands_to_real_arduino()
                
                # State callback'lerini çağır
                for callback in self.state_callbacks:
                    callback(self.vehicle_state)
                    
        except Exception as e:
            print(f"Potansiyometre mesaj işleme hatası: {e}")
    
    def _send_commands_to_real_arduino(self):
        """Gerçek Arduino'ya sadece değişiklik olduğunda komut gönder"""
        if not self.real_serial or not self.real_serial.is_connected:
            return
        try:
            # Motor durumu - Yeşil LED (Pin 2)
            motor_val = 1 if self.vehicle_state.motor_status else 0
            if self.last_outputs['motor'] != motor_val:
                self.real_serial.send_command(2, motor_val)
                self.last_outputs['motor'] = motor_val
            # Klima durumu - Mavi LED (Pin 3)
            climate_val = 1 if self.vehicle_state.climate_status else 0
            if self.last_outputs['climate'] != climate_val:
                self.real_serial.send_command(3, climate_val)
                self.last_outputs['climate'] = climate_val
            # Acil durum - Kırmızı LED (Pin 4)
            emergency_val = 1 if self.vehicle_state.emergency_status else 0
            if self.last_outputs['emergency'] != emergency_val:
                self.real_serial.send_command(4, emergency_val)
                self.last_outputs['emergency'] = emergency_val
            # Hız uyarısı - Hız LED (Pin 5)
            speed_val = 1 if self.vehicle_state.speed > self.vehicle_state.speed_limit else 0
            if self.last_outputs['speed'] != speed_val:
                self.real_serial.send_command(5, speed_val)
                self.last_outputs['speed'] = speed_val
            # Yakıt uyarısı - Yakıt LED (Pin 6)
            fuel_val = 1 if self.vehicle_state.fuel_level < self.vehicle_state.fuel_critical_level else 0
            if self.last_outputs['fuel'] != fuel_val:
                self.real_serial.send_command(6, fuel_val)
                self.last_outputs['fuel'] = fuel_val
        except Exception as e:
            print(f"Real Arduino komut gönderme hatası: {e}")
    
    def _log_message(self, source: str, message: str):
        """Mesajı log dosyasına kaydet"""
        if not self.log_file:
            self._create_log_file()
        
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {source}: {message}\n"
            self.log_file.write(log_entry)
            self.log_file.flush()
        except Exception as e:
            print(f"Log yazma hatası: {e}")
    
    def _log_event(self, event: str):
        """Olayı log dosyasına kaydet"""
        if not self.log_file:
            self._create_log_file()
        
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] OLAY: {event}\n"
            self.log_file.write(log_entry)
            self.log_file.flush()
        except Exception as e:
            print(f"Event log yazma hatası: {e}")
    
    def _create_log_file(self):
        """Log dosyası oluştur"""
        try:
            log_dir = os.path.join(os.path.dirname(__file__), "../../logs")
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(log_dir, f"hil_test_{timestamp}.log")
            self.log_file = open(log_path, 'w', encoding='utf-8')
            
            # Başlık yaz
            self.log_file.write(f"HIL Test Log - {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            self.log_file.write("=" * 50 + "\n\n")
            
        except Exception as e:
            print(f"Log dosyası oluşturma hatası: {e}")
    
    def set_speed_limit(self, limit: float):
        """Hız limitini ayarla"""
        self.vehicle_state.speed_limit = limit
    
    def set_fuel_critical_level(self, level: float):
        """Kritik yakıt seviyesini ayarla"""
        self.vehicle_state.fuel_critical_level = level
    
    def add_state_callback(self, callback: callable):
        """Durum değişikliği callback'i ekle"""
        if callback not in self.state_callbacks:
            self.state_callbacks.append(callback)
    
    def add_message_callback(self, callback: callable):
        """Mesaj callback'i ekle"""
        if callback not in self.message_callbacks:
            self.message_callbacks.append(callback)
    
    def get_vehicle_state(self) -> VehicleState:
        """Mevcut araç durumunu döndür"""
        return self.vehicle_state
    
    def disconnect_all(self):
        """Tüm bağlantıları kapat"""
        if self.sim_serial:
            self.sim_serial.disconnect()
        if self.real_serial:
            self.real_serial.disconnect()
        if self.log_file:
            self.log_file.close()

class HILMainWindow(ctk.CTk):
    """HIL Ana Pencere"""
    
    def __init__(self):
        super().__init__()
        self.title("FNSS HIL Test Uygulaması")
        self.geometry("750x820")
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        bring_to_front_and_center(self)
        
        # HIL Serial Manager
        self.hil_manager = HILSerialManager()
        
        # GUI bileşenleri
        self.connection_frame = None
        self.control_frame = None
        self.visualization_frame = None
        self.monitor_frame = None
        
        # Durum göstergeleri
        self.status_labels = {}
        self.value_labels = {}
        
        # Mesaj listesi
        self.message_list = []
        
        self._build_interface()
        self._start_connections()
    
    def _build_interface(self):
        # Ana frame'i dikey olarak organize et
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=0)
        main_frame.grid_rowconfigure(2, weight=1)
        # Bağlantı durumu frame (en üstte)
        self._build_connection_frame(main_frame)
        self.connection_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        # Araç durumu (ortada)
        self._build_visualization_frame(main_frame)
        self.visualization_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        # Alt frame: ayarlar ve mesaj monitörü yan yana
        bottom_frame = ctk.CTkFrame(main_frame)
        bottom_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=3)
        bottom_frame.grid_rowconfigure(0, weight=1)
        # Ayarlar (sol)
        self._build_control_frame(bottom_frame)
        self.control_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        # Mesaj monitörü (sağ)
        self._build_monitor_frame(bottom_frame)
        self.monitor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
    
    def _build_connection_frame(self, parent):
        self.connection_frame = ctk.CTkFrame(parent)
        self.connection_frame.grid_propagate(False)
        # Bağlantı butonları (artık solda)
        button_frame = ctk.CTkFrame(self.connection_frame)
        button_frame.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        self.connect_sim_btn = ctk.CTkButton(button_frame, text="Proteus Bağlan", command=self._connect_sim)
        self.connect_sim_btn.pack(side="top", padx=5, pady=5, fill="x", expand=True)
        self.connect_real_btn = ctk.CTkButton(button_frame, text="Gerçek Arduino Bağlan", command=self._connect_real)
        self.connect_real_btn.pack(side="top", padx=5, pady=5, fill="x", expand=True)
        # Proteus bağlantı durumu (artık sağda)
        sim_frame = ctk.CTkFrame(self.connection_frame)
        sim_frame.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        ctk.CTkLabel(sim_frame, text="Proteus Arduino:", font=("Arial", 12)).pack()
        self.status_labels['sim'] = ctk.CTkLabel(sim_frame, text="❌ Bağlantı yok", text_color="red")
        self.status_labels['sim'].pack()
        # Gerçek Arduino bağlantı durumu (artık sağda)
        real_frame = ctk.CTkFrame(self.connection_frame)
        real_frame.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        ctk.CTkLabel(real_frame, text="Gerçek Arduino:", font=("Arial", 12)).pack()
        self.status_labels['real'] = ctk.CTkLabel(real_frame, text="❌ Bağlantı yok", text_color="red")
        self.status_labels['real'].pack()

    def _build_control_frame(self, parent):
        """Kontrol frame'ini oluştur"""
        self.control_frame = ctk.CTkFrame(parent)
        self.control_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(self.control_frame, text="Ayarlar", font=("Arial", 14, "bold"))
        title.pack(pady=5)
        
        # Hız limiti ayarı
        speed_frame = ctk.CTkFrame(self.control_frame)
        speed_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(speed_frame, text="Hız Limiti (km/h):", font=("Arial", 12)).pack()
        self.speed_limit_slider = ctk.CTkSlider(speed_frame, from_=30, to=150, number_of_steps=120)
        self.speed_limit_slider.set(80)
        self.speed_limit_slider.pack(fill="x", padx=10, pady=5)
        self.speed_limit_slider.configure(command=self._on_speed_limit_change)
        
        self.value_labels['speed_limit'] = ctk.CTkLabel(speed_frame, text="80 km/h")
        self.value_labels['speed_limit'].pack()
        
        # Yakıt kritik seviye ayarı
        fuel_frame = ctk.CTkFrame(self.control_frame)
        fuel_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(fuel_frame, text="Kritik Yakıt Seviyesi (%):", font=("Arial", 12)).pack()
        self.fuel_critical_slider = ctk.CTkSlider(fuel_frame, from_=5, to=50, number_of_steps=45)
        self.fuel_critical_slider.set(20)
        self.fuel_critical_slider.pack(fill="x", padx=10, pady=5)
        self.fuel_critical_slider.configure(command=self._on_fuel_critical_change)
        
        self.value_labels['fuel_critical'] = ctk.CTkLabel(fuel_frame, text="20%")
        self.value_labels['fuel_critical'].pack()
    
    def _build_visualization_frame(self, parent):
        self.visualization_frame = ctk.CTkFrame(parent, width=600, height=420)
        self.visualization_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.visualization_frame.grid_propagate(False)
        self.visualization_frame.grid_columnconfigure(0, weight=1, minsize=220)
        self.visualization_frame.grid_columnconfigure(1, weight=2, minsize=360)
        self.visualization_frame.grid_rowconfigure(0, weight=0)
        self.visualization_frame.grid_rowconfigure(1, weight=1)
        self.visualization_frame.grid_rowconfigure(2, weight=1)
        self.visualization_frame.grid_rowconfigure(3, weight=1)
        title = ctk.CTkLabel(self.visualization_frame, text="Araç Durumu", font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=5)
        # Sol sütun: Motor, Fan, Emergency (ikon+led grid, sadece frame yüksekliği artırıldı, led konumu eski)
        for i, (name, on_img, off_img, led_color) in enumerate([
            ("motor", "motor_on.png", "motor_off.png", "green"),
            ("fan", "fan_on.png", "fan_off.png", "blue"),
            ("emergency", "emergency_on.png", "emergency_off.png", "red")]):
            row_frame = ctk.CTkFrame(self.visualization_frame, width=180, height=140)
            row_frame.grid(row=i+1, column=0, sticky="ew", padx=10, pady=10)
            row_frame.pack_propagate(False)
            on_img_obj = ctk.CTkImage(light_image=Image.open(get_asset(on_img)), size=(128, 96))
            off_img_obj = ctk.CTkImage(light_image=Image.open(get_asset(off_img)), size=(128, 96))
            setattr(self, f"{name}_on_img", on_img_obj)
            setattr(self, f"{name}_off_img", off_img_obj)
            icon = ctk.CTkLabel(row_frame, image=off_img_obj, text="")
            icon.pack(side="left", padx=5, pady=5, anchor="center")
            setattr(self, f"{name}_icon", icon)
            led_bg = row_frame.cget('fg_color')
            if isinstance(led_bg, (tuple, list)):
                led_bg = led_bg[0]
            elif isinstance(led_bg, str) and " " in led_bg:
                led_bg = led_bg.split()[0]
            if not isinstance(led_bg, str) or not led_bg.startswith("#"):
                led_bg = "#242424"
            led_canvas = ctk.CTkCanvas(row_frame, width=36, height=36, highlightthickness=0, bg=led_bg)
            led_canvas.pack(side="left", padx=35, pady=5, anchor="center")
            led = led_canvas.create_oval(6, 6, 30, 30, fill="gray", outline="gray")
            setattr(self, f"{name}_led_canvas", led_canvas)
            setattr(self, f"{name}_led", led)
        # Sağ sütun: Hız ve Yakıt göstergeleri (tek bir canvas üzerinde gauge+needle+led, alt hizalı)
        gauge_frame = ctk.CTkFrame(self.visualization_frame, width=340, height=280)
        gauge_frame.grid(row=1, column=1, rowspan=3, sticky="nsew", padx=10, pady=10)
        gauge_frame.grid_propagate(False)
        gauge_frame.grid_rowconfigure(0, weight=1)
        gauge_frame.grid_rowconfigure(1, weight=1)
        gauge_frame.grid_columnconfigure(0, weight=1)
        # Hız göstergesi (tek canvas, alt hizalı)
        self.speed_canvas = ctk.CTkCanvas(gauge_frame, width=300, height=192, bg="#222222", highlightthickness=0)
        self.speed_canvas.grid(row=0, column=0, padx=10, pady=10, sticky="sw")
        self.speed_gauge_img_pil = Image.open(get_asset("speed_gauge.png")).convert("RGBA").resize((256, 192))
        self.speed_needle_img_pil = Image.open(get_asset("speed_needle.png")).convert("RGBA").resize((256, 192))
        self.speed_gauge_img_tk = ImageTk.PhotoImage(self.speed_gauge_img_pil)
        self.speed_gauge_canvas_img = self.speed_canvas.create_image(22, -10, anchor="nw", image=self.speed_gauge_img_tk)
        self.speed_needle_img_tk = None  # İlk başta needle yok
        self.speed_needle_canvas_img = None
        led_bg = gauge_frame.cget('fg_color')
        if isinstance(led_bg, (tuple, list)):
            led_bg = led_bg[0]
        elif isinstance(led_bg, str) and " " in led_bg:
            led_bg = led_bg.split()[0]
        if not isinstance(led_bg, str) or not led_bg.startswith("#"):
            led_bg = "#242424"
        self.speed_led_canvas = ctk.CTkCanvas(gauge_frame, width=36, height=36, highlightthickness=0, bg=led_bg)
        self.speed_led_canvas.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.speed_led = self.speed_led_canvas.create_oval(6, 6, 30, 30, fill="gray", outline="gray")
        # Yakıt göstergesi (tek canvas, alt hizalı)
        self.fuel_canvas = ctk.CTkCanvas(gauge_frame, width=300, height=192, bg="#222222", highlightthickness=0)
        self.fuel_canvas.grid(row=1, column=0, padx=10, pady=10, sticky="sw")
        self.fuel_gauge_img_pil = Image.open(get_asset("fuel_gauge.png")).convert("RGBA").resize((256, 192))
        self.fuel_needle_img_pil = Image.open(get_asset("fuel_needle.png")).convert("RGBA").resize((256, 192))
        self.fuel_gauge_img_tk = ImageTk.PhotoImage(self.fuel_gauge_img_pil)
        self.fuel_gauge_canvas_img = self.fuel_canvas.create_image(22, -10, anchor="nw", image=self.fuel_gauge_img_tk)
        self.fuel_needle_img_tk = None
        self.fuel_needle_canvas_img = None
        led_bg = gauge_frame.cget('fg_color')
        if isinstance(led_bg, (tuple, list)):
            led_bg = led_bg[0]
        elif isinstance(led_bg, str) and " " in led_bg:
            led_bg = led_bg.split()[0]
        if not isinstance(led_bg, str) or not led_bg.startswith("#"):
            led_bg = "#242424"
        self.fuel_led_canvas = ctk.CTkCanvas(gauge_frame, width=36, height=36, highlightthickness=0, bg=led_bg)
        self.fuel_led_canvas.grid(row=1, column=1, padx=10, pady=10, sticky="e")
        self.fuel_led = self.fuel_led_canvas.create_oval(6, 6, 30, 30, fill="gray", outline="gray")

    def _build_monitor_frame(self, parent):
        """Monitör frame'ini oluştur"""
        self.monitor_frame = ctk.CTkFrame(parent)
        self.monitor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(self.monitor_frame, text="Mesaj Monitörü", font=("Arial", 14, "bold"))
        title.pack(pady=5)
        
        # Mesaj listesi
        self.message_text = ctk.CTkTextbox(self.monitor_frame, height=150)
        self.message_text.pack(fill="x", padx=10, pady=5)
        
        # Temizle butonu
        clear_btn = ctk.CTkButton(self.monitor_frame, text="Mesajları Temizle", command=self._clear_messages)
        clear_btn.pack(pady=5)
    
    def _start_connections(self):
        """Bağlantıları başlat"""
        # Callback'leri ekle
        self.hil_manager.add_state_callback(self._on_vehicle_state_change)
        self.hil_manager.add_message_callback(self._on_message_received)
        
        # Otomatik bağlantıları başlat
        threading.Thread(target=self._auto_connect, daemon=True).start()
        
        # Mesaj polling'i başlat
        self._start_message_polling()
    
    def _auto_connect(self):
        """Otomatik bağlantıları başlat"""
        # Proteus Arduino'ya bağlan
        if self.hil_manager.connect_sim_arduino():
            self._update_sim_status(True)
        
        # Gerçek Arduino'yu bul ve bağlan
        if self.hil_manager.connect_real_arduino():
            self._update_real_status(True)
    
    def _start_message_polling(self):
        """Mesaj polling'i başlat"""
        def poll_messages():
            while True:
                try:
                    # Sim Arduino'dan mesajları oku
                    if self.hil_manager.sim_serial:
                        self.hil_manager.sim_serial.poll_messages()
                    
                    # Real Arduino'dan mesajları oku (mevcut sistem kullanılıyor)
                    if self.hil_manager.real_serial:
                        self.hil_manager.real_serial.poll_messages()
                    
                    time.sleep(0.01)  # 10ms bekleme
                except Exception as e:
                    print(f"Mesaj polling hatası: {e}")
                    time.sleep(0.1)
        
        # Polling thread'ini başlat
        threading.Thread(target=poll_messages, daemon=True).start()
    
    def _connect_sim(self):
        """Proteus Arduino'ya manuel bağlan"""
        if self.hil_manager.connect_sim_arduino():
            self._update_sim_status(True)
        else:
            self._update_sim_status(False)
    
    def _connect_real(self):
        """Gerçek Arduino'ya manuel bağlan"""
        if self.hil_manager.connect_real_arduino():
            self._update_real_status(True)
        else:
            self._update_real_status(False)
    
    def _update_sim_status(self, connected: bool):
        if connected:
            self.status_labels['sim'].configure(text="✅ Bağlı", text_color="green")
        else:
            self.status_labels['sim'].configure(text="❌ Bağlantı yok", text_color="red")

    def _update_real_status(self, connected: bool):
        if connected:
            self.status_labels['real'].configure(text="✅ Bağlı", text_color="green")
        else:
            self.status_labels['real'].configure(text="❌ Bağlantı yok", text_color="red")
    
    def _on_vehicle_state_change(self, state: VehicleState):
        """Araç durumu değiştiğinde çağrılır"""
        # GUI güncellemelerini ana thread'de yap
        self.after(0, lambda: self._update_vehicle_display(state))
    
    def _update_vehicle_display(self, state: VehicleState):
        # Motor ikonu ve LED
        if state.motor_status:
            self.motor_icon.configure(image=self.motor_on_img)
            self.motor_led_canvas.itemconfig(self.motor_led, fill="green", outline="green")
        else:
            self.motor_icon.configure(image=self.motor_off_img)
            self.motor_led_canvas.itemconfig(self.motor_led, fill="gray", outline="gray")
        # Fan ikonu ve LED
        if state.climate_status:
            self.fan_icon.configure(image=self.fan_on_img)
            self.fan_led_canvas.itemconfig(self.fan_led, fill="blue", outline="blue")
        else:
            self.fan_icon.configure(image=self.fan_off_img)
            self.fan_led_canvas.itemconfig(self.fan_led, fill="gray", outline="gray")
        # Acil durum ikonu ve LED
        if state.emergency_status:
            self.emergency_icon.configure(image=self.emergency_on_img)
            self.emergency_led_canvas.itemconfig(self.emergency_led, fill="red", outline="red")
        else:
            self.emergency_icon.configure(image=self.emergency_off_img)
            self.emergency_led_canvas.itemconfig(self.emergency_led, fill="gray", outline="gray")
        # Hız göstergesi needle pozisyonu ve led
        speed_angle = -140 + min(max((state.speed / 150.0) * 180, 0), 180)  # 0-150 km/h için 0-180 derece
        # Needle'ı döndür ve Canvas'ta güncelle (merkez 64,48)
        rotated_speed_needle = self.speed_needle_img_pil.rotate(-speed_angle, resample=Image.BICUBIC, center=(128, 96), fillcolor=(0,0,0,0))
        self.speed_needle_img_tk = ImageTk.PhotoImage(rotated_speed_needle)
        if self.speed_needle_canvas_img is not None:
            self.speed_canvas.delete(self.speed_needle_canvas_img)
        self.speed_needle_canvas_img = self.speed_canvas.create_image(24, 40, anchor="nw", image=self.speed_needle_img_tk)
        if state.speed > state.speed_limit:
            self.speed_led_canvas.itemconfig(self.speed_led, fill="orange", outline="orange")
        else:
            self.speed_led_canvas.itemconfig(self.speed_led, fill="gray", outline="gray")
        # Yakıt göstergesi needle pozisyonu ve led
        fuel_angle = -145 + min(max((state.fuel_level / 100.0) * 180, 0), 180)  # 0-100% için 0-180 derece
        rotated_fuel_needle = self.fuel_needle_img_pil.rotate(-fuel_angle, resample=Image.BICUBIC, center=(128, 96), fillcolor=(0,0,0,0))
        self.fuel_needle_img_tk = ImageTk.PhotoImage(rotated_fuel_needle)
        if self.fuel_needle_canvas_img is not None:
            self.fuel_canvas.delete(self.fuel_needle_canvas_img)
        self.fuel_needle_canvas_img = self.fuel_canvas.create_image(24, 45, anchor="nw", image=self.fuel_needle_img_tk)
        if state.fuel_level < state.fuel_critical_level:
            self.fuel_led_canvas.itemconfig(self.fuel_led, fill="orange", outline="orange")
        else:
            self.fuel_led_canvas.itemconfig(self.fuel_led, fill="gray", outline="gray")
    
    def _on_message_received(self, source: str, message: str):
        """Mesaj alındığında çağrılır"""
        # Mesajı listeye ekle
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {source}: {message}"
        
        # GUI güncellemesini ana thread'de yap
        self.after(0, lambda: self._add_message_to_display(formatted_message))
    
    def _add_message_to_display(self, message: str):
        """Mesajı ekrana ekle"""
        self.message_text.insert("end", message + "\n")
        self.message_text.see("end")
        
        # Maksimum 1000 satır tut
        lines = self.message_text.get("1.0", "end").split('\n')
        if len(lines) > 1000:
            self.message_text.delete("1.0", f"{len(lines)-1000}.0")
    
    def _on_speed_limit_change(self, value):
        """Hız limiti değiştiğinde"""
        limit = int(value)
        self.value_labels['speed_limit'].configure(text=f"{limit} km/h")
        self.hil_manager.set_speed_limit(limit)
    
    def _on_fuel_critical_change(self, value):
        """Kritik yakıt seviyesi değiştiğinde"""
        level = int(value)
        self.value_labels['fuel_critical'].configure(text=f"{level}%")
        self.hil_manager.set_fuel_critical_level(level)
    
    def _clear_messages(self):
        """Mesajları temizle"""
        self.message_text.delete("1.0", "end")
    
    def on_closing(self):
        """Pencere kapanırken"""
        self.hil_manager.disconnect_all()
        self.quit()

if __name__ == "__main__":
    app = HILMainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
