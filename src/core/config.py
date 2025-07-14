# core/config.py

import json
import os
import sys

def get_config_path():
    # Her zaman exe'nin bulunduğu dizini kullan
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    return config_path

CONFIG_FILE = get_config_path()

PWM_DIGITAL_PINS = [3, 5, 6, 9, 10, 11]
DIGITAL_PINS = list(range(2, 14))
ANALOG_PINS = [f"A{i}" for i in range(6)]

# Varsayılan pin konfigürasyonu
DEFAULT_PINS_CONFIG = {}
for p in DIGITAL_PINS:
    DEFAULT_PINS_CONFIG[str(p)] = {
        "mode": "output",  # input / output / pas
        "type": "pwm" if p in PWM_DIGITAL_PINS else "digital"  # digital / pwm
    }
for a in ANALOG_PINS:
    DEFAULT_PINS_CONFIG[a] = {
        "mode": "input",  # analog pinler varsayılan input
        "type": "analog"  # analog / digital
    }

DEFAULT_CONFIG = {
    "pins": DEFAULT_PINS_CONFIG
}

# Global config object (dict)
CONFIG = None

def load_config():
    """Load configuration from JSON file or return default."""
    global CONFIG
    if CONFIG is not None:
        return CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                CONFIG = json.load(f)
        except Exception:
            CONFIG = DEFAULT_CONFIG.copy()
    else:
        CONFIG = DEFAULT_CONFIG.copy()
    # Eksik anahtarları tamamla
    for key, value in DEFAULT_CONFIG.items():
        if key not in CONFIG:
            CONFIG[key] = value
    # Pins eksikse ekle
    if "pins" not in CONFIG:
        CONFIG["pins"] = DEFAULT_PINS_CONFIG.copy()
    else:
        # 'active' anahtarı artık kullanılmıyor – doğrudan mode alanı bekleniyor
        # Eksik pinleri ekle
        for pin, pin_conf in DEFAULT_PINS_CONFIG.items():
            if pin not in CONFIG["pins"]:
                CONFIG["pins"][pin] = pin_conf
    return CONFIG

def save_config():
    global CONFIG
    if CONFIG is None:
        return
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        print(f"Config save error: {e}")
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Hata", f"Config dosyası kaydedilemedi:\n{e}")
        except Exception:
            pass
