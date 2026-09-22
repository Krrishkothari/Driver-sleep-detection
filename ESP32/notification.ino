// this code is for the esp32 to send a notification to telegram bot 

#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Your_SSID_Here";
const char* password = "your_password_here";

String botToken = "your_bot_token_here";
String chatID = "YOUR_CHAT_ID_HERE";

void sendTelegram(String message) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    String url = "https://api.telegram.org/bot" + botToken +
                 "/sendMessage?chat_id=" + chatID +
                 "&text=" + message;

    http.begin(url);
    http.GET();
    http.end();
  }
}

void setup() {
  Serial.begin(9600);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void loop() {
  if (Serial.available()) {
    char data = Serial.read();

    if (data == 'S') {
      sendTelegram("🚨 ALERT: Driver sleeping for 5 seconds!");
    }
  }
}