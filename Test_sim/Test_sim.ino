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
    cmd.trim(); // sondaki \r veya boşlukları temizle
    
    if (cmd.equals("TEST")) { 
      Serial.println("1"); 
    }
    // Pin modu değiştirme: "MODE <pin>,<mode>" (0=INPUT, 1=OUTPUT, 2=PAS)
    else if (cmd.startsWith("MODE ")) {
      int commaIdx = cmd.indexOf(',');
      if (commaIdx <= 5) return; // eksik komutu yoksay
      int pin = cmd.substring(5, commaIdx).toInt();
      String val = cmd.substring(commaIdx + 1);
      val.trim();
      val.toUpperCase();
      int mode;
      if (val == "2" || val == "PAS" || val == "PASS" || val == "PASIF") mode = 2;
      else mode = (val == "1" || val == "OUT" || val == "OUTPUT") ? 1 : 0;
      
      if (pin >= 2 && pin <= 19) {
        if (mode == 2) {
          pinMode(pin, INPUT);
          pinModes[pin] = 2;
          String msg = "PIN " + pinLabel(pin) + ":PAS";
          Serial.println(msg);
        } else {
          pinMode(pin, mode == 1 ? OUTPUT : INPUT);
          pinModes[pin] = mode;
          String modeStr = mode == 1 ? "OUT" : "IN";
          String msg = "PIN " + pinLabel(pin) + ":" + modeStr;
          Serial.println(msg);
        }
      }
    }
    // Dijital yazma: "<pin>,<durum>\n" (sadece OUTPUT modunda)
    else if (cmd.indexOf(',') > 0 && isDigit(cmd.charAt(0))) {
      int commaIdx = cmd.indexOf(',');
      int pin = cmd.substring(0, commaIdx).toInt();
      int state = cmd.substring(commaIdx + 1).toInt();
      if (pin >= 2 && pin <= 19 && pinModes[pin]) {
        digitalWrite(pin, state == 1 ? HIGH : LOW);
        pinStates[pin] = state;
        String s = "PIN " + pinLabel(pin) + " : " + (state == 1 ? "ON" : "OFF");
        Serial.println(s);
      }
    }
    // PWM yazma: "PWM <pin>,<value>" (0-255)
    else if (cmd.startsWith("PWM ")) {
      int commaIdx = cmd.indexOf(',');
      int pin = cmd.substring(4, commaIdx).toInt();
      int value = cmd.substring(commaIdx + 1).toInt();
      // Sadece PWM destekli pinler: 3, 5, 6, 9, 10, 11
      if ((pin == 3 || pin == 5 || pin == 6 || pin == 9 || pin == 10 || pin == 11) && pinModes[pin]) {
        analogWrite(pin, value);
        pinStates[pin] = value;
        String s = "PIN " + pinLabel(pin) + " : " + String(value);
        Serial.println(s);
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
          pinStates[p] = state == 1 ? 255 : 0;
        } else {
          digitalWrite(p, state == 1 ? HIGH : LOW);
          pinStates[p] = state == 1 ? 1 : 0;
        }
      }
      String msg = String("PIN ALL: ") + (state == 1 ? "ON" : "OFF");
      Serial.println(msg);
    }
    // 'STAT' komutu: tüm pin durumlarını ve modlarını gönder
    else if (cmd.equals("STAT")) {
      for (int p = 2; p <= 19; p++) {
        Serial.print(pinLabel(p));
        Serial.print(":");
        Serial.print(pinStates[p]);
        Serial.print(":");
        Serial.print(pinModes[p]); // 0/1/2
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
          Serial.print(p);
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
