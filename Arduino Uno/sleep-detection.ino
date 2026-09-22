#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);   // Change 0x27 if needed

int relayPin = 7;
int buzzerPin = 8;

bool sleeping = false;

void setup() {
  Serial.begin(9600);

  pinMode(relayPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  digitalWrite(relayPin, HIGH);   // motor ON
  digitalWrite(buzzerPin, LOW);

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0,0);
  lcd.print("Driver Monitor");
  lcd.setCursor(0,1);
  lcd.print("System Ready");
  delay(2000);
  lcd.clear();
}

void loop() {

  if (Serial.available()) {
    char data = Serial.read();

    // sleep detected
    if (data == 'S') {

      digitalWrite(relayPin, LOW);   // Stop motor
      digitalWrite(buzzerPin, HIGH);

      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("!! ALERT !!");
      lcd.setCursor(0,1);
      lcd.print("Driver Sleep");

      sleeping = true;
    }

    // awake detected
    if (data == 'A') {

      digitalWrite(relayPin, HIGH);  // motor On
      digitalWrite(buzzerPin, LOW);

      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Driver Awake");
      lcd.setCursor(0,1);
      lcd.print("Drive Safe");

      sleeping = false;
    }
  }
}