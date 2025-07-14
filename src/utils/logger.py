
import os
import sys

def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "src", "assets", filename)
    else:
        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", filename))


def bring_to_front_and_center(window):
    """
    Verilen pencereyi ekranın ortasında ve önde açar.
    """
    window.update_idletasks()
    w = window.winfo_width()
    h = window.winfo_height()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    window.geometry(f"{w}x{h}+{x}+{y}")
    window.lift()
    window.focus_force()
    window.attributes('-topmost', True)
    window.after(200, lambda: window.attributes('-topmost', False))


# --- Otomatik Merkezleme Yaması ---
# Tüm yeni CTkToplevel pencereleri oluşturulduktan hemen sonra
# bring_to_front_and_center fonksiyonunu çağırmak için CTkToplevel.__init__
# metodunu monkey-patch ediyoruz. Böylece projede yeni açılan her pencere
# otomatik olarak ekranda ortalanır ve öne getirilir.

import customtkinter as ctk
from functools import wraps

# Bu yama yalnızca bir kez uygulanmalı, tekrar çalıştırıldığında ikinci kez
# patch etmeyi önlemek için özel bir öznitelik kullanıyoruz.
if not getattr(ctk.CTkToplevel, "_front_center_patched", False):
    original_init = ctk.CTkToplevel.__init__

    @wraps(original_init)
    def patched_init(self, *args, **kwargs):
        # Orijinal __init__
        original_init(self, *args, **kwargs)

        # Transient ilişki kaldırıldı; böylece ana pencere tekrar öne gelebilir

        # Visibility tamamlandıktan sonra öne getir & merkezle (küçük gecikme)
        try:
            self.after(20, lambda w=self: bring_to_front_and_center(w))
        except Exception:
            pass

    ctk.CTkToplevel.__init__ = patched_init
    ctk.CTkToplevel._front_center_patched = True

# İsteğe bağlı: Ana CTk pencereleri için de benzer davranışı etkinleştirmek
# isterseniz aşağıdaki bloğu yorumdan çıkarabilirsiniz. Şimdilik yalnızca
# Toplevel pencerelerini etkiliyoruz.
# if not getattr(ctk.CTk, "_front_center_patched", False):
#     original_root_init = ctk.CTk.__init__
#     @wraps(original_root_init)
#     def patched_root_init(self, *args, **kwargs):
#         original_root_init(self, *args, **kwargs)
#         try:
#             bring_to_front_and_center(self)
#         except Exception:
#             pass
#     ctk.CTk.__init__ = patched_root_init
#     ctk.CTk._front_center_patched = True

# --- Son ---

