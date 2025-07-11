#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// I2C LCD adresi genelde 0x27 veya 0x3F olur
LiquidCrystal_I2C lcd(0x27, 16, 2);

int pinModes[20]={0}; // 0=INPUT,1=OUTPUT,2=PAS (inactive)
int pinStates[20]={0};
int analogValues[6]={0};

// Yardımcı: Pin numarasını okunabilir etikete dönüştür
String pinLabel(int pin){
  if(pin>=14 && pin<=19) return "A"+String(pin-14);
  return String(pin);
}

String prevLCDLine="";
void lcdMsg(const String &m){
  String newLine = m.length()>16?m.substring(0,16):m;

  // Üst satırı temizle ve önceki mesajı yaz
  lcd.setCursor(0,0);
  lcd.print("                ");
  lcd.setCursor(0,0);
  lcd.print(prevLCDLine.length()>16?prevLCDLine.substring(0,16):prevLCDLine);

  // Alt satırı temizle ve yeni mesajı yaz
  lcd.setCursor(0,1);
  lcd.print("                ");
  lcd.setCursor(0,1);
  lcd.print(newLine);

  prevLCDLine = newLine;
  // gecikme kaldırıldı; anlık güncelleme
} 

void setup(){
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("FNSS Arduino");
  lcd.setCursor(0,1);
  lcd.print("Control Project");
  for(int p=2;p<=19;p++){pinMode(p,OUTPUT);digitalWrite(p,LOW);pinModes[p]=true;}
}

void loop(){
 if(Serial.available()){
  String cmd=Serial.readStringUntil('\n');
  cmd.trim(); // sondaki \r veya boşlukları temizle
  if(cmd.equals("TEST")) { Serial.println("1"); }
  else if(cmd.startsWith("MODE ")){
    int c=cmd.indexOf(',');
    if(c<=5) return; // eksik komutu yoksay
    int pin=cmd.substring(5,c).toInt();
    String val=cmd.substring(c+1);
    val.trim();
    val.toUpperCase();
    int m;
    if(val=="2" || val=="PAS" || val=="PASS" || val=="PASIF") m=2;
    else m = (val=="1" || val=="OUT" || val=="OUTPUT") ? 1 : 0;
    if(pin>=2 && pin<=19){
      if(m==2){
        pinMode(pin, INPUT);
        pinModes[pin]=2;
        String msg = "PIN " + pinLabel(pin) + ":PAS";
        Serial.println(msg);
        lcdMsg(msg); // LCD'ye de yazdır
      }else{
        pinMode(pin, m==1?OUTPUT:INPUT);
        pinModes[pin]=m; // 0/1
        String modeStr = m==1?"OUT":"IN";
        String msg = "PIN " + pinLabel(pin) + ":" + modeStr;
        Serial.println(msg);
        lcdMsg(msg); // LCD'ye de yazdır
      }
    }
  }
  else if(cmd.indexOf(',')>0 && isDigit(cmd.charAt(0))){int c=cmd.indexOf(',');int pin=cmd.substring(0,c).toInt();int st=cmd.substring(c+1).toInt();if(pin>=2&&pin<=19&&pinModes[pin]){digitalWrite(pin,st?HIGH:LOW);pinStates[pin]=st;String s="PIN "+pinLabel(pin)+" : "+ (st?"ON":"OFF");Serial.println(s);lcdMsg(s);} }
  else if(cmd.startsWith("PWM ")){int c=cmd.indexOf(',');int pin=cmd.substring(4,c).toInt();int val=cmd.substring(c+1).toInt();if((pin==3||pin==5||pin==6||pin==9||pin==10||pin==11)&&pinModes[pin]){analogWrite(pin,val);pinStates[pin]=val;String s="PIN "+pinLabel(pin)+" : "+String(val);Serial.println(s);lcdMsg(s);} }
  /* ALLMODE komutu kaldırıldı */
  else if(cmd.startsWith("ALL ")){int st=cmd.substring(4).toInt();for(int p=2;p<=19;p++){if(!pinModes[p])continue;if(p==3||p==5||p==6||p==9||p==10||p==11){analogWrite(p,st?255:0);pinStates[p]=st?255:0;}else {digitalWrite(p,st?HIGH:LOW);pinStates[p]=st?1:0;}}String msg = String("PIN ALL: ") + (st?"ON":"OFF");Serial.println(msg);lcdMsg(msg);} 
  else if(cmd.equals("STAT")){for(int p=2;p<=19;p++){Serial.print(pinLabel(p));Serial.print(":" );Serial.print(pinStates[p]);Serial.print(":" );Serial.print(pinModes[p]); // 0/1/2
        if(p<19)Serial.print(",");}Serial.println();}
  else if(cmd.equals("DIG")){for(int p=2;p<=19;p++){if(!pinModes[p]){int v=digitalRead(p);Serial.print("D");Serial.print(p);Serial.print(":" );Serial.print(v);Serial.print(",");}}Serial.println();}
  else if(cmd.equals("ANA")){for(int a=0;a<6;a++){int v=analogRead(a);analogValues[a]=v;Serial.print("A");Serial.print(a);Serial.print(":" );Serial.print(v);if(a<5)Serial.print(",");}Serial.println();}
 }
} 