from app.schemas import ScaleSyncRequest


def test_scale_bridge_payload_is_accepted():
    payload = ScaleSyncRequest.model_validate(
        {
            "weight_kg": 82.4,
            "impedance": 512,
            "height_cm": 180,
            "age": 30,
            "gender": "male",
            "device_id": "esp32-scale-bridge",
        }
    )

    assert payload.weight_kg == 82.4
    assert payload.impedance == 512


def test_scale_sync_proxy_route_is_exempt_from_browser_basic_auth():
    with open("../infra/caddy/Caddyfile", encoding="utf-8") as caddyfile:
        config = caddyfile.read()

    scale_handler = "@scale_sync path /api/scale-sync\n  handle @scale_sync {\n    reverse_proxy fittrack-api:8000\n  }"
    api_handler = "@api path /api/*"

    assert scale_handler in config
    assert config.index(scale_handler) < config.index(api_handler)
