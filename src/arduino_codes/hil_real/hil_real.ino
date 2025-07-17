/*
 * HIL Real Arduino Kodu - Gerçek Arduino
 * Bu kod gerçek Arduino'da çalışacak ve GUI'den gelen komutları işleyecek
 */

// LED Pin tanımlamaları
const int LED_GREEN = 2;    // Motor durumu - Yeşil LED
const int LED_BLUE = 3;     // Klima durumu - Mavi LED
const int LED_RED = 4;      // Acil durum - Kırmızı LED
const int LED_SPEED = 5;    // Hız uyarısı - Sarı LED
const int LED_FUEL = 6;     // Yakıt uyarısı - Turuncu LED

// LED durumları
bool led_green_state = false;
bool led_blue_state = false;
bool led_red_state = false;
bool led_speed_state = false;
bool led_fuel_state = false;

// Serial mesaj işleme
String inputString = "";
bool stringComplete = false;

void setup() {
  // Serial başlat
  Serial.begin(9600);
  
  // LED pinlerini çıkış olarak ayarla
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_SPEED, OUTPUT);
  pinMode(LED_FUEL, OUTPUT);
  
  // LED'leri başlangıçta kapat
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_BLUE, LOW);
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_SPEED, LOW);
  digitalWrite(LED_FUEL, LOW);
  
  // Başlangıç mesajı
  Serial.println("HIL_REAL_READY");
  
  delay(1000);
}

void loop() {
  // Serial mesajları işle
  if (stringComplete) {
    processSerialMessage(inputString);
    inputString = "";
    stringComplete = false;
  }
  
  delay(10);
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void processSerialMessage(String message) {
  message.trim();
  
  // Test mesajı kontrolü
  if (message == "TEST") {
    Serial.println("1");
    return;
  }
  
  // Pin komutları: "pin,state" formatında
  if (message.indexOf(',') != -1) {
    int commaIndex = message.indexOf(',');
    int pin = message.substring(0, commaIndex).toInt();
    int state = message.substring(commaIndex + 1).toInt();
    
    setPinState(pin, state);
    return;
  }
  
  // PWM komutları: "PWM pin,value" formatında
  if (message.startsWith("PWM ")) {
    String pwmPart = message.substring(4);
    int commaIndex = pwmPart.indexOf(',');
    if (commaIndex != -1) {
      int pin = pwmPart.substring(0, commaIndex).toInt();
      int value = pwmPart.substring(commaIndex + 1).toInt();
      
      setPWMValue(pin, value);
    }
    return;
  }
  
  // Pin modu komutları: "MODE pin,mode" formatında
  if (message.startsWith("MODE ")) {
    String modePart = message.substring(5);
    int commaIndex = modePart.indexOf(',');
    if (commaIndex != -1) {
      int pin = modePart.substring(0, commaIndex).toInt();
      int mode = modePart.substring(commaIndex + 1).toInt();
      
      setPinMode(pin, mode);
    }
    return;
  }
  
  // Tüm pinleri aynı anda kontrol: "ALL state" formatında
  if (message.startsWith("ALL ")) {
    int state = message.substring(4).toInt();
    setAllPins(state);
    return;
  }
}

void setPinState(int pin, int state) {
  bool pinState = (state == 1);
  
  switch (pin) {
    case LED_GREEN:
      digitalWrite(LED_GREEN, pinState ? HIGH : LOW);
      led_green_state = pinState;
      Serial.print("LED_GREEN:");
      Serial.println(pinState ? "ON" : "OFF");
      break;
      
    case LED_BLUE:
      digitalWrite(LED_BLUE, pinState ? HIGH : LOW);
      led_blue_state = pinState;
      Serial.print("LED_BLUE:");
      Serial.println(pinState ? "ON" : "OFF");
      break;
      
    case LED_RED:
      digitalWrite(LED_RED, pinState ? HIGH : LOW);
      led_red_state = pinState;
      Serial.print("LED_RED:");
      Serial.println(pinState ? "ON" : "OFF");
      break;
      
    case LED_SPEED:
      digitalWrite(LED_SPEED, pinState ? HIGH : LOW);
      led_speed_state = pinState;
      Serial.print("LED_SPEED:");
      Serial.println(pinState ? "ON" : "OFF");
      break;
      
    case LED_FUEL:
      digitalWrite(LED_FUEL, pinState ? HIGH : LOW);
      led_fuel_state = pinState;
      Serial.print("LED_FUEL:");
      Serial.println(pinState ? "ON" : "OFF");
      break;
      
    default:
      Serial.print("UNKNOWN_PIN:");
      Serial.println(pin);
      break;
  }
}

void setPWMValue(int pin, int value) {
  // PWM değerini 0-255 arasında sınırla
  value = constrain(value, 0, 255);
  
  switch (pin) {
    case LED_GREEN:
    case LED_BLUE:
    case LED_RED:
    case LED_SPEED:
    case LED_FUEL:
      analogWrite(pin, value);
      Serial.print("PWM_SET:");
      Serial.print(pin);
      Serial.print(":");
      Serial.println(value);
      break;
      
    default:
      Serial.print("PWM_UNKNOWN_PIN:");
      Serial.println(pin);
      break;
  }
}

void setPinMode(int pin, int mode) {
  switch (pin) {
    case LED_GREEN:
    case LED_BLUE:
    case LED_RED:
    case LED_SPEED:
    case LED_FUEL:
      pinMode(pin, mode);
      Serial.print("MODE_SET:");
      Serial.print(pin);
      Serial.print(":");
      Serial.println(mode);
      break;
      
    default:
      Serial.print("MODE_UNKNOWN_PIN:");
      Serial.println(pin);
      break;
  }
}

void setAllPins(int state) {
  bool pinState = (state == 1);
  
  digitalWrite(LED_GREEN, pinState ? HIGH : LOW);
  digitalWrite(LED_BLUE, pinState ? HIGH : LOW);
  digitalWrite(LED_RED, pinState ? HIGH : LOW);
  digitalWrite(LED_SPEED, pinState ? HIGH : LOW);
  digitalWrite(LED_FUEL, pinState ? HIGH : LOW);
  
  led_green_state = pinState;
  led_blue_state = pinState;
  led_red_state = pinState;
  led_speed_state = pinState;
  led_fuel_state = pinState;
  
  Serial.print("ALL_LEDS:");
  Serial.println(pinState ? "ON" : "OFF");
}

// Durum sorgulama fonksiyonu
void getStatus() {
  Serial.println("STATUS:");
  Serial.print("GREEN:");
  Serial.println(led_green_state ? "ON" : "OFF");
  Serial.print("BLUE:");
  Serial.println(led_blue_state ? "ON" : "OFF");
  Serial.print("RED:");
  Serial.println(led_red_state ? "ON" : "OFF");
  Serial.print("SPEED:");
  Serial.println(led_speed_state ? "ON" : "OFF");
  Serial.print("FUEL:");
  Serial.println(led_fuel_state ? "ON" : "OFF");
} 