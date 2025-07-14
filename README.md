# FNSS - Arduino Pin Kontrol ve İzleme Uygulaması

FNSS stajımda geliştirmiş olduğum bu proje, Arduino tabanlı projelerde dijital ve analog pinlerin kolayca kontrol edilmesini ve izlenmesini sağlayan modern bir masaüstü uygulamasıdır. Kullanıcı dostu arayüzüyle pinleri anlık olarak yönetebilir, okuma/yazma işlemleri yapabilir ve otomatik patternler uygulayabilirsiniz.

## 🚀 Özellikler

### 🔌 Pin Kontrolü
- **Dijital Pinler (2-13):** Her pin için aç/kapat toggle anahtarı
- **PWM Pinler (3, 5, 6, 9, 10, 11):** 0-255 arası hassas PWM kontrolü
- **Analog Pinler (A0-A5):** Hem dijital hem analog modda kullanım
- **Anlık Görsel Geri Bildirim:** Toggle butonları canlı renk güncellemesi (Yeşil: Açık, Kırmızı: Kapalı)

### 📊 Gerçek Zamanlı İzleme
- **Dijital Okuma:** Pin durumlarını renkli göstergelerle takip et
- **Analog Okuma:** A0-A5 pinlerinden 0-1023 arası değerleri anlık görüntüle
- **Özelleştirilebilir Okuma Hızı:** Dijital ve analog okuma için ayrı ayrı zamanlama
- **Otomatik Senkronizasyon:** Arduino'dan gelen yanıtlarla görsel durumlar senkronize

### 🎭 Otomatik Patternler
- **Sıralı Pattern:** Pinleri sırayla aç/kapat (dalga efekti)
- **Blink Pattern:** Her pin için sırayla aç-kapat (sıralı yanıp sönme)
- **Hepsi Pattern:** Tüm pinleri aynı anda aç/kapat (senkronize yanıp sönme)
- **Özelleştirilebilir Hız:** Her pattern için ayrı ayrı zamanlama ayarı
- **Anlık Kontrol:** "Hepsi Açık" ve "Hepsi Kapalı" butonları ile toplu kontrol

### ⚙️ Konfigürasyon Sistemi
- **Pin Modları:** Her pin için INPUT/OUTPUT/PASIF mod seçimi
- **Pin Türleri:** Digital/PWM (dijital pinler), Analog/Digital (analog pinler)
- **Toplu Ayarlar:** "Tümü Okuma", "Tümü Yazma" butonları
- **Varsayılana Döndür:** Tek tıkla fabrika ayarlarına sıfırlama
- **Otomatik Kaydetme:** Değişiklikler anında kaydedilir

### 🔧 Serial Haberleşme
- **Otomatik Port Bulma:** Arduino portunu otomatik tespit
- **Manuel Bağlantı:** İstenilen port ve baudrate ile bağlantı
- **Serial Monitor:** Gönderilen/alınan mesajları canlı izleme
- **Mesaj Geçmişi:** Serial monitör açıldığında önceki mesaj sayılarını gösterme
- **Bağlantı Durumu:** Gerçek zamanlı bağlantı durumu takibi

### 🎨 Modern Arayüz
- **CustomTkinter:** Modern, güzel görünümlü arayüz
- **Responsive Tasarım:** Pencere boyutuna uyumlu layout
- **Renk Kodlaması:** Mesaj türlerine göre renkli gösterim
- **Otomatik Kaydırma:** Yeni mesajlar için otomatik scroll
- **Zaman Damgaları:** İsteğe bağlı zaman damgası gösterimi

## 📋 Gereksinimler

### Sistem Gereksinimleri
- **Python:** 3.7 veya üzeri
- **İşletim Sistemi:** Windows, macOS, Linux
- **Arduino:** Uno, Nano veya uyumlu board
- **Bağlantı:** USB kablosu

### Python Paketleri
```bash
pip install customtkinter
pip install pyserial
```

## 🛠️ Kurulum

### 1. Projeyi İndirin
```bash
git clone https://github.com/ahmetrft/FNSS.git
cd FNSS
```

### 2. Gerekli Paketleri Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Arduino Kodunu Yükleyin
- `src/arduino_codes/test_real/Test_real.ino` dosyasını Arduino IDE'de açın
- Arduino board'unuza yükleyin
- USB ile bilgisayara bağlayın

### 4. Uygulamayı Başlatın
```bash
python src/main.py
```

## 🎮 Kullanım Kılavuzu

### Ana Pencere
Uygulama başlatıldığında ana pencere açılır. Buradan diğer modüllere erişebilirsiniz:
- **Kontrol Modu:** Pin kontrolü ve patternler
- **Konfigürasyon Modu:** Pin ayarları
- **Serial Monitor:** Haberleşme izleme

### Kontrol Modu
1. **Pin Kontrolü:** Toggle butonları ile pinleri aç/kapat
2. **PWM Kontrolü:** Slider ile PWM değerini ayarla (0-255)
3. **Patternler:** 
   - Sıralı: Pinleri sırayla aç/kapat
   - Blink: Her pin için sırayla aç-kapat
   - Hepsi: Tüm pinleri aynı anda aç/kapat
4. **Okuma:** Dijital ve analog pinleri otomatik oku

### Konfigürasyon Modu
1. **Pin Aktif/Pasif:** Her pin için aktif/pasif toggle
2. **Pin Modu:** INPUT/OUTPUT seçimi
3. **Pin Türü:** Digital/PWM (dijital), Analog/Digital (analog)
4. **Toplu İşlemler:** Tüm pinleri aynı anda ayarla

### Serial Monitor
1. **Port Seçimi:** Arduino portunu seç
2. **Bağlantı:** Connect butonu ile bağlan
3. **Mesaj İzleme:** Gönderilen/alınan mesajları gör
4. **Mesaj Gönderme:** Manuel mesaj gönder

## 📁 Proje Yapısı

```
FNSS/
├── src/
│   ├── main.py                 # Ana uygulama başlatıcı
│   ├── gui/                    # Arayüz modülleri
│   │   ├── main_window.py      # Ana pencere
│   │   ├── control_menu.py     # Kontrol modu
│   │   ├── config_menu.py      # Konfigürasyon modu
│   │   └── serial_monitor.py   # Serial monitör
│   ├── core/                   # Çekirdek işlevler
│   │   ├── config.py           # Konfigürasyon yönetimi
│   │   ├── pin_manager.py      # Pin işlemleri
│   │   ├── serial_manager.py   # Serial haberleşme
│   │   ├── message_router.py   # Mesaj yönlendirme
│   │   └── scheduler.py        # Zamanlanmış görevler
│   ├── utils/                  # Yardımcı fonksiyonlar
│   │   └── logger.py           # Loglama
│   ├── assets/                 # Uygulama varlıkları
│   │   ├── logo.png            # Uygulama logosu
│   │   └── indir.ico           # Uygulama ikonu
│   └── arduino_codes/          # Arduino kodları
│       ├── test_real/          # Gerçek Arduino kodu
│       └── test_sim/           # Simülasyon kodu
├── config.json                 # Konfigürasyon dosyası
├── requirements.txt            # Python bağımlılıkları
├── LICENSE                     # Lisans dosyası
└── README.md                   # Bu dosya
```

## 🔧 Teknik Detaylar

### Mimari
- **Singleton Pattern:** SerialManager, PinManager, Scheduler
- **Observer Pattern:** Event-driven mesaj sistemi
- **Threading:** Arka plan işlemleri için thread kullanımı
- **Queue System:** Thread-safe mesaj kuyrukları

### Haberleşme Protokolü
- **Komut Formatı:** `PIN,STATE` (örn: `7,1`)
- **PWM Komutu:** `PWM PIN,VALUE` (örn: `PWM 9,128`)
- **Mod Komutu:** `MODE PIN,MODE` (örn: `MODE 7,1`)
- **Toplu Komut:** `ALL STATE` (örn: `ALL 1`)
- **Okuma Komutları:** `DIG`, `ANA`, `STAT`

### Güvenlik ve Hata Yönetimi
- **Bağlantı Kontrolü:** Otomatik bağlantı testi
- **Hata Yakalama:** Try-catch blokları ile güvenli işlemler
- **Timeout Mekanizması:** Yanıt gelmeyen komutlar için timeout
- **Graceful Shutdown:** Uygulama kapatılırken temiz kapanma

## 🐛 Bilinen Sorunlar ve Çözümler

### Arduino Bağlantı Sorunları
- **Port Bulunamıyor:** Arduino IDE'den port numarasını kontrol edin
- **Baudrate Uyumsuzluğu:** Arduino kodunda 9600 baudrate kullanın
- **Driver Sorunları:** Arduino driver'larını güncelleyin

### Python Paket Sorunları
- **CustomTkinter Hatası:** `pip install --upgrade customtkinter`
- **PySerial Hatası:** `pip install --upgrade pyserial`

## 🤝 Katkıda Bulunma

1. Bu repository'yi fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı ile lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

## 👨‍💻 Geliştirici

**Ahmet Rıfat Karademir**  
- 📧 E-posta: deepyellow18@gmail.com  
- 🐙 GitHub: [@ahmetrft](https://github.com/ahmetrft)
- 🔗 LinkedIn: [Ahmet Rıfat Karademir](https://www.linkedin.com/in/ahmetrifatkarademir)

## 🙏 Teşekkürler
- **FNSS** şirketine bu projeyi geliştirme fırsatı verdiği için

---

⭐ Bu projeyi beğendiyseniz yıldız vermeyi unutmayın!