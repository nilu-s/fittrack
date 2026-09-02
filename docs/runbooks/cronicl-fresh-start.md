# Cronicl: frischer Produktionsstart

Cronicl verwendet eine neue, leere Datenbank und übernimmt keine Daten aus
der früheren Laufzeit. Die technischen Namen sind absichtlich neutral (`app`,
`db`, `api`, `web`), während `APP_NAME` die sichtbare Marke festlegt.

Die frühere Daten- und Migrationshistorie ist für den aktiven Betrieb
superseded. Sie wird in einem eigenen, geprüften Bereinigungsschritt durch eine
einzige Cronicl-Baseline ersetzt; nicht mehr verwendete Migrationen,
Kompatibilitätscode und Verträge werden dabei gemeinsam entfernt.

## Einmalige Konfiguration

In der produktiven, nicht versionierten `.env` müssen mindestens diese Werte
gesetzt sein. Keine Geheimnisse in dieses Repository oder in den Chat kopieren.

```env
APP_NAME=Cronicl
APP_PUBLIC_ORIGIN=https://DEIN-ENDGUELTIGER-HOSTNAME
APP_DB_PASSWORD=...
APP_JWT_SECRET=...
```

`APP_PUBLIC_ORIGIN` muss auch als autorisierte Redirect-URI
`${APP_PUBLIC_ORIGIN}/api/google/callback` beim bestehenden Google-OAuth-Client
hinterlegt sein. Der Host muss vor dem Start per DNS auf den Server zeigen.

## Startreihenfolge

1. Die obigen Variablen setzen und den neuen Google-OAuth-Redirect hinterlegen.
2. Neue Images bauen und starten: `docker compose up -d --build`.
3. Gegen die neue, leere Datenbank migrieren: `docker compose exec api alembic upgrade head`.
4. Im Browser anmelden und die Health-Route sowie Ortssuche testen.
5. Die ESP32-Konfiguration mit dem finalen Host und `X-App-Device-Key` bauen
   und erst dann auf das Gerät flashen.

Die bisherige Datenbank bzw. ihr Docker-Volume wird in diesem Ablauf nicht
verwendet. Sie darf erst nach erfolgreicher Abnahme explizit entfernt werden.
