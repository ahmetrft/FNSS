#!/usr/bin/env python3
"""
HIL Test Uygulaması Başlatma Scripti
Bu script HIL uygulamasını çalıştırır.
"""

import sys
import os

# Proje kök dizinini Python path'ine ekle
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

def main():
    """Ana fonksiyon"""
    try:
        # HIL uygulamasını başlat
        from src.hil_main import HILMainWindow
        import customtkinter as ctk
        
        # Uygulama ayarları
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Ana pencereyi oluştur ve çalıştır
        app = HILMainWindow()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
        
    except ImportError as e:
        print(f"Modül import hatası: {e}")
        print("Lütfen gerekli kütüphanelerin yüklü olduğundan emin olun.")
        print("Gerekli kütüphaneler: customtkinter, pyserial")
        return 1
        
    except Exception as e:
        print(f"Uygulama başlatma hatası: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 