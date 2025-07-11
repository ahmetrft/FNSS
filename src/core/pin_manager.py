"""core.pin_manager
Üst seviye pin işlemleri (mode, dijital yaz/oku, pwm yaz/oku) için tek giriş noktası.
SerialManager üzerinden haberleşir, MessageRouter'dan gelen olaylarla dahili durumu günceller.
"""
from __future__ import annotations

from typing import Dict, Callable, Any

from core.serial_manager import serial_manager
from core.message_router import message_router


class PinManager:
    _instance: 'PinManager' | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        # Dahili durum tabloları
        self.pin_modes: Dict[int, int] = {}      # 0=input, 1=output
        self.pin_states: Dict[int, int] = {}     # 0/1 veya pwm değeri (0-255)
        self.analog_values: Dict[str, int] = {}
        # Event dinleyici listesi
        self._listeners: Dict[str, list[Callable[[Any], None]]] = {}
        # Mesaj yönlendirici aboneliği
        message_router.add_listener("pin_state", self._on_pin_state)
        message_router.add_listener("analog_value", self._on_analog_value)

    # --------------- Public API ---------------
    def set_mode(self, pin: int, mode: int):
        """Belirtilen pin için modu ayarla.
        mode: 0=input, 1=output, 2=pas (inactive)
        """
        if mode not in (0, 1, 2):
            mode = 0
        serial_manager.send_mode_command(pin, mode)
        self.pin_modes[pin] = mode

    # set_all_modes kaldırıldı – ALLMODE komutu desteklenmiyor

    def write_digital(self, pin: int, value: int):
        serial_manager.send_command(pin, 1 if value else 0)
        self.pin_states[pin] = 1 if value else 0

    def write_pwm(self, pin: int, value: int):
        value = max(0, min(255, int(value)))
        serial_manager.send_pwm_command(pin, value)
        self.pin_states[pin] = value

    def request_digital_read(self):
        serial_manager.send_message("DIG")

    def request_analog_read(self):
        serial_manager.send_message("ANA")

    def get_pin_state(self, pin: int):
        return self.pin_states.get(pin, 0)

    def get_analog_value(self, name: str):
        return self.analog_values.get(name, 0)

    # Listener kayıt
    def add_listener(self, event_type: str, callback: Callable[[Any], None]):
        self._listeners.setdefault(event_type, []).append(callback)

    def remove_listener(self, event_type: str, callback: Callable[[Any], None]):
        lst = self._listeners.get(event_type)
        if lst and callback in lst:
            lst.remove(callback)

    # --------------- Config Apply ---------------
    def apply_config(self, config_data: dict):
        """Verilen konfigürasyondaki pin modlarını Arduino'ya gönderir.
        config_data: load_config() çıktısı formatında sözlük
        """
        # Lazy import burada yapılır ki döngüsel import sorunu olmasın
        from core.config import DIGITAL_PINS, ANALOG_PINS

        import time  # Gerektiğinde küçük gecikme eklemek için

        # Dijital pinler (2-13)
        for pin in DIGITAL_PINS:
            conf = config_data.get("pins", {}).get(str(pin), {})
            mode_str = conf.get("mode", "output")
            if mode_str == "pas":
                self.set_mode(pin, 2)
            elif mode_str == "output":
                self.set_mode(pin, 1)
            else:
                self.set_mode(pin, 0)
            # no delay here

        # Analog pinler (A0-A5 -> 14-19)
        for idx, name in enumerate(ANALOG_PINS):
            conf = config_data.get("pins", {}).get(name, {})
            arduino_pin = 14 + idx
            mode_str = conf.get("mode", "input")
            if mode_str == "pas":
                self.set_mode(arduino_pin, 2)
            elif mode_str == "output":
                self.set_mode(arduino_pin, 1)
            else:
                self.set_mode(arduino_pin, 0)
            # no delay

        # Durum tablosu zaten set_mode içinde güncelleniyor

    # --------------- Internal Callbacks ---------------
    def _notify(self, event_type: str, data: Any):
        for cb in self._listeners.get(event_type, []):
            try:
                cb(data)
            except Exception as e:
                print(f"PinManager listener error ({event_type}): {e}")

    def _on_pin_state(self, data: Dict[str, Any]):
        pin = data["pin"]
        value = data["value"]
        self.pin_states[pin] = value
        self._notify("pin_state", data)

    def _on_analog_value(self, data: Dict[str, Any]):
        name = data["pin"]
        value = data["value"]
        self.analog_values[name] = value
        self._notify("analog_value", data)


# Global instance
pin_manager = PinManager()
