/*
 * Cronicl Scale Bridge -- Renpho ES-CS20M protocol diagnostic
 *
 * Flash with:  pio run -e diagnostic -t upload
 * Watch with:  pio device monitor -b 115200
 *
 * 1. Open the serial monitor.
 * 2. Step on the scale with bare feet and remain on it until it turns off.
 * 3. Save the complete log between the START and END markers.
 *
 * No measurement is uploaded by this program.  It is intentionally a
 * read-only BLE inspector used to build the scale-specific production decoder.
 */

#include <Arduino.h>
#include <map>
#include <string>
#include <BLEDevice.h>
#include <BLEClient.h>
#include <BLEScan.h>
#include <BLERemoteCharacteristic.h>
#include <BLERemoteDescriptor.h>
#include <BLERemoteService.h>

namespace {

constexpr uint32_t SCAN_SECONDS = 20;
constexpr uint32_t RESCAN_DELAY_MS = 3000;
constexpr char SCALE_NAME_PREFIX[] = "ES-CS20M";

BLEClient* client = nullptr;
BLEAdvertisedDevice selectedDevice;
bool scaleFound = false;
bool connected = false;

void printHex(const uint8_t* data, size_t length) {
  for (size_t i = 0; i < length; ++i) {
    Serial.printf("%02X%s", data[i], i + 1 == length ? "" : " ");
  }
}

void printValue(const std::string& value) {
  printHex(reinterpret_cast<const uint8_t*>(value.data()), value.length());
}

void onNotification(BLERemoteCharacteristic* characteristic, uint8_t* data,
                    size_t length, bool isNotify) {
  Serial.printf("FRAME kind=%s service=%s characteristic=%s bytes=%u hex=",
                isNotify ? "notify" : "indicate",
                characteristic->getRemoteService()->getUUID().toString().c_str(),
                characteristic->getUUID().toString().c_str(),
                static_cast<unsigned>(length));
  printHex(data, length);
  Serial.println();
}

class ScaleAdvertisedCallbacks final : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice device) override {
    const String name = device.haveName() ? String(device.getName().c_str()) : "";
    Serial.printf("ADVERTISEMENT address=%s rssi=%d name=%s payload=",
                  device.getAddress().toString().c_str(), device.getRSSI(),
                  name.length() ? name.c_str() : "<none>");
    if (device.haveManufacturerData()) {
      printValue(device.getManufacturerData());
    }
    Serial.println();

    if (!scaleFound && name.startsWith(SCALE_NAME_PREFIX)) {
      selectedDevice = device;
      scaleFound = true;
      Serial.println("SCALE_MATCH found ES-CS20M; stopping scan.");
      BLEDevice::getScan()->stop();
    }
  }
};

void inspectGatt() {
  auto* services = client->getServices();
  if (services == nullptr || services->empty()) {
    Serial.println("GATT_ERROR no services discovered");
    return;
  }

  for (const auto& serviceItem : *services) {
    BLERemoteService* service = serviceItem.second;
    Serial.printf("SERVICE uuid=%s\n", service->getUUID().toString().c_str());
    auto* characteristics = service->getCharacteristics();
    if (characteristics == nullptr) continue;

    for (const auto& characteristicItem : *characteristics) {
      BLERemoteCharacteristic* characteristic = characteristicItem.second;
      Serial.printf(
          "CHARACTERISTIC uuid=%s read=%d write=%d write_no_response=%d notify=%d indicate=%d\n",
          characteristic->getUUID().toString().c_str(), characteristic->canRead(),
          characteristic->canWrite(), characteristic->canWriteNoResponse(),
          characteristic->canNotify(), characteristic->canIndicate());

      if (characteristic->canRead()) {
        const std::string value = characteristic->readValue();
        Serial.print("READ_VALUE hex=");
        printValue(value);
        Serial.println();
      }
      if (characteristic->canNotify() || characteristic->canIndicate()) {
        characteristic->registerForNotify(
            onNotification, characteristic->canNotify(), characteristic->canIndicate());
        Serial.printf("SUBSCRIBE uuid=%s requested\n",
                      characteristic->getUUID().toString().c_str());
      }
    }
  }
}

bool connectAndInspect() {
  if (client == nullptr) client = BLEDevice::createClient();

  Serial.printf("CONNECT address=%s name=%s\n",
                selectedDevice.getAddress().toString().c_str(),
                selectedDevice.getName().c_str());
  if (!client->connect(&selectedDevice)) {
    Serial.println("CONNECT_FAILED");
    return false;
  }
  connected = true;
  Serial.println("CONNECT_OK");
  inspectGatt();
  Serial.println("--- CRONICL_SCALE_DIAGNOSTIC_READY: perform one full measurement ---");
  return true;
}

void scanForScale() {
  scaleFound = false;
  BLEScan* scan = BLEDevice::getScan();
  scan->clearResults();
  scan->setActiveScan(true);
  scan->setInterval(100);
  scan->setWindow(99);
  Serial.printf("SCAN_START seconds=%u target_prefix=%s\n", SCAN_SECONDS,
                SCALE_NAME_PREFIX);
  scan->start(SCAN_SECONDS, false);
  scan->clearResults();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n--- CRONICL_SCALE_DIAGNOSTIC_START ---");
  Serial.println("Target: RENPHO ES-CS20M. No network or API request will be made.");
  BLEDevice::init("Cronicl-Scale-Diagnostic");
  BLEDevice::getScan()->setAdvertisedDeviceCallbacks(new ScaleAdvertisedCallbacks());
}

void loop() {
  if (!connected) {
    scanForScale();
    if (scaleFound) {
      connectAndInspect();
    } else {
      Serial.printf("SCALE_NOT_FOUND retrying_in_ms=%u\n", RESCAN_DELAY_MS);
      delay(RESCAN_DELAY_MS);
    }
  }
  delay(100);
}
