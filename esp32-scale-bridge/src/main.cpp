/*
 * FitTrack Scale Bridge — ESP32 Main Firmware
 *
 * Reads weight + impedance from a Renpho BLE body fat scale,
 * sends data to FitTrack API via HTTPS.
 *
 * Protocol: The Renpho scale sends data via BLE notifications on
 * service 0xFFE1. The payload format (reverse-engineered by the
 * open-source community, notably openScale and wiecosystem projects):
 *
 * - First packet: header + weight (when measurement stabilizes)
 * - Second packet: impedance (after the user stands still long enough)
 *
 * Weight encoding: The scale sends a few bytes. The weight value is
 * typically encoded as a 16-bit integer with a factor depending on
 * the scale firmware. Common encoding: weight_kg = raw_value / 100.0
 * or weight_kg = raw_value / 200.0.
 *
 * This firmware uses the widely-documented Renpho protocol. If your
 * specific scale model uses a different encoding, adjust the parse
 * functions accordingly.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <BLEDevice.h>
#include <BLEClient.h>
#include <BLERemoteService.h>
#include <BLERemoteCharacteristic.h>
#include <ArduinoJson.h>
#include "config.h"

// --- State machine ---
enum ScaleState {
  STATE_IDLE,         // waiting for user to step on scale
  STATE_SCANNING,     // BLE scanning for scale
  STATE_CONNECTED,    // connected to scale, waiting for data
  STATE_GOT_WEIGHT,   // received weight, waiting for impedance
  STATE_GOT_IMPEDANCE,// received impedance, ready to send
  STATE_SENDING,      // sending data to API
  STATE_DONE,         // sent successfully, back to idle
  STATE_ERROR         // error, will retry
};

static ScaleState state = STATE_IDLE;
static BLEClient* pClient = nullptr;
static BLERemoteCharacteristic* pDataChar = nullptr;

// Parsed measurement data
static float measuredWeight = 0.0;
static int measuredImpedance = 0;
static bool weightReceived = false;
static bool impedanceReceived = false;
static unsigned long lastDataTime = 0;

// --- Forward declarations ---
static void notifyCallback(BLERemoteCharacteristic*, uint8_t*, size_t);
static bool connectToScale();
static bool sendToApi();
static void resetMeasurement();
static void enterState(ScaleState newState);

// ============================================================
// BLE notification callback — called when scale sends data
// ============================================================
static void notifyCallback(
  BLERemoteCharacteristic* pChar,
  uint8_t* pData,
  size_t length
) {
  if (length < 2) return;

  Serial.print("BLE data (");
  Serial.print(length);
  Serial.print(" bytes): ");
  for (size_t i = 0; i < length; i++) {
    Serial.printf("%02X ", pData[i]);
  }
  Serial.println();

  lastDataTime = millis();

  // Renpho protocol parsing (simplified — based on openScale/wiecosystem)
  // The first byte is typically a control/header byte:
  //   0x01 = weight measurement
  //   0x02 = impedance measurement
  //   0x00 = start/ack

  uint8_t header = pData[0];

  if (header == 0x01 && length >= 4) {
    // Weight data — extract from bytes 1-2 (little-endian)
    // Common encoding: weight_kg = raw / 200.0 or raw / 100.0
    // The exact factor depends on the scale model — adjust if needed
    uint16_t rawWeight = (pData[2] << 8) | pData[1];
    measuredWeight = rawWeight / 200.0;
    weightReceived = true;
    Serial.printf("  → Weight: %.1f kg (raw: %d)\n", measuredWeight, rawWeight);
    enterState(STATE_GOT_WEIGHT);

  } else if (header == 0x02 && length >= 3) {
    // Impedance data
    measuredImpedance = (pData[2] << 8) | pData[1];
    impedanceReceived = true;
    Serial.printf("  → Impedance: %d ohm\n", measuredImpedance);
    enterState(STATE_GOT_IMPEDANCE);

  } else if (header == 0x00) {
    // Scale started measuring
    Serial.println("  → Scale measurement started");
  }
}

// ============================================================
// Connect to the Renpho BLE scale
// ============================================================
static bool connectToScale() {
  Serial.println("Scanning for BLE scale...");

  BLEScan* pScan = BLEDevice::getScan();
  pScan->setActiveScan(true);
  BLEScanResults results = pScan->start(BLE_SCAN_DURATION);

  BLEAdvertisedDevice* scaleDevice = nullptr;
  for (int i = 0; i < results.getCount(); i++) {
    BLEAdvertisedDevice dev = results.getDevice(i);
    String name = dev.getName().c_str();
    Serial.printf("  Found: %s (addr: %s)\n", name.c_str(), dev.getAddress().toString().c_str());

    if (name.startsWith(SCALE_NAME_PREFIX) ||
        name.indexOf("RENPHO") >= 0 ||
        name.indexOf("QNB") >= 0) {
      // Found a scale — clone it (BLEAdvertisedDevice from scan results is transient)
      static BLEAdvertisedDevice foundDevice;
      foundDevice = dev;
      scaleDevice = &foundDevice;
      break;
    }
  }

  if (!scaleDevice) {
    Serial.println("Scale not found in scan.");
    return false;
  }

  Serial.printf("Connecting to scale: %s\n", scaleDevice->getName().c_str());

  if (pClient == nullptr) {
    pClient = BLEDevice::createClient();
  }

  if (!pClient->connect(scaleDevice)) {
    Serial.println("Failed to connect to scale.");
    return false;
  }

  Serial.println("Connected. Subscribing to notifications...");

  BLERemoteService* pService = pClient->getService(BLEUUID(SCALE_SERVICE_UUID));
  if (!pService) {
    Serial.println("Scale service not found.");
    pClient->disconnect();
    return false;
  }

  pDataChar = pService->getCharacteristic(BLEUUID(SCALE_CHAR_UUID));
  if (!pDataChar) {
    Serial.println("Data characteristic not found.");
    pClient->disconnect();
    return false;
  }

  pDataChar->registerForNotify(notifyCallback);

  // Enable notifications
  uint8_t enable[] = {0x01, 0x00};
  BLERemoteDescriptor* pDesc = pDataChar->getDescriptor(BLEUUID((uint16_t)0x2902));
  if (pDesc) {
    pDesc->writeValue(enable, 2, true);
  }

  Serial.println("Subscribed. Waiting for measurement...");
  return true;
}

// ============================================================
// Send measurement to FitTrack API
// ============================================================
static bool sendToApi() {
  Serial.println("Sending to FitTrack API...");

  WiFiClientSecure client;
  client.setInsecure();  // skip cert verification (self-signed sslip.io)
  client.setTimeout(HTTP_TIMEOUT / 1000);

  if (!client.connect(API_HOST, API_PORT)) {
    Serial.println("HTTPS connection failed.");
    return false;
  }

  // Build JSON payload
  StaticJsonDocument<512> doc;
  doc["weight_kg"] = measuredWeight;
  if (impedanceReceived && measuredImpedance > 0) {
    doc["impedance"] = measuredImpedance;
  }
  doc["height_cm"] = USER_HEIGHT_CM;
  doc["age"] = USER_AGE;
  doc["gender"] = USER_GENDER;
  doc["device_id"] = "esp32-scale-bridge";

  String json;
  serializeJson(doc, json);

  // Build HTTP request
  String request = "POST " + String(API_PATH) + " HTTP/1.1\r\n";
  request += "Host: " + String(API_HOST) + "\r\n";
  request += "X-FitTrack-CLI-Key: " + String(API_KEY) + "\r\n";
  request += "Content-Type: application/json\r\n";
  request += "Content-Length: " + String(json.length()) + "\r\n";
  request += "Connection: close\r\n";
  request += "\r\n";
  request += json;

  client.print(request);

  // Read response
  String response = "";
  while (client.connected() || client.available()) {
    if (client.available()) {
      response += client.readString();
    }
    delay(10);
  }

  // Check for 200
  if (response.indexOf("200") > 0 || response.indexOf("201") > 0) {
    Serial.println("API: OK ✓");
    return true;
  } else {
    Serial.print("API error: ");
    Serial.println(response.substring(0, 200));
    return false;
  }
}

// ============================================================
// State machine helpers
// ============================================================
static void resetMeasurement() {
  measuredWeight = 0.0;
  measuredImpedance = 0;
  weightReceived = false;
  impedanceReceived = false;
}

static void enterState(ScaleState newState) {
  if (newState != state) {
    Serial.printf("State: %d → %d\n", state, newState);
    state = newState;
  }
}

// ============================================================
// Setup
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== FitTrack Scale Bridge ===\n");

  // Connect WiFi
  Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nWiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());

  // Init BLE
  Serial.println("Initializing BLE...");
  BLEDevice::init("FitTrack-Scale-Bridge");

  enterState(STATE_IDLE);
  Serial.println("Ready. Step on scale to measure.\n");
}

// ============================================================
// Main loop
// ============================================================
void loop() {
  switch (state) {

    case STATE_IDLE:
      // Start scanning when idle
      enterState(STATE_SCANNING);
      resetMeasurement();
      break;

    case STATE_SCANNING:
      if (connectToScale()) {
        enterState(STATE_CONNECTED);
        lastDataTime = millis();
      } else {
        Serial.println("Retrying in 30s...");
        delay(30000);
        enterState(STATE_IDLE);
      }
      break;

    case STATE_CONNECTED:
      // Wait for weight data, with timeout
      if (weightReceived) {
        // Weight received, waiting for impedance
      } else if (millis() - lastDataTime > 60000) {
        Serial.println("Timeout: no weight received in 60s. Disconnecting.");
        pClient->disconnect();
        delay(1000);
        enterState(STATE_IDLE);
      }
      break;

    case STATE_GOT_WEIGHT:
      // Wait for impedance (if scale supports it)
      if (impedanceReceived) {
        enterState(STATE_GOT_IMPEDANCE);
      } else if (millis() - lastDataTime > 15000) {
        // No impedance after 15s — send weight only
        Serial.println("No impedance received, sending weight only.");
        enterState(STATE_SENDING);
      }
      break;

    case STATE_GOT_IMPEDANCE:
      enterState(STATE_SENDING);
      break;

    case STATE_SENDING:
      if (sendToApi()) {
        enterState(STATE_DONE);
      } else {
        Serial.println("API send failed. Retrying in 10s...");
        delay(10000);
        // Retry once more
        if (sendToApi()) {
          enterState(STATE_DONE);
        } else {
          enterState(STATE_ERROR);
        }
      }
      // Disconnect from scale
      if (pClient && pClient->isConnected()) {
        pClient->disconnect();
        delay(500);
      }
      break;

    case STATE_DONE:
      Serial.println("\n✓ Measurement complete. Back to idle in 10s.\n");
      delay(10000);
      enterState(STATE_IDLE);
      break;

    case STATE_ERROR:
      Serial.println("\n✗ Error. Retrying in 30s.\n");
      delay(30000);
      enterState(STATE_IDLE);
      break;
  }

  // Small delay to prevent busy-looping
  delay(100);
}