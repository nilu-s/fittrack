from app.schemas import ScaleSyncV2Request


def test_scale_bridge_payload_is_accepted():
    payload = ScaleSyncV2Request.model_validate(
        {
            "weight_kg": 82.4,
            "device_id": "esp32-scale-bridge",
            "device_event_id": "fixture-82-4",
            "measured_at": "2026-08-31T07:15:02Z",
            "impedance_ohm": None,
            "protocol": "renpho-aabb",
            "protocol_version": 1,
        }
    )

    assert payload.weight_kg == 82.4
    assert payload.impedance_ohm is None


def test_scale_sync_proxy_route_is_exempt_from_browser_basic_auth():
    with open("../infra/caddy/Caddyfile", encoding="utf-8") as caddyfile:
        config = caddyfile.read()

    scale_handler = "@scale_sync path /api/scale-sync/v2\n  handle @scale_sync {\n    reverse_proxy fittrack-api:8000\n  }"
    api_handler = "@api path /api/*"

    assert scale_handler in config
    assert config.index(scale_handler) < config.index(api_handler)
