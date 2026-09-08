# Native Anreisebegleitung betreiben und abnehmen

Governing: `../specs/native-travel-companion.md`. Implementierung: `../plans/2026-09-08-native-travel-implementation.md`.

## Server

API und `travel-worker` verwenden dieselbe Datenbankkonfiguration. Vor neuem Code `alembic upgrade head` aus dem neu gebauten API-Image ausführen. Der Worker läuft als eigener Compose-Service, verwendet persistente Überwachungen und eine transaktionale Outbox. Ein PostgreSQL-Advisory-Lock verhindert parallele Worker-Ticks. Fehler werden ohne Payloads protokolliert. Alle 30 Sekunden wird fällige Arbeit geprüft; pro Tick maximal `TRAVEL_MAX_CHECKS_PER_TICK` (Standard 10, effektiv 1–50) Überwachungen, mit höchstens zwei Google-Anfragen je Prüfung. Das ist eine technische Obergrenze, kein monatliches Kostenversprechen.

Bestehende Maps-Konfiguration wird übernommen. Bei fehlendem Schlüssel wird die fehlgeschlagene Verkehrsprüfung im UI angezeigt. `TRAVEL_PUSH_ENABLED=false` ist der sichere Standard bis zur Einrichtung des jeweiligen Providers. Keine Vorab-Einrichtung behaupten, wenn nur die Standort-/Push-Rechte am Telefon erteilt wurden.

### Push-Konfiguration (extern)

- Apple: `APNS_KEY_FILE` (Pfad innerhalb des Worker-Containers), `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_TOPIC=app.cronicl.mobile`, `APNS_SANDBOX=true` für Entwicklungs-Builds beziehungsweise `false` für Distribution.
- Android: `FCM_PROJECT_ID`, `FCM_CREDENTIALS_FILE` (Service-Account-Datei innerhalb des Worker-Containers). Firebase-Projekt muss zur mobilen Konfiguration passen.
- Private Dateien außerhalb Git in `secrets/travel/` ablegen; Worker-Mount: `/run/secrets/travel`. Dateien nicht in Logs oder Chat kopieren. Nur nach korrekter Providerkonfiguration `TRAVEL_PUSH_ENABLED=true` setzen und API/Worker neu starten.
- Die Push-Nachricht enthält keine Orte, Aufgabenbezeichnungen oder Koordinaten. Sie öffnet Datum und To-do; der Server prüft die Sitzung erneut. Zustellung ist Best Effort. Vorlauf-/Losgeh-Ereignisse sind pro Planversion eindeutig; Wiederholungen nach Netzwerkfehler können providerseitig trotzdem doppelt eintreffen.

## iPhone und Android

Im `frontend/`:

```sh
npm ci
npm run native:sync
npm run native:ios
# oder
npm run native:android
```

`CRONICL_API_ORIGIN` kann beim Sync den fest konfigurierten HTTPS-Origin überschreiben. Standard ist der bestätigte öffentliche Cronicl-Host. Keine Server-URL als ferngesteuerte WebView verwenden; das Bundle liegt lokal in den nativen Projekten. Jede Änderung an Webcode benötigt für die mobile App einen neuen Build/Sync und eine neue installierte Version.

Android ab API 26: Android Studio, SDK 36 und zur Gradle-/Capacitor-Version passende JDK-Installation. `android/app/google-services.json` aus dem passenden Firebase-Projekt ist lokal erforderlich für Push und absichtlich gitignoriert. Release-Key und Signing-Konfiguration extern verwalten. Der Standortdienst startet nur aus der sichtbaren App, zeigt eine permanente Systemmeldung und besitzt einen Beenden-Button. Kein Boot-Receiver und kein versprochener automatischer Neustart nach Force-stop.

iOS ab 15: macOS/Xcode und passendes Apple Developer Team wählen. Bundle-ID und APNs-Topic abgleichen. Signing & Capabilities: Push Notifications und Background Modes/Location Updates. Debug-Entitlement nutzt `development`, Release `production`. Standortrechte sind zweckgebunden beschrieben. Das eigene native Modul ist über `CroniclViewController` registriert; `SceneDelegate` muss diesen Controller verwenden. Systembrowser-Login kehrt über `cronicl://auth-complete` zurück; die URI enthält kein Sitzungstoken. Die Einlösung erfordert zusätzlich den geheimen Challenge-Verifier aus der gestarteten App.

Die Website kann einen festen bestätigten Startort überwachen. Aktuelle Hintergrundpositionen benötigen die native App. Pro Gerät läuft eine bewusst gestartete, zeitlich begrenzte Begleitung. Serverprüfung startet im konfigurierten Vorlauf auch ohne aktiven Standortdienst. Das Telefon wird zum Starten über die Vorlauf-Benachrichtigung zur App geführt; automatischer GPS-Start bei geschlossener App ist nicht zugesagt.

## Abnahme

Automatisch:

- `backend`: `pytest -q`; mit `APP_INTEGRATION_DATABASE=1` ausschließlich auf einer isolierten migrierten Testdatenbank. Der OpenAPI-Snapshot wird deterministisch mit `python scripts/update_openapi.py` erzeugt, ohne `.env` zu laden.
- `frontend`: `npm run check`, `npm run lint:design`, `npm run build`, `npm run build:mobile`, `npx cap sync`.
- Browser: lokalen Vite-Server auf Port 4179 starten und `node scripts/test-travel-ui.mjs` ausführen. Alle API-Daten sind synthetisch; keine echten Google-/Haushaltsdaten werden verwendet.

Noch gesondert auf physischen Geräten zu prüfen:

| Fall | Erwartung |
| --- | --- |
| Login, Prozessneustart, Logout | Geschützte Sitzung bleibt verfügbar beziehungsweise wird widerrufen; kein Token in Web Storage |
| Begleitung, Bildschirm 30–60 Minuten gesperrt | Native Fixes treffen mit echter Messzeit ein; Akkuverbrauch protokollieren |
| Rechte verweigert/entzogen, ungenauer Standort | Kein Live-Versprechen; bestätigter Startort und Status bleiben verständlich |
| Flugmodus und Rückkehr | Kein Bewegungsarchiv und kein Nachsenden alter Fixes |
| Force-stop, Reboot, Energiesparen | Tatsächliche Plattformgrenzen protokollieren; UI zeigt fehlende Aktualität |
| Termin geändert/erledigt/gelöscht, Uhrzeit-/Zeitzonenwechsel | Alter Plan sendet keine neue Benachrichtigung; Fix-Upload wird abgelehnt |
| Push online/offline/verspätet, App geschlossen | Aktuelles autorisiertes To-do öffnen, keine gespeicherte alte Route als aktuellen Zustand darstellen |
| Zwei Konten und zwei Geräte | Keine fremde Position, Sitzung, Überwachung oder Benachrichtigung sichtbar |

Diese Gerätefälle wurden nicht durch einen Web-Build oder Emulator ersetzt. Lokale Umgebung bietet derzeit keine Xcode-/Android-SDK-Toolchain und keine verbundenen Telefone. Store-Verteilung ist erst nach Signing und dieser Abnahme freigabefähig.

## Deployment und Rollback

1. Laufende API-/Web-Image-IDs festhalten und vor der Migration ein PostgreSQL-Backup mit eingeschränkten Dateirechten außerhalb Git erstellen.
2. `docker compose build api web travel-worker`, anschließend `docker compose run --rm --no-deps api alembic upgrade head`.
3. `docker compose up -d --no-deps api web travel-worker`.
4. Health, anonymen Zugriffsschutz, Migration und Worker prüfen. Bei nicht eingerichteten Push-Credentials keine Push-Zustellung als erfolgreich melden.
5. Rollback: Worker stoppen und API/Web auf die zuvor aufgezeichneten Images zurücksetzen. Die additive neue Migration darf zunächst bestehen bleiben; alte Codeversionen ignorieren die neuen Tabellen. Kein Produktions-Downgrade und keine Wiederherstellung/Löschung produktiver Daten ohne konkrete Notwendigkeit und gesonderte Prüfung.
