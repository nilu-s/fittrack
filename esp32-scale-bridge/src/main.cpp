/*
 * FitTrack Scale Bridge -- RENPHO ES-CS20M AABB broadcast variant.
 *
 * This hardware revision is not GATT-connectable. It broadcasts a 0xAABB
 * manufacturer-data frame; final frames contain weight only. The ESP32 scans
 * passively and never writes to or pairs with the scale.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <NimBLEDevice.h>
#include <string>
#include <time.h>
#if __has_include("config.h")
#include "config.h"
#endif
#include "config_defaults.h"

constexpr uint8_t COMPANY_ID_LOW = 0xFF;
constexpr uint8_t COMPANY_ID_HIGH = 0xFF;
constexpr uint8_t AABB_MAGIC_0 = 0xAA;
constexpr uint8_t AABB_MAGIC_1 = 0xBB;
constexpr size_t COMPANY_ID_BYTES = 2;
constexpr size_t AABB_MIN_PAYLOAD_LENGTH = 19;
constexpr size_t STATUS_OFFSET = 15;
constexpr size_t WEIGHT_OFFSET = 17;
constexpr uint8_t FINAL_FRAME_FLAG = 0x01;
constexpr unsigned long WIFI_RETRY_MS = 15000;
constexpr unsigned long SEND_RETRY_MS = 10000;
constexpr unsigned long MEASUREMENT_COOLDOWN_MS = 10000;

static portMUX_TYPE measurementLock = portMUX_INITIALIZER_UNLOCKED;
static bool measurementPending = false;
static float pendingWeightKg = 0.0f;
static String pendingEventId;
static String pendingMeasuredAt;
static uint32_t eventSequence = 0;
static unsigned long lastMeasurementAt = 0;
static unsigned long lastWifiAttemptAt = 0;
static unsigned long lastSendAttemptAt = 0;
static bool wifiConnectedReported = false;

static bool sendToApi(float weightKg, const String& eventId, const String& measuredAt);

static String utcTimestamp() {
  const time_t now = time(nullptr);
  if (now < 1700000000) return "";
  struct tm utc{};
  gmtime_r(&now, &utc);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(buffer);
}

static bool isTargetScale(const NimBLEAdvertisedDevice* device) {
  const String address(device->getAddress().toString().c_str());
  if (!address.equalsIgnoreCase(SCALE_BLE_ADDRESS)) return false;
  const std::string manufacturer = device->getManufacturerData();
  return manufacturer.size() >= COMPANY_ID_BYTES + AABB_MIN_PAYLOAD_LENGTH &&
      static_cast<uint8_t>(manufacturer[0]) == COMPANY_ID_LOW &&
      static_cast<uint8_t>(manufacturer[1]) == COMPANY_ID_HIGH &&
      static_cast<uint8_t>(manufacturer[2]) == AABB_MAGIC_0 &&
      static_cast<uint8_t>(manufacturer[3]) == AABB_MAGIC_1;
}

static bool parseFinalWeight(const std::string& manufacturer, float* weightKg) {
  if (manufacturer.size() < COMPANY_ID_BYTES + AABB_MIN_PAYLOAD_LENGTH) return false;
  const auto* payload = reinterpret_cast<const uint8_t*>(manufacturer.data() + COMPANY_ID_BYTES);
  if (payload[0] != AABB_MAGIC_0 || payload[1] != AABB_MAGIC_1) return false;
  if ((payload[STATUS_OFFSET] & FINAL_FRAME_FLAG) == 0) return false;

  const uint16_t weightRaw = static_cast<uint16_t>(payload[WEIGHT_OFFSET]) |
      (static_cast<uint16_t>(payload[WEIGHT_OFFSET + 1]) << 8);
  const float parsedWeight = weightRaw / 100.0f;
  if (parsedWeight < 0.5f || parsedWeight > 300.0f) return false;
  *weightKg = parsedWeight;
  return true;
}

class ScaleScanCallbacks final : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice* device) override {
    if (!isTargetScale(device)) return;
    const std::string manufacturer = device->getManufacturerData();
    float weightKg = 0.0f;
    if (!parseFinalWeight(manufacturer, &weightKg)) return;

    const unsigned long now = millis();
    const String measuredAt = utcTimestamp();
    if (measuredAt.isEmpty()) return;
    portENTER_CRITICAL(&measurementLock);
    const bool withinCooldown = now - lastMeasurementAt < MEASUREMENT_COOLDOWN_MS;
    if (!measurementPending && !withinCooldown) {
      pendingWeightKg = weightKg;
      pendingMeasuredAt = measuredAt;
      pendingEventId = String(ESP.getEfuseMac(), HEX) + "-" + String(++eventSequence) + "-" + String(now);
      measurementPending = true;
      lastMeasurementAt = now;
      Serial.printf("RENPHO AABB final measurement: %.2f kg\n", weightKg);
    }
    portEXIT_CRITICAL(&measurementLock);
  }
};

static ScaleScanCallbacks scanCallbacks;

static void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiConnectedReported) {
      Serial.printf("WiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());
      wifiConnectedReported = true;
    }
    return;
  }
  wifiConnectedReported = false;
  const unsigned long now = millis();
  if (lastWifiAttemptAt != 0 && now - lastWifiAttemptAt < WIFI_RETRY_MS) return;
  lastWifiAttemptAt = now;
  Serial.printf("Connecting to WiFi: %s\n", WIFI_SSID);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

static bool sendToApi(float weightKg, const String& eventId, const String& measuredAt) {
  if (WiFi.status() != WL_CONNECTED) return false;
  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(HTTP_TIMEOUT / 1000);
  if (!client.connect(API_HOST, API_PORT)) {
    Serial.println("HTTPS connection failed.");
    return false;
  }

  StaticJsonDocument<384> doc;
  doc["weight_kg"] = weightKg;
  doc["device_id"] = DEVICE_ID;
  doc["device_event_id"] = eventId;
  doc["measured_at"] = measuredAt;
  doc["impedance_ohm"] = nullptr;
  doc["protocol"] = "renpho-aabb";
  doc["protocol_version"] = 1;

  String json;
  serializeJson(doc, json);
  String request = "POST " + String(API_PATH) + " HTTP/1.1\r\n";
  request += "Host: " + String(API_HOST) + "\r\n";
  request += "X-FitTrack-Device-Key: " + String(DEVICE_KEY) + "\r\n";
  request += "Content-Type: application/json\r\n";
  request += "Content-Length: " + String(json.length()) + "\r\n";
  request += "Connection: close\r\n\r\n";
  request += json;
  client.print(request);

  String response;
  while (client.connected() || client.available()) {
    if (client.available()) response += client.readString();
    delay(10);
  }
  if (response.indexOf("HTTP/1.1 200") >= 0 || response.indexOf("HTTP/1.1 201") >= 0) {
    Serial.printf("FitTrack API: OK (%.2f kg)\n", weightKg);
    return true;
  }
  Serial.printf("FitTrack API error: %s\n", response.substring(0, 200).c_str());
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== FitTrack Scale Bridge: RENPHO AABB Broadcast ===\n");
  if (String(WIFI_SSID).isEmpty() || String(API_HOST).isEmpty() ||
      String(DEVICE_ID).isEmpty() || String(DEVICE_KEY).isEmpty() ||
      String(SCALE_BLE_ADDRESS).isEmpty()) {
    Serial.println("Bridge is not configured; create local src/config.h from config.h.example.");
    return;
  }
  WiFi.mode(WIFI_STA);
  ensureWifi();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  NimBLEDevice::init("FitTrack-Scale-Bridge");
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&scanCallbacks, true);
  scan->setActiveScan(true);
  scan->setInterval(100);
  scan->setWindow(99);
  scan->start(0, false, true);
  Serial.printf("Listening for RENPHO AABB broadcasts from %s\n", SCALE_BLE_ADDRESS);
}

void loop() {
  ensureWifi();
  float weightToSend = 0.0f;
  String eventToSend;
  String measuredAtToSend;
  bool shouldSend = false;
  const unsigned long now = millis();
  portENTER_CRITICAL(&measurementLock);
  if (measurementPending && now - lastSendAttemptAt >= SEND_RETRY_MS) {
    weightToSend = pendingWeightKg;
    eventToSend = pendingEventId;
    measuredAtToSend = pendingMeasuredAt;
    lastSendAttemptAt = now;
    shouldSend = true;
  }
  portEXIT_CRITICAL(&measurementLock);

  if (shouldSend && sendToApi(weightToSend, eventToSend, measuredAtToSend)) {
    portENTER_CRITICAL(&measurementLock);
    measurementPending = false;
    portEXIT_CRITICAL(&measurementLock);
  }
  delay(100);
}
