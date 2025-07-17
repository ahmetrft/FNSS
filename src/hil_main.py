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
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
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
        self.geometry("600x800")
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
        """Arayüzü oluştur"""
        # Ana frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Grid yapılandırması
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Bağlantı durumu frame
        self._build_connection_frame(main_frame)
        
        # Kontrol frame
        self._build_control_frame(main_frame)
        
        # Görselleştirme frame
        self._build_visualization_frame(main_frame)
        
        # Monitör frame
        self._build_monitor_frame(main_frame)
    
    def _build_connection_frame(self, parent):
        """Bağlantı durumu frame'ini oluştur"""
        self.connection_frame = ctk.CTkFrame(parent)
        self.connection_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        title = ctk.CTkLabel(self.connection_frame, text="Bağlantı Durumu", font=("Arial", 14, "bold"))
        title.pack(pady=5)
        
        # Sim Arduino durumu
        sim_frame = ctk.CTkFrame(self.connection_frame)
        sim_frame.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        ctk.CTkLabel(sim_frame, text="Proteus Arduino:", font=("Arial", 12)).pack()
        self.status_labels['sim'] = ctk.CTkLabel(sim_frame, text="❌ Bağlantı yok", text_color="red")
        self.status_labels['sim'].pack()
        
        # Real Arduino durumu
        real_frame = ctk.CTkFrame(self.connection_frame)
        real_frame.pack(side="right", padx=10, pady=5, fill="x", expand=True)
        
        ctk.CTkLabel(real_frame, text="Gerçek Arduino:", font=("Arial", 12)).pack()
        self.status_labels['real'] = ctk.CTkLabel(real_frame, text="❌ Bağlantı yok", text_color="red")
        self.status_labels['real'].pack()
    
    def _build_control_frame(self, parent):
        """Kontrol frame'ini oluştur"""
        self.control_frame = ctk.CTkFrame(parent)
        self.control_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
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
        
        # Bağlantı butonları
        button_frame = ctk.CTkFrame(self.control_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.connect_sim_btn = ctk.CTkButton(button_frame, text="Proteus Bağlan", command=self._connect_sim)
        self.connect_sim_btn.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        self.connect_real_btn = ctk.CTkButton(button_frame, text="Gerçek Arduino Bağlan", command=self._connect_real)
        self.connect_real_btn.pack(side="right", padx=5, pady=5, fill="x", expand=True)
    
    def _build_visualization_frame(self, parent):
        self.visualization_frame = ctk.CTkFrame(parent, width=260)
        self.visualization_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.visualization_frame.grid_propagate(False)
        title = ctk.CTkLabel(self.visualization_frame, text="Araç Durumu", font=("Arial", 14, "bold"))
        title.pack(pady=5)
        # Motor durumu
        motor_frame = ctk.CTkFrame(self.visualization_frame)
        motor_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(motor_frame, text="Motor:", font=("Arial", 12), width=80, anchor="w").pack(side="left", padx=5)
        self.status_labels['motor'] = ctk.CTkLabel(motor_frame, text="❌ Kapalı", text_color="red", width=120, anchor="w")
        self.status_labels['motor'].pack(side="right", padx=5)
        # Klima durumu
        climate_frame = ctk.CTkFrame(self.visualization_frame)
        climate_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(climate_frame, text="Klima:", font=("Arial", 12), width=80, anchor="w").pack(side="left", padx=5)
        self.status_labels['climate'] = ctk.CTkLabel(climate_frame, text="❌ Kapalı", text_color="red", width=120, anchor="w")
        self.status_labels['climate'].pack(side="right", padx=5)
        # Acil durum
        emergency_frame = ctk.CTkFrame(self.visualization_frame)
        emergency_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(emergency_frame, text="Acil Durum:", font=("Arial", 12), width=80, anchor="w").pack(side="left", padx=5)
        self.status_labels['emergency'] = ctk.CTkLabel(emergency_frame, text="✅ Sorun yok", text_color="green", width=120, anchor="w")
        self.status_labels['emergency'].pack(side="right", padx=5)
        
        # Hız göstergesi
        speed_frame = ctk.CTkFrame(self.visualization_frame)
        speed_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(speed_frame, text="Hız:", font=("Arial", 12), width=80, anchor="w").pack(side="left", padx=5)
        self.value_labels['speed'] = ctk.CTkLabel(speed_frame, text="0 km/h", width=120, anchor="w")
        self.value_labels['speed'].pack(side="right", padx=5)
        
        # Yakıt seviyesi
        fuel_frame = ctk.CTkFrame(self.visualization_frame)
        fuel_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(fuel_frame, text="Yakıt:", font=("Arial", 12), width=80, anchor="w").pack(side="left", padx=5)
        self.value_labels['fuel'] = ctk.CTkLabel(fuel_frame, text="100%", width=120, anchor="w")
        self.value_labels['fuel'].pack(side="right", padx=5)
        
        # LED durumları
        led_frame = ctk.CTkFrame(self.visualization_frame)
        led_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(led_frame, text="LED Durumları:", font=("Arial", 12, "bold")).pack()
        
        led_grid = ctk.CTkFrame(led_frame)
        led_grid.pack(fill="x", padx=5, pady=5)
        led_grid.grid_columnconfigure((0,1), weight=1)
        
        # LED'ler
        self.status_labels['led_green'] = ctk.CTkLabel(led_grid, text="🟢 Yeşil: Kapalı", text_color="gray")
        self.status_labels['led_green'].grid(row=0, column=0, padx=5, pady=2)
        
        self.status_labels['led_blue'] = ctk.CTkLabel(led_grid, text="🔵 Mavi: Kapalı", text_color="gray")
        self.status_labels['led_blue'].grid(row=0, column=1, padx=5, pady=2)
        
        self.status_labels['led_red'] = ctk.CTkLabel(led_grid, text="🔴 Kırmızı: Kapalı", text_color="gray")
        self.status_labels['led_red'].grid(row=1, column=0, padx=5, pady=2)
        
        self.status_labels['led_speed'] = ctk.CTkLabel(led_grid, text="🟡 Hız: Kapalı", text_color="gray")
        self.status_labels['led_speed'].grid(row=1, column=1, padx=5, pady=2)
        
        self.status_labels['led_fuel'] = ctk.CTkLabel(led_grid, text="🟠 Yakıt: Kapalı", text_color="gray")
        self.status_labels['led_fuel'].grid(row=2, column=0, columnspan=2, padx=5, pady=2)
    
    def _build_monitor_frame(self, parent):
        """Monitör frame'ini oluştur"""
        self.monitor_frame = ctk.CTkFrame(parent)
        self.monitor_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
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
        """Sim Arduino durumunu güncelle"""
        if connected:
            self.status_labels['sim'].configure(text="✅ Bağlı", text_color="green")
        else:
            self.status_labels['sim'].configure(text="❌ Bağlantı yok", text_color="red")
    
    def _update_real_status(self, connected: bool):
        """Real Arduino durumunu güncelle"""
        if connected:
            self.status_labels['real'].configure(text="✅ Bağlı", text_color="green")
        else:
            self.status_labels['real'].configure(text="❌ Bağlantı yok", text_color="red")
    
    def _on_vehicle_state_change(self, state: VehicleState):
        """Araç durumu değiştiğinde çağrılır"""
        # GUI güncellemelerini ana thread'de yap
        self.after(0, lambda: self._update_vehicle_display(state))
    
    def _update_vehicle_display(self, state: VehicleState):
        """Araç durumunu görsel olarak güncelle"""
        # Motor durumu
        if state.motor_status:
            self.status_labels['motor'].configure(text="✅ Açık", text_color="green")
            self.status_labels['led_green'].configure(text="🟢 Yeşil: Açık", text_color="green")
        else:
            self.status_labels['motor'].configure(text="❌ Kapalı", text_color="red")
            self.status_labels['led_green'].configure(text="🟢 Yeşil: Kapalı", text_color="gray")
        
        # Klima durumu
        if state.climate_status:
            self.status_labels['climate'].configure(text="✅ Açık", text_color="green")
            self.status_labels['led_blue'].configure(text="🔵 Mavi: Açık", text_color="blue")
        else:
            self.status_labels['climate'].configure(text="❌ Kapalı", text_color="red")
            self.status_labels['led_blue'].configure(text="🔵 Mavi: Kapalı", text_color="gray")
        
        # Acil durum
        if state.emergency_status:
            self.status_labels['emergency'].configure(text="❌ Acil Durum", text_color="red")
            self.status_labels['led_red'].configure(text="🔴 Kırmızı: Açık", text_color="red")
        else:
            self.status_labels['emergency'].configure(text="✅ Sorun yok", text_color="green")
            self.status_labels['led_red'].configure(text="🔴 Kırmızı: Kapalı", text_color="gray")
        
        # Hız
        self.value_labels['speed'].configure(text=f"{state.speed:.1f} km/h")
        if state.speed > state.speed_limit:
            self.status_labels['led_speed'].configure(text="🟡 Hız: Açık", text_color="orange")
        else:
            self.status_labels['led_speed'].configure(text="🟡 Hız: Kapalı", text_color="gray")
        
        # Yakıt
        self.value_labels['fuel'].configure(text=f"{state.fuel_level:.1f}%")
        if state.fuel_level < state.fuel_critical_level:
            self.status_labels['led_fuel'].configure(text="🟠 Yakıt: Açık", text_color="orange")
        else:
            self.status_labels['led_fuel'].configure(text="🟠 Yakıt: Kapalı", text_color="gray")
    
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
