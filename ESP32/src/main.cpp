#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h"

const int RECONNECT_DELAY_MS = 5000;

bool wasConnected = false;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  Serial.println("Connecting to WiFi...");
  Serial.print("SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    wasConnected = true;
  } else {
    Serial.println();
    Serial.println("Failed to connect to WiFi. Check your credentials in secrets.h.");
  }
}

void loop() {
  bool isConnected = WiFi.status() == WL_CONNECTED;

  if (wasConnected && !isConnected) {
    Serial.println("WiFi disconnected. Reconnecting...");
    WiFi.reconnect();
    delay(RECONNECT_DELAY_MS);
  } else if (!wasConnected && isConnected) {
    Serial.println("WiFi reconnected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  }

  wasConnected = isConnected;
}
