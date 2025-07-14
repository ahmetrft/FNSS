import threading
import time
import serial
import serial.tools.list_ports
import queue
from typing import Optional, Callable, List
from datetime import datetime
import json
import os
from core.config import get_config_path

class SerialManager:
    """Merkezi serial haberleşme yöneticisi"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        # Serial connection
        self.serial_port: Optional[serial.Serial] = None
        self.serial_thread: Optional[SerialThread] = None
        self.is_connected = False
        self.port_name = "COM4"
        self.baudrate = 9600
        
        # Son başarılı port bilgisini yükle
        self.last_successful_port = None
        self._load_last_successful_port()
        
        # Queues
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        
        # Callbacks
        self.message_callbacks: List[Callable[[str, str], None]] = []
        self.connection_callbacks: List[Callable[[bool], None]] = []
        
        # Statistics
        self.sent_count = 0
        self.received_count = 0
    
    def _load_last_successful_port(self):
        """Son başarılı port bilgisini dosyadan yükle"""
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.last_successful_port = config.get("last_successful_port")
        except Exception:
            pass
    
    def _save_last_successful_port(self):
        """Son başarılı port bilgisini dosyaya kaydet"""
        try:
            config_path = get_config_path()
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config["last_successful_port"] = self.last_successful_port
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def add_message_callback(self, callback: Callable[[str, str], None]):
        """Mesaj alındığında çağrılacak callback ekle"""
        if callback not in self.message_callbacks:
            self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable[[str, str], None]):
        """Mesaj callback'ini kaldır"""
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
    
    def add_connection_callback(self, callback: Callable[[bool], None]):
        """Bağlantı durumu değiştiğinde çağrılacak callback ekle"""
        if callback not in self.connection_callbacks:
            self.connection_callbacks.append(callback)
    
    def remove_connection_callback(self, callback: Callable[[bool], None]):
        """Bağlantı callback'ini kaldır"""
        if callback in self.connection_callbacks:
            self.connection_callbacks.remove(callback)
    
    def get_available_ports(self) -> List[str]:
        """Gerçekten mevcut (takılı) seri portları döndürür"""
        try:
            return [port.device for port in serial.tools.list_ports.comports()]
        except Exception:
            return []
    
    def find_arduino_port(self, timeout: float = 3.0) -> Optional[str]:
        """Arduino portunu bul - basit ve hızlı"""
        # Eğer zaten bağlıysa, mevcut portu döndür
        if self.is_connected:
            return self.port_name
            
        available_ports = self.get_available_ports()
        
        if not available_ports:
            return None
        
        # Son başarılı portu ilk sıraya al
        if self.last_successful_port and self.last_successful_port in available_ports:
            available_ports.remove(self.last_successful_port)
            available_ports.insert(0, self.last_successful_port)
        
        for port in available_ports:
            if self._test_port_quick(port, timeout):
                self.last_successful_port = port
                self._save_last_successful_port()
                return port
        
        return None
    
    def _test_port_quick(self, port: str, timeout: float) -> bool:
        """Portu hızlıca test et"""
        test_serial = None
        response_received = False
        try:
            # Portu aç
            test_serial = serial.Serial(port, self.baudrate, timeout=timeout)
            time.sleep(0.2)  # Kısa bağlantı stabilizasyonu
            
            # Port açıldı mı kontrol et
            if not test_serial.is_open:
                return False
            
            # Önce mevcut veriyi temizle
            test_serial.reset_input_buffer()
            test_serial.reset_output_buffer()
            
            # Arduino'nun tam olarak başlaması için bekle
            time.sleep(2.0)  # Arduino'nun başlaması için 2 saniye bekle
            
            # Test mesajı gönder
            test_message = "TEST\n"
            test_serial.write(test_message.encode('utf-8'))
            test_serial.flush()
            
            # Yanıt bekle
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if test_serial.in_waiting:
                    try:
                        response = test_serial.readline().decode('utf-8', errors='ignore').strip()
                        
                        if response == "1":
                            response_received = True
                            break
                        elif response:  # Boş olmayan başka bir yanıt
                            pass # Debug mesajları kaldırıldı
                    except Exception as e:
                        pass # Debug mesajları kaldırıldı
                time.sleep(0.1)
            
            if response_received:
                # Test başarılı! Bu bağlantıyı kullan
                self.serial_port = test_serial
                self.port_name = port
                self.is_connected = True
                
                # Start serial thread
                self.serial_thread = SerialThread(self.serial_port, self.send_queue, self.receive_queue)
                self.serial_thread.start()
                
                # Notify callbacks
                self._notify_connection_callbacks(True)
                
                return True
            
            return False
            
        except Exception as e:
            # Port açılamadı
            return False
        finally:
            # Sadece başarısız olursa kapat
            if not response_received and test_serial and test_serial.is_open:
                try:
                    test_serial.close()
                except Exception:
                    pass
    
    def connect(self, port: str = None, baudrate: int = None, test_connection: bool = True) -> bool:
        """Serial bağlantısını aç"""
        if self.is_connected:
            return True
        
        # Eğer port belirtilmişse
        if port and not self.is_connected:
            self.port_name = port
            if baudrate:
                self.baudrate = baudrate
            
            # Test modu aktifse test et, değilse direkt bağlan
            if test_connection:
                return self._test_port_quick(port, 3.0)
            else:
                return self._connect_direct(port, baudrate)
        
        return False
    
    def _connect_direct(self, port: str, baudrate: int = None) -> bool:
        """Direkt bağlantı kur (test yapmadan)"""
        try:
            self.serial_port = serial.Serial(port, self.baudrate, timeout=1)
            time.sleep(1)  # Connection stabilization
            
            self.is_connected = True
            
            # Start serial thread
            self.serial_thread = SerialThread(self.serial_port, self.send_queue, self.receive_queue)
            self.serial_thread.start()
            
            # Notify callbacks
            self._notify_connection_callbacks(True)
            
            return True
            
        except serial.SerialException as e:
            return False
        except Exception as e:
            return False

    def disconnect(self):
        """Serial bağlantısını kapat"""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
        
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass  # Port zaten kapanmış olabilir
        
        self.is_connected = False
        self._notify_connection_callbacks(False)
    
    def send_message(self, message: str) -> bool:
        """Mesaj gönder"""
        if not self.is_connected:
            return False
        
        try:
            # Add newline if not present
            if not message.endswith('\n'):
                message += '\n'
            
            self.send_queue.put(message)
            self.sent_count += 1
            # GÖNDERİLEN MESAJI CALLBACK İLE YAZDIR
            self._notify_message_callbacks("Gönderilen", message.strip())
            
            return True
            
        except Exception as e:
            return False
    
    def send_command(self, pin, state):
        """Pin durumu komutu gönder"""
        # Analog pinler için A0->14, A1->15 ...
        if isinstance(pin, str) and pin.startswith("A"):
            pin_num = 14 + int(pin[1])
        else:
            pin_num = pin
        cmd = f"{pin_num},{state}\n"
        return self.send_message(cmd)
    
    def send_pwm_command(self, pin, value):
        """PWM komutu gönder"""
        # Pin modunu değiştirme, sadece PWM değerini gönder
        if isinstance(pin, str) and pin.startswith("A"):
            pin_num = 14 + int(pin[1])
        else:
            pin_num = pin
        cmd = f"PWM {pin_num},{value}\n"
        return self.send_message(cmd)
    
    def send_mode_command(self, pin, mode):
        """Pin modu komutu gönder"""
        if isinstance(pin, str) and pin.startswith("A"):
            pin_num = 14 + int(pin[1])
        else:
            pin_num = pin
        cmd = f"MODE {pin_num},{mode}\n"
        return self.send_message(cmd)

    # send_all_mode_command kaldırıldı – ALLMODE artık desteklenmiyor
    
    def send_all_command(self, state: int):
        """Tüm pinleri aynı anda aç/kapat (state 0 veya 1)"""
        state = 1 if state else 0
        cmd = f"ALL {state}\n"
        return self.send_message(cmd)
    
    def poll_messages(self):
        """Alınan mesajları işle"""
        try:
            while True:
                message = self.receive_queue.get_nowait()
                self.received_count += 1
                self._notify_message_callbacks("Alınan", message)
        except queue.Empty:
            pass
    
    def _notify_message_callbacks(self, source: str, message: str):
        """Mesaj callback'lerini çağır"""
        for callback in self.message_callbacks[:]:  # Copy list to avoid modification during iteration
            try:
                callback(source, message)
            except Exception as e:
                print(f"Message callback error: {e}")
    
    def _notify_connection_callbacks(self, connected: bool):
        """Bağlantı callback'lerini çağır"""
        for callback in self.connection_callbacks[:]:  # Copy list to avoid modification during iteration
            try:
                callback(connected)
            except Exception as e:
                print(f"Connection callback error: {e}")
    
    def get_stats(self) -> dict:
        """İstatistikleri döndür"""
        return {
            'sent_count': self.sent_count,
            'received_count': self.received_count,
            'is_connected': self.is_connected,
            'port_name': self.port_name,
            'baudrate': self.baudrate,
            'last_successful_port': self.last_successful_port
        }
    
    def reset_stats(self):
        """İstatistikleri sıfırla"""
        self.sent_count = 0
        self.received_count = 0

    def handle_connection_lost(self):
        self.is_connected = False
        self._notify_connection_callbacks(False)


class SerialThread(threading.Thread):
    """Serial haberleşme thread'i"""
    
    def __init__(self, serial_port, send_queue, receive_queue):
        super().__init__(daemon=True)
        self.serial_port = serial_port
        self.send_queue = send_queue
        self.receive_queue = receive_queue
        self.running = True
        self._waiting_resp = False
        self._last_send_ts = 0.0
    
    def run(self):
        import sys
        while self.running:
            try:
                # Sırayla gönder: yanıt gelmeden yenisini yollama
                if not self._waiting_resp:
                    try:
                        message = self.send_queue.get_nowait()
                        self.serial_port.write(message.encode('utf-8'))
                        self.serial_port.flush()
                        self._waiting_resp = True
                        self._last_send_ts = time.time()
                    except queue.Empty:
                        pass
                # Receive messages
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.receive_queue.put(line)
                        self._waiting_resp = False
                # Timeout: 300 ms içinde yanıt gelmezse beklemeyi bırak
                if self._waiting_resp and (time.time() - self._last_send_ts) > 0.3:
                    self._waiting_resp = False
                time.sleep(0.005)
            except (OSError, PermissionError) as e:
                # Bağlantı koptu - thread'i durdur ve ana thread'e bildir
                self.receive_queue.put(f"Serial thread hatası: Bağlantı koptu")
                # SerialManager'a bildir
                from core.serial_manager import serial_manager
                serial_manager.handle_connection_lost()
                break
            except Exception as e:
                self.receive_queue.put(f"Serial thread hatası: {e}")
                from core.serial_manager import serial_manager
                serial_manager.handle_connection_lost()
                break
    
    def stop(self):
        self.running = False


# Global instance
serial_manager = SerialManager() 