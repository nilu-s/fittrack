# FitTrack Scale Bridge — ESP32

ESP32 firmware that reads a Renpho BLE body fat scale and sends weight + impedance to the FitTrack API.

## Hardware

- **ESP32** (any variant with BLE + WiFi — ESP32-DevKit, ESP32-WROOM, etc.)
- **Renpho Bluetooth Body Fat Scale** (Amazon B01N1UX8RW or similar Renpho BLE scale)
- ESP32 must be within BLE range (~10m) of the scale AND connected to WiFi

## How it works

1. ESP32 scans for BLE devices with Renpho-scale names
2. Connects via GATT to service `0xFFE1`
3. Subscribes to data characteristic notifications
4. When you step on the scale:
   - Scale sends weight data → ESP32 parses it
   - Scale sends impedance data → ESP32 parses it
5. ESP32 sends JSON POST to `https://fittrack.49.12.225.84.sslip.io/api/scale-sync`
6. API calculates body composition (BMI, body fat %, muscle mass, water %, bone mass, BMR, visceral fat, metabolic age) from weight + impedance + user profile
7. UI shows weight in biometrics card with "Waage ✓" badge and expandable body composition details

## Setup

```bash
# Install PlatformIO
pip install platformio

# Copy config template
cp src/config.h.example src/config.h

# Edit config.h with your WiFi, API key, and user profile
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

Then wake the scale by stepping on it, perform one complete bare-foot
measurement, and save the serial output from
`FITTRACK_SCALE_DIAGNOSTIC_START` through the last `FRAME` line. The diagnostic
prints advertisement data, every discovered GATT service/characteristic and
all notification/indication frames; it never sends a measurement to FitTrack.

Send that log back before flashing the normal `esp32dev` environment. We use it
to implement and test the ES-CS20M-specific decoder rather than guessing a
generic Renpho packet format.

## Config (config.h)

| Setting | Description |
|---|---|
| `WIFI_SSID` | Your home WiFi name |
| `WIFI_PASSWORD` | Your home WiFi password |
| `API_HOST` | FitTrack server hostname |
| `API_KEY` | Must match `FITTRACK_CLI_KEY` env var on server |
| `USER_HEIGHT_CM` | Your height in cm (for body comp calc) |
| `USER_AGE` | Your age |
| `USER_GENDER` | `"male"` or `"female"` |
| `SCALE_NAME_PREFIX` | BLE name prefix of your scale (try `"QN-Scale"` or scan first) |

## BLE Protocol

The Renpho scale protocol has been reverse-engineered by the open-source community (openScale, wiecosystem projects). Key details:

- **Service UUID**: `0000ffe1-0000-1000-8000-00805f9b34fb`
- **Characteristic**: same UUID, sends notifications
- **Weight packet**: header `0x01` + 16-bit little-endian weight value
- **Impedance packet**: header `0x02` + 16-bit impedance value
- **Weight encoding**: `weight_kg = raw_value / 200.0` (common factor — adjust if your scale differs)

If your specific Renpho model uses a different encoding, watch the serial monitor's hex dump and adjust the parse logic in `main.cpp`.

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
| API auth failed | Check `API_KEY` matches `FITTRACK_CLI_KEY` on server |
| HTTPS connection failed | Ensure ESP32 has internet access (not just LAN) |
| No impedance | Some scales don't send impedance if feet aren't planted correctly — weight-only still works |
