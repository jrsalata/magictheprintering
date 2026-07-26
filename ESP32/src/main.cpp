#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>
#include "secrets.h"

const int RECONNECT_DELAY_MS = 5000;
const int STATUS_LED_PIN = 13;
const int LED_BLINK_INTERVAL_MS = 750;
const int BUTTON_PIN = 0;
const int DEBOUNCE_DELAY_MS = 50;

// TFT pins for Adafruit Feather ESP32-S3 Reverse TFT
const int TFT_CS_PIN   = 7;
const int TFT_DC_PIN   = 39;
const int TFT_RST_PIN  = 40;
const int TFT_BACKLITE_PIN = 45;

// Prefix used in the server's success message (e.g. "Printed Lightning Bolt")
const String PRINTED_PREFIX = "Printed ";

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

bool wasConnected = false;
bool ledState = false;
unsigned long lastLedToggleMs = 0;
unsigned long lastReconnectAttemptMs = 0;

int lastButtonState = HIGH;
int buttonState = HIGH;
unsigned long lastDebounceMs = 0;

void tftPrintMessage(const String &line1, const String &line2 = "") {
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.println(line1);
  if (line2.length() > 0) {
    tft.println(line2);
  }
}

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

// Extract the message text from the HTML response body.
// The server embeds the message in: <div class="message">...</div>
String extractMessage(const String &body) {
  const String marker = "class=\"message\">";
  int start = body.indexOf(marker);
  if (start == -1) {
    return "";
  }
  start += marker.length();
  int end = body.indexOf("</div>", start);
  if (end == -1) {
    return "";
  }
  return body.substring(start, end);
}

void callDiscordEndpoint() {
  if (WiFi.status() != WL_CONNECTED) {
    tftPrintMessage("No WiFi", "Check connection");
    return;
  }

  tftPrintMessage("Printing...");

  String endpointUrl = String(SERVER_URL) + "/discord";

  HTTPClient http;
  WiFiClientSecure secureClient;

  if (endpointUrl.startsWith("https://")) {
    secureClient.setInsecure();
    http.begin(secureClient, endpointUrl);
  } else {
    http.begin(endpointUrl);
  }

  http.setAuthorization(PRINTER_USERNAME, PRINTER_PASSWORD);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int httpCode = http.POST("");

  if (httpCode > 0) {
    String body = http.getString();
    String message = extractMessage(body);
    if (message.length() > 0) {
      String cardName = message.startsWith(PRINTED_PREFIX)
          ? message.substring(PRINTED_PREFIX.length())
          : message;
      tftPrintMessage("Printed:", cardName);
    } else {
      tftPrintMessage("Done", "HTTP " + String(httpCode));
    }
  } else {
    tftPrintMessage("Error", "HTTP " + String(httpCode));
  }

  http.end();
}

void setup() {
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Initialise TFT display
  pinMode(TFT_BACKLITE_PIN, OUTPUT);
  digitalWrite(TFT_BACKLITE_PIN, HIGH);
  tft.init(135, 240);
  tft.setRotation(3);
  tftPrintMessage("Connecting...");

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
    tftPrintMessage("Ready", "Press to print");
  } else {
    tftPrintMessage("WiFi failed", "Check credentials");
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

  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonState) {
    lastDebounceMs = millis();
  }

  if (millis() - lastDebounceMs >= DEBOUNCE_DELAY_MS) {
    if (reading != buttonState) {
      buttonState = reading;
      if (buttonState == LOW) {
        callDiscordEndpoint();
      }
    }
  }

  lastButtonState = reading;
  wasConnected = isConnected;
}
