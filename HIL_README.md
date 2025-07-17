# FNSS HIL (Hardware in the Loop) Test Uygulaması

## Proje Amacı
Bu proje, fiziksel Arduino kartı ve Proteus üzerinden simüle edilmiş bir Arduino arasında gerçek zamanlı veri iletişimi sağlayan, kullanıcıya etkileşimli ve görsel bir arayüz sunan bir Hardware in the Loop (HIL) test sistemidir. Amaç, gerçek ve simüle edilen donanım arasında güvenli ve izlenebilir bir test ortamı oluşturmaktır.

## Genel Özellikler
- **Gerçek ve Simüle Arduino ile Eşzamanlı Haberleşme**
- **Modern GUI** (CustomTkinter)
- **Gerçek Zamanlı Durum Görselleştirme**: Motor, Klima, Acil Durum, Hız, Yakıt, LED durumları
- **Acil Durum Latch**: Acil durum bir kez aktif olursa, program yeniden başlatılana kadar aktif kalır.
- **Kapsamlı Loglama**: Tüm olaylar ve mesajlar zaman damgalı olarak kaydedilir.

## Sistem Gereksinimleri

### Yazılım Gereksinimleri
- Python 3.7+
- CustomTkinter
- PySerial
- Proteus (Arduino simülasyonu için)

### Donanım Gereksinimleri
- Gerçek Arduino kartı (Uno, Nano, vb.)
- USB kablosu
- 5 adet LED (Yeşil, Mavi, Kırmızı, Sarı, Turuncu)
- 5 adet 220Ω direnç
- Breadboard ve jumper kablolar

## Kurulum
1. Gerekli Python kütüphanelerini yükleyin:
   ```bash
   pip install customtkinter pyserial
   ```
2. Arduino kodlarını yükleyin:
   - Proteus için: `src/arduino_codes/hil_sim/hil_sim.ino`
   - Gerçek Arduino için: `src/arduino_codes/hil_real/hil_real.ino`
3. Donanım bağlantılarını yapın:
   - Pin 2: Yeşil LED (Motor)
   - Pin 3: Mavi LED (Klima)
   - Pin 4: Kırmızı LED (Acil Durum)
   - Pin 5: Sarı LED (Hız Uyarı)
   - Pin 6: Turuncu LED (Yakıt Uyarı)

## Kullanım
Uygulamayı başlatmak için:
```bash
python run_hil.py
```

### Arayüz Bileşenleri
- **Bağlantı Durumu**: Proteus ve Gerçek Arduino bağlantı durumu
- **Ayarlar**: Hız limiti ve kritik yakıt seviyesi ayarı
- **Araç Durumu**: Motor, Klima, Acil Durum, Hız, Yakıt ve LED durumları
- **Mesaj Monitörü**: Tüm gelen/giden mesajlar ve olaylar

### PLC Buton Mantığı
- Tüm butonlar (Motor Aç/Kapa, Klima Aç/Kapa, Acil Durum) PLC mantığına uygun olarak çalışır:
  - **Buton basılıysa:** 1
  - **Buton bırakıldıysa:** 0
- Motor veya Klima LED'inin yanma koşulu:
  - Motor Aç butonu 1 **ve** Motor Kapa butonu 0 ise Motor LED yanar.
  - Klima Aç butonu 1 **ve** Klima Kapa butonu 0 ise Klima LED yanar.
- Acil Durum butonuna bir kez basılırsa (1 sinyali gelirse) acil durum aktif olur ve program yeniden başlatılana kadar pasif olmaz.

#### 2. Kontrol Ayarları
- **Hız Limiti**: 30-150 km/h arası ayarlanabilir (varsayılan: 80 km/h)
- **Kritik Yakıt Seviyesi**: %5-50 arası ayarlanabilir (varsayılan: %20)
- **Manuel Bağlantı Butonları**: Her iki Arduino için ayrı bağlantı butonları

### Loglama
- Tüm mesajlar ve olaylar `logs/` klasöründe zaman damgalı olarak kaydedilir.
- Örnek log satırı:
  ```
  [14:30:15] OLAY: Motor Başlatıldı
  [14:30:16] SIM: BUTTON:1:1
  [14:30:16] REAL: LED_GREEN:ON
  ```

## Test Senaryosu
- **Butonlar**: Motor Aç/Kapa, Klima Aç/Kapa, Acil Durum butonları ile LED'lerin ve GUI'nin doğru tepki verdiği gözlemlenir.
- **Potansiyometreler**: Hız ve yakıt seviyesi değiştirildiğinde GUI ve LED'ler doğru tepki verir.
- **Acil Durum**: Bir kez aktif olunca program yeniden başlatılana kadar pasif olmaz.
- **Seri Monitör**: Tüm mesajlar ve olaylar anlık olarak izlenebilir.

Uygulama çalışırken tüm mesajlar ve olaylar `logs/` klasöründe kaydedilir:
- Dosya adı: `hil_test_YYYYMMDD_HHMMSS.log`
- Format: `[HH:MM:SS] KAYNAK: MESAJ`
- Örnek: `[14:30:15] OLAY: Motor Başlatıldı`

## Öncelik Kuralları

- **Buton 2** (Motor Durdur) ve **Buton 4** (Klima Kapat), **Buton 1** (Motor Başlat) ve **Buton 3** (Klima Aç) butonlarına göre önceliklidir
- Motor açıkken Buton 2'ye basılırsa motor kapanır
- Klima açıkken Buton 4'e basılırsa klima kapanır

## Sorun Giderme

### Bağlantı Sorunları
1. **Proteus Arduino bağlanmıyor:**
   - COM6 portunun doğru olduğundan emin olun
   - Proteus simülasyonunun çalıştığından emin olun
   - Arduino kodunun yüklendiğinden emin olun

2. **Gerçek Arduino bulunamıyor:**
   - Arduino'nun USB ile bağlı olduğundan emin olun
   - Arduino kodunun yüklendiğinden emin olun
   - Başka bir uygulamanın portu kullanmadığından emin olun

### LED Sorunları
1. **LED'ler yanmıyor:**
   - Pin bağlantılarını kontrol edin
   - Direnç değerlerini kontrol edin
   - Arduino kodunun doğru yüklendiğinden emin olun

### Mesaj Sorunları
1. **Mesajlar görünmüyor:**
   - Serial monitörün açık olduğundan emin olun
   - Baud rate'in 9600 olduğundan emin olun
   - Log dosyalarını kontrol edin

## Teknik Detaylar

### Pin Haritası
- **Proteus Arduino**: Pin 2-6 (butonlar), A0-A1 (potansiyometreler)
- **Gerçek Arduino**: Pin 2-6 (LED'ler)

### Baud Rate
- Her iki Arduino için 9600 baud

### Mesaj Protokolü
- Satır sonu ile ayrılmış mesajlar
- UTF-8 encoding
- Gerçek zamanlı işleme

## Geliştirme

### Yeni Özellik Ekleme
1. `VehicleState` sınıfına yeni alan ekleyin
2. Mesaj işleme fonksiyonlarını güncelleyin
3. GUI bileşenlerini ekleyin
4. Arduino kodlarını güncelleyin

### Hata Ayıklama
- Log dosyalarını kontrol edin
- Serial monitörü kullanın
- Debug mesajlarını etkinleştirin

## Lisans
Bu proje, **FNSS Savunma Sistemleri A.Ş.** bünyesinde staj yaptığım süre boyunca tarafımdan (@ahmetrft) geliştirilmiştir.