import threading
import time
import serial
import serial.tools.list_ports
import queue
from typing import Optional, Callable, List
from datetime import datetime

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
        
        # Queues
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        
        # Callbacks
        self.message_callbacks: List[Callable[[str, str], None]] = []
        self.connection_callbacks: List[Callable[[bool], None]] = []
        
        # Statistics
        self.sent_count = 0
        self.received_count = 0
    
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
        """Gerçekten mevcut (takılı) seri portları döndürür; fallback eklemez."""
        try:
            return [port.device for port in serial.tools.list_ports.comports()]
        except Exception:
            return []
    
    def connect(self, port: str = None, baudrate: int = None) -> bool:
        """Serial bağlantısını aç"""
        if self.is_connected:
            return True
        
        if port:
            self.port_name = port
        if baudrate:
            self.baudrate = baudrate
        
        try:
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=1)
            time.sleep(1)  # Connection stabilization
            
            self.is_connected = True
            
            # Start serial thread
            self.serial_thread = SerialThread(self.serial_port, self.send_queue, self.receive_queue)
            self.serial_thread.start()
            
            # Notify callbacks
            self._notify_connection_callbacks(True)
            
            return True
            
        except serial.SerialException as e:
            self._notify_message_callbacks("Hata", f"Serial bağlantısı açılamadı: {e}")
            return False
        except Exception as e:
            self._notify_message_callbacks("Hata", f"Beklenmeyen hata: {e}")
            return False

    def disconnect(self):
        """Serial bağlantısını kapat"""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.is_connected = False
        self._notify_connection_callbacks(False)
        self._notify_message_callbacks("Sistem", "Serial bağlantısı kapatıldı")
    
    def send_message(self, message: str) -> bool:
        """Mesaj gönder"""
        if not self.is_connected:
            self._notify_message_callbacks("Hata", "Serial bağlantısı yok")
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
            self._notify_message_callbacks("Hata", f"Mesaj gönderilemedi: {e}")
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
            'baudrate': self.baudrate
        }
    
    def reset_stats(self):
        """İstatistikleri sıfırla"""
        self.sent_count = 0
        self.received_count = 0


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
                        # Yanıt alındı, yeni komut gönderilebilir
                        self._waiting_resp = False
                
                # Timeout: 300 ms içinde yanıt gelmezse beklemeyi bırak
                if self._waiting_resp and (time.time() - self._last_send_ts) > 0.3:
                    self._waiting_resp = False

                time.sleep(0.005)  # Reduce CPU usage
                
            except Exception as e:
                self.receive_queue.put(f"Serial thread hatası: {e}")
                break
    
    def stop(self):
        self.running = False


# Global instance
serial_manager = SerialManager() 