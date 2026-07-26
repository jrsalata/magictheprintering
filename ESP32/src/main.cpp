#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h"

const int RECONNECT_DELAY_MS = 5000;
const int STATUS_LED_PIN = 13;
const int LED_BLINK_INTERVAL_MS = 750;

bool wasConnected = false;
bool ledState = false;
unsigned long lastLedToggleMs = 0;
unsigned long lastReconnectAttemptMs = 0;

void updateStatusLed(bool isConnected) {
  if (isConnected) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    ledState = true;
    return;
  }

  unsigned long now = millis();
  if (now - lastLedToggleMs >= LED_BLINK_INTERVAL_MS) {
    ledState = !ledState;
    digitalWrite(STATUS_LED_PIN, ledState ? HIGH : LOW);
    lastLedToggleMs = now;
  }
}

void setup() {
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    updateStatusLed(false);
    delay(500);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wasConnected = true;
    updateStatusLed(true);
  }
}

void loop() {
  bool isConnected = WiFi.status() == WL_CONNECTED;
  updateStatusLed(isConnected);

  if (!isConnected) {
    unsigned long now = millis();
    if (now - lastReconnectAttemptMs >= RECONNECT_DELAY_MS) {
      WiFi.reconnect();
      lastReconnectAttemptMs = now;
    }
  }

  wasConnected = isConnected;
}
