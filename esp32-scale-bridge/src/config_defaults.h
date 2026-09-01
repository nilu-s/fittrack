#ifndef APP_CONFIG_DEFAULTS_H
#define APP_CONFIG_DEFAULTS_H

// Credential-free compile defaults. A local config.h overrides these values
// for a flashed bridge and is deliberately ignored by Git.
#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
#ifndef API_HOST
#define API_HOST ""
#endif
#ifndef API_PORT
#define API_PORT 443
#endif
#ifndef API_PATH
#define API_PATH "/api/scale-sync/v2"
#endif
#ifndef DEVICE_ID
#define DEVICE_ID ""
#endif
#ifndef DEVICE_KEY
#define DEVICE_KEY ""
#endif
#ifndef SCALE_BLE_ADDRESS
#define SCALE_BLE_ADDRESS ""
#endif
#ifndef HTTP_TIMEOUT
#define HTTP_TIMEOUT 10000
#endif

#endif
