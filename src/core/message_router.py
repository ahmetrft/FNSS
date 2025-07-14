"""core.message_router
SerialManager'dan gelen ham satırları ayrıştırır ve olaylara dönüştürür.
Basit bir publish/subscribe mekanizması sağlar.
Olay tipleri:
    • pin_state   : {'pin': int, 'value': int}
    • analog_value: {'pin': str, 'value': int}
    • stat        : {'entries': List[Tuple[int, int, int]]}
    • raw         : {'line': str}
"""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple, Any

from core.serial_manager import serial_manager


class MessageRouter:
    _instance: 'MessageRouter' | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        # SerialManager callback kaydı
        serial_manager.add_message_callback(self._on_serial_message)

    # ----------------- Public API -----------------
    def add_listener(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        self._listeners.setdefault(event_type, []).append(callback)

    def remove_listener(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        lst = self._listeners.get(event_type)
        if lst and callback in lst:
            lst.remove(callback)

    # ----------------- Internal -----------------
    def _dispatch(self, event_type: str, data: Dict[str, Any]):
        for cb in self._listeners.get(event_type, []):
            try:
                cb(data)
            except Exception as e:
                print(f"MessageRouter listener error ({event_type}): {e}")

    def _on_serial_message(self, source: str, line: str):
        if source != "Alınan":
            return
        line = line.strip()
        self._dispatch("raw", {"line": line})
        # Parse pin state messages e.g. "PIN 7  : ON" or "PIN 11 : 127"
        if line.startswith("PIN "):  # state change feedback
            parts = line[4:].strip()
            if parts.upper().startswith("ALL"):
                return  # toplu mesajı atla
            if ':' not in parts:
                return
            pin_part, val_part = parts.split(':', 1)
            pin_part = pin_part.strip()
            val_part = val_part.strip()
            if pin_part.isdigit():
                pin = int(pin_part)
                up_val = val_part.upper()
                if val_part.isdigit():
                    value = int(val_part)
                elif up_val in ("ON", "OFF"):
                    value = 1 if up_val == "ON" else 0
                else:
                    # IN, OUT, PAS gibi mod değişim mesajlarını görmezden gel
                    return
                self._dispatch("pin_state", {"pin": pin, "value": value})
            return
        # Dijital okuma: "D2:1,D3:0,..."
        if line.startswith("D") and ':' in line:
            entries = line.split(',')
            for ent in entries:
                if ':' in ent and ent.startswith("D"):
                    p, v = ent.split(':')
                    if p[1:].isdigit() and v.isdigit():
                        self._dispatch("pin_state", {"pin": int(p[1:]), "value": int(v)})
            return
        # Analog okuma: "A0:123,A1:456,..."
        if line.startswith("A0:"):
            for ent in line.split(','):
                if ':' in ent:
                    name, val = ent.split(':')
                    if val.isdigit():
                        self._dispatch("analog_value", {"pin": name.strip(), "value": int(val)})
            return
        # STAT cevabı: "2:1:1,3:0:1,..."
        if ':' in line and ',' in line and not line.startswith(('A', 'D')):
            entries: List[Tuple[int, int, int]] = []
            for ent in line.split(','):
                parts = ent.split(':')
                if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                    entries.append((int(parts[0]), int(parts[1]), int(parts[2])))
            if entries:
                self._dispatch("stat", {"entries": entries})
            return


# Global instance
message_router = MessageRouter() 