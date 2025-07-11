// Pin durum/mode tabloları
int pinModes[20] = {0};   // 0=INPUT, 1=OUTPUT, 2=PAS (inactive)
int pinStates[20] = {0};  // Dijital veya PWM değeri
int analogValues[6] = {0};

// Yardımcı: 14-19 → A0-A5 etiketi
String pinLabel(int pin) {
  if (pin >= 14 && pin <= 19) return "A" + String(pin - 14);
  return String(pin);
}

void setup() {
  Serial.begin(9600);
  // Varsayılan: tüm pinler OUTPUT & LOW
  for (int pin = 2; pin <= 19; pin++) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
    pinModes[pin] = 1;
    pinStates[pin] = 0;
  }
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    // Pin modu değiştirme: "MODE <pin>,<mode>" (0=INPUT, 1=OUTPUT)
    if (cmd.startsWith("MODE ")) {
      int commaIdx = cmd.indexOf(',');
      if (commaIdx > 5) {
        int pin = cmd.substring(5, commaIdx).toInt();
        int mode = cmd.substring(commaIdx + 1).toInt();
        if (pin >= 2 && pin <= 19) {
          if (mode == 2) {
            pinMode(pin, INPUT);
            pinModes[pin] = 2;
            Serial.print("PIN "); Serial.print(pinLabel(pin)); Serial.println(":PAS");
          } else {
            pinMode(pin, mode == 1 ? OUTPUT : INPUT);
            pinModes[pin] = mode;
            Serial.print("PIN "); Serial.print(pinLabel(pin)); Serial.print(":");
            Serial.println(mode == 1 ? "OUT" : "IN");
          }
        }
      }
    }
    // PWM yazma: "PWM <pin>,<value>" (0-255)
    else if (cmd.startsWith("PWM ")) {
      int commaIdx = cmd.indexOf(',');
      if (commaIdx > 0) {
        int pin = cmd.substring(4, commaIdx).toInt();
        int value = cmd.substring(commaIdx + 1).toInt();
        // Sadece PWM destekli pinler: 3, 5, 6, 9, 10, 11
        if ((pin == 3 || pin == 5 || pin == 6 || pin == 9 || pin == 10 || pin == 11) && pinModes[pin] == 1) { // Changed pinModes[pin] to pinModes[pin] == 1
          analogWrite(pin, value);
          pinStates[pin] = value;
          Serial.print("PIN ");
          Serial.print(pinLabel(pin));
          if(pin<10) Serial.print("  : "); else Serial.print(" : ");
          Serial.println(value);
        }
        // Analog pinler için (A0-A5 = 14-19) dijital çıkış (HIGH/LOW) olarak kullanılır
        else if (pin >= 14 && pin <= 19 && pinModes[pin] == 1) { // Changed pinModes[pin] to pinModes[pin] == 1
          digitalWrite(pin, value > 0 ? HIGH : LOW);
          pinStates[pin] = (value > 0 ? 1 : 0);
          Serial.print("PIN ");
          Serial.print(pinLabel(pin));
          Serial.print(value > 0 ? " ON" : " OFF");
          Serial.println();
        }
      }
    }
    // Dijital yazma: "<pin>,<durum>\n" (sadece OUTPUT modunda)
    else if (cmd.indexOf(',') > 0 && isDigit(cmd.charAt(0))) {
      int commaIdx = cmd.indexOf(',');
      int pin = cmd.substring(0, commaIdx).toInt();
      int state = cmd.substring(commaIdx + 1).toInt();
      if (pin >= 2 && pin <= 19 && pinModes[pin] == 1) { // Changed pinModes[pin] to pinModes[pin] == 1
        digitalWrite(pin, state == 1 ? HIGH : LOW);
        pinStates[pin] = state;
        Serial.print("PIN ");
        Serial.print(pinLabel(pin));
        if(pin<10) Serial.print("  : "); else Serial.print(" : ");
        Serial.println(state == 1 ? "ON" : "OFF");
      }
    }
    // Tüm pinleri aç/kapat: "ALL <state>" (state 0 veya 1)
    else if (cmd.startsWith("ALL ")) {
      int state = cmd.substring(4).toInt();
      for (int p = 2; p <= 19; p++) {
        if (!pinModes[p]) continue; // sadece OUTPUT pinler
        // PWM destekli pinler
        if (p == 3 || p == 5 || p == 6 || p == 9 || p == 10 || p == 11) {
          analogWrite(p, state == 1 ? 255 : 0);
        } else {
          digitalWrite(p, state == 1 ? HIGH : LOW);
        }
        pinStates[p] = (state == 1 ? 1 : 0);
      }
      String s = String("PIN ALL: ") + (state == 1 ? "ON" : "OFF");
      Serial.println(s);
    }
    // 'STAT' komutu: tüm pin durumlarını ve modlarını gönder
    else if (cmd.equals("STAT")) {
      for (int p = 2; p <= 19; p++) {
        Serial.print(pinLabel(p));
        Serial.print(":");
        Serial.print(pinStates[p]);
        Serial.print(":");
        Serial.print(pinModes[p]);
        if (p < 19) Serial.print(",");
      }
      Serial.println();
    }
    // 'DIG' komutu: dijital pin okumaları (INPUT modundaki pinler)
    else if (cmd.equals("DIG")) {
      for (int p = 2; p <= 19; p++) {
        if (!pinModes[p]) {
          int val = digitalRead(p);
          Serial.print("D");
          Serial.print(pinLabel(p));
          Serial.print(":");
          Serial.print(val);
          Serial.print(",");
        }
      }
      Serial.println();
    }
    // 'ANA' komutu: analog pin okumaları
    else if (cmd.equals("ANA")) {
      for (int a = 0; a < 6; a++) {
        int val = analogRead(a);
        analogValues[a] = val;
        Serial.print("A");
        Serial.print(a);
        Serial.print(":");
        Serial.print(val);
        if (a < 5) Serial.print(",");
      }
      Serial.println();
    }
  }
}
