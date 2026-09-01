# Scale bridge area rules

The ESP32 is an untrusted device source. It submits only a raw measurement with
its registered device key and never selects an account or contains profile data.
Do not read, log, or commit `src/config.h`.

Read the Scale v2 contract and multi-account specification before changing BLE
parsing or transport. Preserve raw event fidelity and keep protocol observation
in `diagnostic.cpp` credential-free.

Run `pio run` and `pio run -e diagnostic` when changing firmware or its build
configuration.
