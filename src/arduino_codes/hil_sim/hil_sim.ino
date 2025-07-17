/*
 * HIL Test Arduino Kodu - Proteus Simülasyonu
 * Bu kod Proteus üzerinde çalışacak ve GUI'ye veri gönderecek
 */

// Pin tanımlamaları
const int BUTTON_1 = 2;  // Motor Start
const int BUTTON_2 = 3;  // Motor Stop
const int BUTTON_3 = 4;  // AC Start
const int BUTTON_4 = 5;  // AC Stop
const int BUTTON_5 = 6;  // Emergency

const int POT_1 = A0;    // Speed Control
const int POT_2 = A1;    // Fuel Level

// Buton durumları (PLC mantığı: 1=basılı, 0=bırakılmış)
bool button1_state = false;
bool button2_state = false;
bool button3_state = false;
bool button4_state = false;
bool button5_state = false;

// Potansiyometre değerleri
int pot1_value = 0;
int pot2_value = 0;

// Zaman kontrolü
unsigned long last_pot_read = 0;
const unsigned long POT_READ_INTERVAL = 100; // 100ms

void setup() {
  // Serial başlat
  Serial.begin(9600);
  
  // Pin modlarını ayarla
  pinMode(BUTTON_1, INPUT_PULLUP);
  pinMode(BUTTON_2, INPUT_PULLUP);
  pinMode(BUTTON_3, INPUT_PULLUP);
  pinMode(BUTTON_4, INPUT_PULLUP);
  pinMode(BUTTON_5, INPUT_PULLUP);
  
  // Analog pinler otomatik olarak INPUT modunda
  
  // Başlangıç mesajı
  Serial.println("HIL_SIM_READY");
  
  delay(1000);
}

void loop() {
  // Butonları oku
  readButtons();
  
  // Potansiyometreleri belirli aralıklarla oku
  if (millis() - last_pot_read >= POT_READ_INTERVAL) {
    readPotentiometers();
    last_pot_read = millis();
  }
  
  delay(10); // Kısa bekleme
}

void readButtons() {
  // Buton 1 - Motor Start (PLC mantığı: 1=basılı, 0=bırakılmış)
  bool current_button1 = digitalRead(BUTTON_1); // Tersleme YOK!
  if (current_button1 != button1_state) {
    button1_state = current_button1;
    Serial.print("BUTTON:1:");
    Serial.println(button1_state ? "1" : "0");
  }
  
  // Buton 2 - Motor Stop
  bool current_button2 = digitalRead(BUTTON_2);
  if (current_button2 != button2_state) {
    button2_state = current_button2;
    Serial.print("BUTTON:2:");
    Serial.println(button2_state ? "1" : "0");
  }
  
  // Buton 3 - AC Start
  bool current_button3 = digitalRead(BUTTON_3);
  if (current_button3 != button3_state) {
    button3_state = current_button3;
    Serial.print("BUTTON:3:");
    Serial.println(button3_state ? "1" : "0");
  }
  
  // Buton 4 - AC Stop
  bool current_button4 = digitalRead(BUTTON_4);
  if (current_button4 != button4_state) {
    button4_state = current_button4;
    Serial.print("BUTTON:4:");
    Serial.println(button4_state ? "1" : "0");
  }
  
  // Buton 5 - Emergency
  bool current_button5 = digitalRead(BUTTON_5);
  if (current_button5 != button5_state) {
    button5_state = current_button5;
    Serial.print("BUTTON:5:");
    Serial.println(button5_state ? "1" : "0");
  }
}

void readPotentiometers() {
  // Potansiyometre 1 - Hız (0-150 km/h)
  int new_pot1 = analogRead(POT_1);
  int mapped_pot1 = map(new_pot1, 0, 1023, 0, 150);
  
  if (abs(mapped_pot1 - pot1_value) >= 1) { // 1 km/h değişim toleransı
    pot1_value = mapped_pot1;
    Serial.print("POT:1:");
    Serial.println(pot1_value);
  }
  
  // Potansiyometre 2 - Yakıt (0-100%)
  int new_pot2 = analogRead(POT_2);
  int mapped_pot2 = map(new_pot2, 0, 1023, 0, 100);
  
  if (abs(mapped_pot2 - pot2_value) >= 1) { // 1% değişim toleransı
    pot2_value = mapped_pot2;
    Serial.print("POT:2:");
    Serial.println(pot2_value);
  }
} 