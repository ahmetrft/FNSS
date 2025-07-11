"""core.scheduler
Merkezi zamanlayıcı – belirli aralıklarla çalışan arka plan görevlerini yönetir.
Basit thread-başına-job yaklaşımı kullanır.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict


class _Job(threading.Thread):
    def __init__(self, name: str, func: Callable[[], None], interval: float):
        super().__init__(daemon=True, name=f"Job-{name}")
        self._name = name
        self._func = func
        self._interval = max(0.01, interval)
        self._stop_event = threading.Event()

    def run(self):
        # Her döngüde fonksiyonu çağır, sonra interval bekle.
        while not self._stop_event.is_set():
            try:
                self._func()
            except Exception as e:
                # Görev içi hataları bastırmak yerine yazdır.
                print(f"Scheduler job '{self._name}' error: {e}")
            # Küçük parçalı bekleme ile hızlı durdurma imkânı.
            total_sleep = 0.0
            while total_sleep < self._interval and not self._stop_event.is_set():
                time.sleep(min(0.05, self._interval - total_sleep))
                total_sleep += 0.05

    def stop(self):
        self._stop_event.set()


class Scheduler:
    """Singleton Scheduler"""

    _instance: 'Scheduler' | None = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._jobs: Dict[str, _Job] = {}

    # ------------------- Public API -------------------
    def add_job(self, name: str, func: Callable[[], None], interval: float, *, replace: bool = True):
        """Yeni bir arka plan görevi ekle.
        name           : benzersiz iş adı (string)
        func           : çağrılacak fonksiyon (args yok)
        interval (sec) : çağrılar arasındaki süre
        replace        : aynı isimde job varsa önce durdurup yenisini ekle
        """
        if name in self._jobs:
            if not replace:
                raise ValueError(f"Job '{name}' already exists")
            self.remove_job(name)
        job = _Job(name, func, interval)
        self._jobs[name] = job
        job.start()

    def remove_job(self, name: str):
        job = self._jobs.pop(name, None)
        if job:
            job.stop()

    def list_jobs(self):
        return list(self._jobs.keys())

    def stop_all(self):
        for name in list(self._jobs.keys()):
            self.remove_job(name)


# Global Scheduler instance
scheduler = Scheduler() 