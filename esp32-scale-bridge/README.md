# Chronickel Scale Bridge — ESP32

ESP32 firmware that reads a Renpho AABB broadcast scale and sends a raw,
weight-only device event to the Chronickel API.

## Hardware

- **ESP32** (any variant with BLE + WiFi — ESP32-DevKit, ESP32-WROOM, etc.)
- **Renpho Bluetooth Body Fat Scale** (Amazon B01N1UX8RW or similar Renpho BLE scale)
- ESP32 must be within BLE range (~10m) of the scale AND connected to WiFi

## How it works

1. ESP32 passively scans the configured AABB broadcast address.
2. A final weight frame creates one stable device event ID.
3. ESP32 retries that exact event at `POST /api/scale-sync/v2` with
   `X-App-Device-Key`.
4. The server, never the firmware, assigns an accepted event to an account.

## Setup

```bash
# Install PlatformIO
pip install platformio

# Copy config template
cp src/config.h.example src/config.h

# Edit config.h with WiFi and the dedicated device credential
nano src/config.h

# Build and upload
pio run -t upload

# Monitor serial output
pio run -t monitor
```

## First: identify the exact ES-CS20M protocol

The Amazon model is **RENPHO ES-CS20M**. Do this before using the production
bridge: BLE protocol variants differ between Renpho models.

```bash
# Upload the non-invasive BLE diagnostic (no WiFi/API configuration required)
pio run -e diagnostic -t upload
pio device monitor -b 115200
```

Then wake the scale and save the serial output from
`CHRONICKEL_SCALE_DIAGNOSTIC_START` through the last `FRAME` line. The diagnostic
prints advertisement data, every discovered GATT service/characteristic and
all notification/indication frames; it never sends a measurement to Chronickel.

Use the log only to verify the AABB weight-frame decoder before flashing the
normal `esp32dev` environment. This release is weight-only: no impedance or
body-composition data is captured, inferred, or sent.

## Config (config.h)

| Setting | Description |
|---|---|
| `WIFI_SSID` | Your home WiFi name |
| `WIFI_PASSWORD` | Your home WiFi password |
| `API_HOST` | Chronickel server hostname |
| `DEVICE_ID` | Registered server-side bridge ID |
| `DEVICE_KEY` | Dedicated device credential; never a user credential |
| `SCALE_BLE_ADDRESS` | AABB broadcast address emitted by the diagnostic |

## BLE protocol boundary

The bridge accepts only the configured scale's final AABB broadcast frame and
extracts a stable weight. Other Renpho protocols and any future impedance
support require a separately approved protocol and body-composition change;
they are not part of this firmware.

## Manual entry still works

When you weigh yourself away from home, you can still manually enter weight in the app:
- Tap the edit icon (✎) on the weight biometric card
- Enter your weight
- It will be saved with `weight_source = "manual"`

The app shows a badge: "Waage ✓" (from ESP) or "manuell" (manual entry).

## Finding your scale's BLE name

If `QN-Scale` doesn't match, scan for BLE devices:

```bash
# After uploading firmware, open serial monitor
pio run -t monitor

# The firmware prints all BLE devices found during scan
# Look for your scale's name and update SCALE_NAME_PREFIX in config.h
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Scale not found in BLE scan | Check scale is in pairing mode (usually automatic when stepping on it) |
| Wrong weight values | Adjust the weight encoding factor in `parseScaleData()` |
| API auth failed | Check `DEVICE_KEY` against the registered device credential |
| `401 Unknown device` | Device ID is unregistered, inactive, or the credential is wrong |
| HTTPS connection failed | Ensure ESP32 has internet access (not just LAN) |
| No body composition | This bridge intentionally sends weight only |
