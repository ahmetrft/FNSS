import customtkinter as ctk
from utils.logger import bring_to_front_and_center
from core.serial_manager import serial_manager
import threading
import time
from datetime import datetime

class SerialMonitor(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Serial Monitor - Arduino Haberleşme")
        # Daha geniş pencere
        self.geometry("950x600")
        self.resizable(True, True)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Serial communication variables
        self.is_connected = False
        
        # UI variables
        self.auto_scroll = ctk.BooleanVar(value=True)
        self.show_timestamps = ctk.BooleanVar(value=True)
        self.show_sent = ctk.BooleanVar(value=True)
        self.show_received = ctk.BooleanVar(value=True)
        
        # Message counters
        self.sent_count = 0
        self.received_count = 0
        
        # Register callbacks
        serial_manager.add_message_callback(self.on_message_received)
        serial_manager.add_connection_callback(self.on_connection_changed)
        
        self._build_layout()
        bring_to_front_and_center(self)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start polling for received messages
        self.poll_serial()
        
        # Initialize port list
        self.refresh_ports()
        
        # Update connection status
        self.update_connection_status()
    
    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        try:
            ports = serial_manager.get_available_ports()
            self.port_menu.configure(values=ports)
            
            # Keep current selection if it's still valid
            current_port = self.port_var.get()
            if current_port not in ports and ports:
                self.port_var.set(ports[0])
            
            self.log_message("Sistem", f"Port listesi güncellendi: {len(ports)} port bulundu", "info")
            
        except Exception as e:
            self.log_message("Hata", f"Port listesi alınamadı: {e}", "error")
    
    def on_port_change(self, value):
        """Called when port selection changes"""
        self.log_message("Sistem", f"Port seçildi: {value}", "info")
    
    def _build_layout(self):
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Connection frame
        connection_frame = ctk.CTkFrame(main_frame)
        connection_frame.pack(fill="x", padx=5, pady=5)
        
        # Port selection
        ctk.CTkLabel(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        # Varsayılan port: bağlıysa aktif port, değilse config'ten okunan değer
        try:
            from core.config import load_config as _load_cfg
            cfg_default = _load_cfg().get("serial_port", "COM7")
        except Exception:
            cfg_default = "COM"

        default_port = serial_manager.get_stats().get("port_name", cfg_default) if serial_manager.is_connected else cfg_default

        # Port listesi
        try:
            port_list = serial_manager.get_available_ports()
        except Exception:
            port_list = [default_port]

        # Eğer hiç port bulunamazsa kullanıcıya boş bir menü gösterilecek; en azından tek eleman ekleyelim
        if not port_list:
            port_list = ["YOK"]

        # OptionMenu
        initial_port = default_port if default_port in port_list else port_list[0]
        self.port_var = ctk.StringVar(value=initial_port)
        self.port_menu = ctk.CTkOptionMenu(
            connection_frame,
            values=port_list,
            variable=self.port_var,
            command=self.on_port_change,  # on_port_change zaten var
            width=100
        )
        self.port_menu.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Refresh ports button
        ctk.CTkButton(connection_frame, text="🔄", command=self.refresh_ports, width=40).grid(row=0, column=2, padx=2, pady=5, sticky="w")
        
        # Baudrate selection
        ctk.CTkLabel(connection_frame, text="Baudrate:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.baudrate_var = ctk.StringVar(value="9600")
        baudrate_options = ["9600", "19200", "38400", "57600", "115200"]
        self.baudrate_menu = ctk.CTkOptionMenu(connection_frame, values=baudrate_options, variable=self.baudrate_var)
        self.baudrate_menu.grid(row=0, column=4, padx=5, pady=5, sticky="w")
        
        # Connect/Disconnect button
        self.connect_btn = ctk.CTkButton(connection_frame, text="Bağlan", command=self.toggle_connection, width=100)
        self.connect_btn.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        
        # Status label
        self.status_label = ctk.CTkLabel(connection_frame, text="Bağlantı yok", text_color="red")
        self.status_label.grid(row=0, column=6, padx=10, pady=5, sticky="w")
        
        # Message counter label
        self.counter_label = ctk.CTkLabel(connection_frame, text="Gönderilen: 0 | Alınan: 0")
        self.counter_label.grid(row=0, column=7, padx=10, pady=5, sticky="w")
        
        # Options frame
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", padx=5, pady=5)
        
        # Checkboxes for display options
        ctk.CTkCheckBox(options_frame, text="Otomatik kaydır", variable=self.auto_scroll).pack(side="left", padx=5, pady=5)
        ctk.CTkCheckBox(options_frame, text="Zaman damgası", variable=self.show_timestamps).pack(side="left", padx=5, pady=5)
        ctk.CTkCheckBox(options_frame, text="Gönderilen", variable=self.show_sent).pack(side="left", padx=5, pady=5)
        ctk.CTkCheckBox(options_frame, text="Alınan", variable=self.show_received).pack(side="left", padx=5, pady=5)
        
        # Clear button
        ctk.CTkButton(options_frame, text="Temizle", command=self.clear_monitor, width=80).pack(side="right", padx=5, pady=5)
        
        # Monitor text area
        monitor_frame = ctk.CTkFrame(main_frame)
        monitor_frame.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Text widget with scrollbar
        self.monitor_text = ctk.CTkTextbox(monitor_frame, font=("Consolas", 10))
        self.monitor_text.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Send frame
        send_frame = ctk.CTkFrame(main_frame)
        send_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(send_frame, text="Mesaj:").pack(side="left", padx=5, pady=5)
        self.message_entry = ctk.CTkEntry(send_frame, placeholder_text="Gönderilecek mesajı yazın...")
        self.message_entry.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        self.message_entry.bind("<Return>", self.send_message)
        
        self.send_btn = ctk.CTkButton(send_frame, text="Gönder", command=self.send_message, width=80)
        self.send_btn.pack(side="right", padx=5, pady=5)
    
    def toggle_connection(self):
        if not self.is_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        # Eğer zaten bağlıysa tekrar deneme ve loglama yapma
        if serial_manager.is_connected:
            return

        try:
            port = self.port_var.get()
            baudrate = int(self.baudrate_var.get())

            if serial_manager.connect(port, baudrate):
                self.log_message("Sistem", f"Serial bağlantısı açıldı: {port} @ {baudrate} bps", "info")
            else:
                self.log_message("Hata", "Serial bağlantısı açılamadı", "error")
            
        except Exception as e:
            self.log_message("Hata", f"Beklenmeyen hata: {e}", "error")
    
    def disconnect_serial(self):
        # SerialManager zaten kapatıldığında "Serial bağlantısı kapatıldı" mesajını yayınlıyor.
        # Burada yeniden loglamaya gerek yok, aksi halde iki kez görünür.
        serial_manager.disconnect()
    
    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        if not message:
            return
        
        if serial_manager.send_message(message):
            # Mesaj GUI'de yalnızca callback üzerinden gösterilecek, burada tekrar yazdırma
            self.message_entry.delete(0, "end")
        else:
            self.log_message("Hata", "Mesaj gönderilemedi", "error")
    
    def log_message(self, source, message, msg_type="info"):
        # Sayısal 14-19 pin numaralarını (Arduino analog pinleri) A0-A5 etiketiyle değiştir
        pin_alias = {14: "A0", 15: "A1", 16: "A2", 17: "A3", 18: "A4", 19: "A5"}
        for num, name in pin_alias.items():
            message = message.replace(f"PIN {num}", f"PIN {name}")
            message = message.replace(f"{num}:", f"{name}:")

        if not self.show_timestamps.get():
            timestamp = ""
        else:
            timestamp = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
        
        # Color coding based on message type
        color_map = {
            "info": "#007ACC",      # Blue
            "error": "#FF3B30",     # Red
            "sent": "#34C759",      # Green
            "received": "#FF9500"   # Orange
        }
        
        color = color_map.get(msg_type, "#000000")
        
        # Format the message
        formatted_msg = f"{timestamp}[{source}] {message}\n"
        
        # Insert with color
        self.monitor_text.insert("end", formatted_msg)
        
        # Apply color to the last line
        last_line_start = self.monitor_text.index("end-2c linestart")
        last_line_end = self.monitor_text.index("end-1c")
        self.monitor_text.tag_add(f"color_{msg_type}", last_line_start, last_line_end)
        self.monitor_text.tag_config(f"color_{msg_type}", foreground=color)
        
        # Auto-scroll if enabled
        if self.auto_scroll.get():
            self.monitor_text.see("end")
        
        # Update counter
        self.update_counter()
    
    def update_counter(self):
        """Update the message counter display"""
        self.counter_label.configure(text=f"Gönderilen: {self.sent_count} | Alınan: {self.received_count}")
    
    def increment_sent(self):
        """Increment sent message counter"""
        self.sent_count += 1
        self.update_counter()
    
    def increment_received(self):
        """Increment received message counter"""
        self.received_count += 1
        self.update_counter()
    
    def clear_monitor(self):
        self.monitor_text.delete("1.0", "end")
        serial_manager.reset_stats()
        self.sent_count = 0
        self.received_count = 0
        self.update_counter()
    
    def on_message_received(self, source: str, message: str):
        """Serial manager'dan gelen mesajları işle"""
        if source == "Alınan" and self.show_received.get():
            self.log_message("Alınan", message, "received")
        elif source == "Gönderilen" and self.show_sent.get():
            self.log_message("Gönderilen", message, "sent")
        elif source in ["Sistem", "Hata"]:
            self.log_message(source, message, "info" if source == "Sistem" else "error")
    
    def on_connection_changed(self, connected: bool):
        """Bağlantı durumu değiştiğinde çağrılır"""
        self.is_connected = connected
        self.update_connection_status()
    
    def update_connection_status(self):
        """Bağlantı durumunu UI'da güncelle"""
        stats = serial_manager.get_stats()
        # Dahili durum değişkenini her zaman güncel tut
        self.is_connected = stats['is_connected']

        if self.is_connected:
            # Port menüsünde bağlı portu seçili hale getir
            connected_port = stats['port_name']
            if connected_port not in self.port_menu.cget("values"):
                # Menü değerleri bağlı portu içermiyorsa yenile
                self.refresh_ports()
            self.port_var.set(connected_port)

            self.connect_btn.configure(text="Bağlantıyı Kes")
            self.status_label.configure(text=f"Bağlı: {connected_port} @ {stats['baudrate']} bps", text_color="green")
        else:
            self.connect_btn.configure(text="Bağlan")
            self.status_label.configure(text="Bağlantı yok", text_color="red")
    
    def poll_serial(self):
        """Poll for received messages from the serial thread"""
        serial_manager.poll_messages()
        
        # Update counters from manager stats
        stats = serial_manager.get_stats()
        self.sent_count = stats['sent_count']
        self.received_count = stats['received_count']
        self.update_counter()
        
        # Schedule next poll
        self.after(100, self.poll_serial)
    
    def on_closing(self):
        # Callbacks'leri kaldır
        serial_manager.remove_message_callback(self.on_message_received)
        serial_manager.remove_connection_callback(self.on_connection_changed)
        
        # Ana pencereye referansı temizle
        if hasattr(self.master, 'serial_monitor'):
            self.master.serial_monitor = None
        self.destroy()


 