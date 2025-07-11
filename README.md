# FNSS - Arduino Pin Kontrol Sistemi

FNSS (Flexible Network Sensor System), Arduino pinlerini kontrol etmek ve okumak için geliştirilmiş modern bir Python uygulamasıdır.

## 🚀 Özellikler

### 🔍 Otomatik Port Tarama
- **Akıllı Port Algılama**: Bilgisayardaki tüm COM portlarını otomatik tarar
- **Arduino Test Mesajı**: "TEST" mesajı göndererek Arduino varlığını doğrular
- **Otomatik Bağlantı**: İlk çalışan Arduino portuna otomatik bağlanır
- **Gerçek Zamanlı Durum**: Bağlantı durumunu canlı olarak gösterir

### 📝 Yazma Modu
- **Dijital Pin Kontrolü**: Pin 2-13 arası dijital çıkış kontrolü
- **PWM Kontrolü**: Pin 3, 5, 6, 9, 10, 11 için 0-255 arası PWM kontrolü
- **Analog Pin Kontrolü**: A0-A5 pinleri için dijital çıkış kontrolü
- **Gelişmiş Patternler**: 
  - Sıralı yak → sıralı söndür
  - Sıralı yak-söndür döngüsü
  - Hepsini yak → hepsini söndür
- **Global Mod Kontrolü**: Yazma/Okuma modu arası geçiş
- **Gerçek Zamanlı Görsel Geri Bildirim**: Pin durumlarını renkli göstergelerle takip

### 📖 Okuma Modu
- **Dijital Pin Okuma**: Pin 2-13'ten dijital değerleri okuma (0/1)
- **Analog Pin Okuma**: A0-A5 pinlerinden analog değerleri okuma (0-1023)
- **Görsel Durum Göstergeleri**: LED benzeri renkli noktalar
- **Otomatik Okuma Döngüleri**: Sürekli veri akışı

### ⚙️ Konfigürasyon Modu
- **Seri Port Ayarları**: Port, baudrate, timeout ayarları
- **Uygulama Ayarları**: Tema, otomatik bağlantı
- **Bağlantı Testi**: Seri port bağlantısını test etme
- **Ayarları Kaydetme**: JSON formatında konfigürasyon saklama

## 🛠️ Kurulum

### Gereksinimler
- Python 3.7+
- Arduino Uno/Nano (veya uyumlu)
- USB kablosu

### Python Paketleri
```bash
pip install customtkinter
pip install pyserial
```

### Arduino Kodu
Arduino'ya aşağıdaki kodu yükleyin:

```cpp
// Arduino pin kontrol kodu
// Pin 2-13: Dijital I/O
// Pin 3,5,6,9,10,11: PWM destekli
// A0-A5: Analog okuma

const int DIGITAL_PINS[] = {2,3,4,5,6,7,8,9,10,11,12,13};
const int PWM_PINS[] = {3,5,6,9,10,11};
const int ANALOG_PINS[] = {A0,A1,A2,A3,A4,A5};

void setup() {
  Serial.begin(9600);
  
  // Tüm dijital pinleri OUTPUT olarak ayarla
  for(int i = 0; i < 12; i++) {
    pinMode(DIGITAL_PINS[i], OUTPUT);
  }
}

void loop() {
  if(Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Dijital pin kontrolü: "pin,state"
    if(command.indexOf(',') > 0 && !command.startsWith("PWM") && !command.startsWith("MODE")) {
      int commaIndex = command.indexOf(',');
      int pin = command.substring(0, commaIndex).toInt();
      int state = command.substring(commaIndex + 1).toInt();
      
      if(pin >= 2 && pin <= 13) {
        digitalWrite(pin, state);
        Serial.print("LED ");
        Serial.print(pin);
        Serial.println(state ? " ON" : " OFF");
      }
    }
    
    // PWM kontrolü: "PWM pin,value"
    else if(command.startsWith("PWM ")) {
      command = command.substring(4);
      int commaIndex = command.indexOf(',');
      int pin = command.substring(0, commaIndex).toInt();
      int value = command.substring(commaIndex + 1).toInt();
      
      if(pin >= 2 && pin <= 13) {
        analogWrite(pin, value);
        Serial.print("PWM ");
        Serial.print(pin);
        Serial.print(": ");
        Serial.println(value);
      }
    }
    
    // Pin modu değiştirme: "MODE pin,mode"
    else if(command.startsWith("MODE ")) {
      command = command.substring(5);
      int commaIndex = command.indexOf(',');
      int pin = command.substring(0, commaIndex).toInt();
      int mode = command.substring(commaIndex + 1).toInt();
      
      if(pin >= 2 && pin <= 13) {
        pinMode(pin, mode ? OUTPUT : INPUT);
      }
    }
    
    // Durum sorgusu: "STAT"
    else if(command == "STAT") {
      for(int i = 0; i < 12; i++) {
        int pin = DIGITAL_PINS[i];
        int state = digitalRead(pin);
        int mode = (pin >= 2 && pin <= 13) ? 1 : 0; // Basitleştirilmiş
        Serial.print(pin);
        Serial.print(":");
        Serial.print(state);
        Serial.print(":");
        Serial.print(mode);
        if(i < 11) Serial.print(",");
      }
      Serial.println();
    }
    
    // Dijital okuma: "DIG"
    else if(command == "DIG") {
      for(int i = 0; i < 12; i++) {
        int pin = DIGITAL_PINS[i];
        int state = digitalRead(pin);
        Serial.print("D");
        Serial.print(pin);
        Serial.print(":");
        Serial.print(state);
        if(i < 11) Serial.print(",");
      }
      Serial.println();
    }
    
    // Analog okuma: "ANA"
    else if(command == "ANA") {
      for(int i = 0; i < 6; i++) {
        int value = analogRead(ANALOG_PINS[i]);
        Serial.print("A");
        Serial.print(i);
        Serial.print(":");
        Serial.print(value);
        if(i < 5) Serial.print(",");
      }
      Serial.println();
    }
  }
}
```

## 🎯 Kullanım

### Uygulamayı Başlatma
```bash
python src/main.py
```

### Ana Menü
1. **Okuma Modu**: Pin durumlarını okumak için
2. **Yazma Modu**: Pinleri kontrol etmek için  
3. **Konfigürasyon Modu**: Ayarları değiştirmek için

### Yazma Modu Kullanımı
- **Global Mod Butonu**: Yazma/Okuma modu arası geçiş
- **Dijital Switch'ler**: Pin 2-13 için açma/kapama
- **PWM Slider'lar**: Pin 3,5,6,9,10,11 için 0-255 arası kontrol
- **Pattern Butonları**: Otomatik pattern çalıştırma
- **Hepsini Yak/Söndür**: Tüm pinleri aynı anda kontrol

### Okuma Modu Kullanımı
1. **Tüm Pinleri INPUT Yap**: Dijital pinleri okuma moduna alır
2. **Dijital Okuma Başlat**: Pin 2-13'ten dijital değerleri okur
3. **Analog Okuma Başlat**: A0-A5 pinlerinden analog değerleri okur
- **Yeşil nokta**: Pin HIGH (1)
- **Kırmızı nokta**: Pin LOW (0)

### Konfigürasyon Modu
- **Seri Port**: Arduino'nun bağlı olduğu port
- **Baudrate**: İletişim hızı (genellikle 9600)
- **Tema**: Uygulama görünümü
- **Bağlantı Testi**: Seri port bağlantısını test etme

## 📁 Proje Yapısı

```
FNSS/
├── src/
│   ├── main.py              # Ana uygulama
│   ├── gui/
│   │   ├── main_window.py   # Ana pencere
│   │   ├── write_menu.py    # Yazma modu
│   │   ├── read_menu.py     # Okuma modu
│   │   └── config_menu.py   # Konfigürasyon modu
│   ├── core/                # Çekirdek modüller
│   └── utils/               # Yardımcı fonksiyonlar
├── tests/                   # Test dosyaları
├── Blink/                   # Arduino örnek kodları
└── README.md               # Bu dosya
```

## 🔧 Sorun Giderme

### Seri Port Bağlantı Sorunları
1. Arduino'nun doğru porta bağlı olduğundan emin olun
2. Konfigürasyon modunda bağlantı testini çalıştırın
3. Arduino IDE'de port seçimini kontrol edin
4. USB kablosunu değiştirmeyi deneyin

### PWM Pin Sorunları
- Sadece pin 3, 5, 6, 9, 10, 11 PWM destekler
- Diğer pinler sadece dijital çıkış olarak çalışır

### Pattern Çalışmıyor
- Global modun "YAZMA MODU"nda olduğundan emin olun
- Arduino kodunun doğru yüklendiğini kontrol edin

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Ayrıntılar için LICENSE dosyasına bakınız.

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit yapın (`git commit -m 'Add some AmazingFeature'`)
4. Push yapın (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📞 İletişim

Sorularınız için issue açabilir veya pull request gönderebilirsiniz. 