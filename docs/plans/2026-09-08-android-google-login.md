# Android Google-Login v2: Umsetzung und Abnahme

Aktueller Stand 2026-09-10: Backend/Web/Worker produktiv ausgeliefert, Migration
und Login-Konfiguration geprüft. Android-APK gebaut; echte Google-Geräteanmeldung
und Google-Konsoleneintrag noch nicht durch den Nutzer bestätigt.

Owner/alleiniger Schreiber: Hauptagent. Auftrag: Nutzerfreigabe zur Umsetzung von
Google Credential Manager am 2026-09-08. Governing:
`../specs/android-google-sign-in.md`, ergänzend Konto- und Native-Travel-Spezifikation.

Ziel: Google-Kontoauswahl im Android-Modul, geprüfte einmalige Backend-Einlösung,
private widerrufbare Sitzung und verständliche Login-Zustände. Konfliktdomain:
Authentifizierung einschließlich serialisierter Migration/API/Bridge-Verbraucher.
In Scope: Auth-Service/-Routen, native Sitzungsmodelle, eine Alembic-Revision,
Worker-Versionsprüfung, Android-Modul, gemeinsame Login-UI, korrekte Anzeige der
Google-Datenfreigabe, Tests/OpenAPI und Dokumentation. iOS erhält ausschließlich eine
Sperre der neuen Login-Routen im generischen Transport; das ist kein iOS-Login.
Out of Scope: Kalender-Autorisierungsimplementierung, ESP/BIA, Deployment,
Google-Konsolenänderungen, Release-Signierung und Store-Auslieferung. Der ergänzende
Nutzerauftrag autorisiert die lokale SDK-Installation mit Lizenzannahme und die
Debug-APK-Erstellung; eine Produktionsfreigabe wurde separat angefragt.

Erlaubte Seiteneffekte: lokale Dateien, Abhängigkeiten/Builds, isolierte synthetische
PostgreSQL-Testdaten. Keine produktiven Einstellungen, Geheimnisse oder echten
Google-/Push-Nutzdaten. Stop bei neuen Produktentscheidungen, widersprüchlichen
Specs oder fehlenden externen Google-/SDK-/Geräteberechtigungen. Unabhängige Arbeit
läuft weiter. Abnahme: v2 Proof/Replay/Account-Isolation/Widerruf, dauerhafte
v1-Invalidierung, Migration auf leerer und v1-Testdatenbank, OpenAPI,
Frontend check/design/build/mobile, Login-/Travel-Browserregression, Android-Build.
Echte Google-Geräteabnahme bleibt separat ausgewiesen.

## Umsetzung

- Separate freigegebene Spezifikationsrevision vor Implementierung erstellt.
- Android: Credential Manager 1.6.0 und googleid 1.2.0, Button-Flow mit Nonce,
  Verifier ausschließlich im Modul, verschlüsselte Sitzung im Android Keystore.
  Generische Bridge darf keine Google-Login-Routen abrufen; veralteter Android
  Deep Link entfernt. Abbruch/Logout beendet die laufende Anmeldung, neue Anmeldung
  verwirft vorherige lokale Sitzung; Providerstatus wird beim Logout gelöscht.
- Backend: explizite Google-Native-Client-ID, Nonce-Hash und Verifier, echte
  Signatur-/audience-/issuer-/Ablaufprüfung, Freigabeliste/verifizierte E-Mail,
  transaktionale Einlösung und sichere Konkurrenz bei erstmaliger Kontoanlage.
  Google-Integrationstokens werden bei nativer Anmeldung nicht angefasst.
- Persistente Protokollversion 2 und `crn2_` schließen v1 auch nach Codeänderungen aus.
  Migration `b60908c002` widerruft v1, entfernt Geräte-Pushs und alte Standorte;
  normale To-dos bleiben erhalten. Ein Downgrade reaktiviert keine Sitzung.
- UI: Doppelklickschutz, Abbruch ohne Fehler, verständliche Wiederholung,
  serverseitige Sitzungsprüfung vor Navigation, Onboarding oder Tagesansicht.
  Integrationen zeigen echten Google-Datenzugriff statt bloßen Loginstatus.

## Verifikation

- Backend: **99 Tests und 19 Subtests bestanden**, keine übersprungenen Tests,
  mit `APP_IGNORE_DOTENV=1`, `APP_NAME=Cronicl`, `APP_INTEGRATION_DATABASE=1`
  auf einer isolierten PostgreSQL-16-Instanz. Signaturen wurden zusätzlich mit
  lokal erzeugten Testschlüsseln tatsächlich verifiziert; kein Google-Netzwerkzugriff.
  Nach zusätzlicher v1-Versionsprüfung: gezielt 8 Tests und 11 Subtests bestanden.
- Migration: `scripts/verify_native_auth_migration.py` auf einer eigenen leeren
  Datenbank erfolgreich. Vorher v1-Datensätze angelegt, Upgrade, dauerhafte
  Invalidierung, Erhalt des To-dos, Downgrade/Upgrade und einzelner Head
  `b60908c002` verifiziert.
- Frontend: check (0 Fehler, 5 bestehende CSS-Warnungen), Designprüfung,
  Web-Build, Mobile-Build und `cap sync android` erfolgreich.
- Login-Browserregression: synthetische Android-Bridge, Tastatur/Touch,
  Doppelklickschutz, Abbruch/Fokusrückgabe, Ablehnung, Wiederholung, serverseitig
  bestätigtes Onboarding/Tagesansicht, korrekte Integrationsanzeige und iOS-Sperre.
  Bestehende Travel-Browserregression ebenfalls erfolgreich.
- Android SDK unter `/opt/android-sdk` installiert, Lizenzannahme durch den
  ergänzenden Nutzerauftrag autorisiert. Java 21, Plattform 36, Build Tools 35/36.
  Gradle 8.14.3: **BUILD SUCCESSFUL**, 183 Tasks. `:app:assembleDebug`,
  `:app:testDebugUnitTest`, `:app:assembleDebugAndroidTest`, `:app:signingReport`
  erfolgreich. Der vorhandene lokale Android-Test ist nur ein Template-Smoke-Test;
  die Geräte-Instrumentierung wurde kompiliert, mangels Gerät nicht ausgeführt.
- Debug-APK: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`, ca. 7 MiB,
  Paket `app.cronicl.mobile`, Version 1.0/1, minSdk 26, targetSdk 36.
  `apksigner verify --verbose --print-certs`: gültige APK-v2-Signatur.
  Datei-SHA-256: `b96172ab3a4b751f69ced087e5384c548dc3443e9d15a67719a81ec3f61dbbe3`.
  `adb devices` meldet keine verbundenen Geräte. Kein echter Google-Login behauptet.
- `git diff --check` erfolgreich. Kein Commit, Deployment oder produktiver
  Konfigurationswechsel durchgeführt.
- Auslieferungsimages lokal vorbereitet (2026-09-09):
  `cronicl-google-v2-api:20260909` mit Image-ID
  `sha256:4fd190be2b2149283e4d26da62f05a5105774a1c3f314ce0d7e72cd0c6061198`,
  `cronicl-google-v2-web:20260909` mit Image-ID
  `sha256:8fa86276bc2609214b06df93cd5b14ce1e546d850f265c3507fa9584558ef975`.
  Isolierter API-Image-Smoke-Test ohne Netzwerk: Health 200, private Route 401,
  fehlende Native-Konfiguration 503, v1-Login 503. Web-Image startet und liefert
  `/login` mit HTTP 200. Keine laufenden Produktionscontainer ersetzt.

Offen: ausdrücklich freigegebene Produktionsauslieferung, Google-Projektregistrierung
(Paket/Signatur und `GOOGLE_NATIVE_CLIENT_ID`), echte Geräteanmeldung/Neustart/Logout,
separate Push-Abnahme. Die native Geräteanmeldung ist durch synthetische
Bridge-/Providerprüfungen nicht bestätigt.

## Revalidierung

Auth-/Protokoll-/Schema-/Worker-/Login-Touchpoints wurden ausgelöst.
Die Android-Spezifikation ersetzt den früheren Android-Browser-Handoff explizit.
Kontoisolation, private Travel-Grenzen und das bestehende Interaktionslayout bleiben
verbindlich; OpenAPI und Tests werden gemeinsam aktualisiert. Alte 503-Routen
bleiben ausschließlich als explizite Ablehnung für v1-Clients, mit der in der
Spezifikation definierten Entfernungsvoraussetzung.

Ergebnis: Android-Protokollentscheidung, Kontogrenzen und Native-Travel-Vertrag
**confirmed** durch Code-/Testabgleich für die hier ausführbaren Checks;
Android-Build bestätigt, externe Geräteabnahme ausdrücklich offen. Der Android-v1-Handoff
ist **superseded** durch die neue Spezifikation. Keine globale native Login-Sperre
mehr als aktuelle v2-Beschreibung führen; iOS/v1 bleiben abgewiesen.

## Konkrete Google- und Installationsübergabe (2026-09-09)

Die folgenden IDs sind öffentliche Registrierungsdaten, keine Geheimnisse.
Die Web-Client-ID wurde über die öffentliche Google-Anmeldeweiterleitung ermittelt,
keine `.env` oder Produktionsgeheimnisse gelesen.

| Eintrag | Wert |
| --- | --- |
| Google-Web-Client-ID / Backend-Audience | `781843769391-2ltgr9efv8ji9tjkr80sidg2sjpc6tn3.apps.googleusercontent.com` |
| Android-Paketname | `app.cronicl.mobile` |
| SHA-1 des Zertifikats dieser Debug-APK | `EE:A0:48:B7:16:0F:7B:BE:A5:ED:6D:36:5D:C3:C8:F2:06:6D:08:05` |
| SHA-256 des Zertifikats | `F3:64:FD:F5:CE:29:91:7F:9B:57:AC:A7:B7:43:D3:82:15:5F:80:8D:03:C0:39:D6:5E:9F:77:5C:7E:E1:17:5A` |
| Eingebauter API-Origin | `https://cronicl.49.12.225.84.sslip.io` |

Im **gleichen Google-Projekt wie die Web-Client-ID** unter Google Auth Platform →
Clients einen Android-Client mit Paketname und SHA-1 oben registrieren. Der neue
Android-Client besitzt eine eigene ID; im Backend bleibt die Web-Client-ID als
Audience. Für einen später anders signierten Release ist dessen Fingerabdruck
zusätzlich zu registrieren. Der Debug-Schlüssel bleibt außerhalb Git und wird
nicht als Release-Schlüssel verwendet.

Auf einem Rechner mit angeschlossenem Android-Gerät:

```sh
adb install -r app-debug.apk
adb shell am start -n app.cronicl.mobile/.MainActivity
```

Die APK ist gebaut und signiert. Erfolgreiche Anmeldung setzt zusätzlich das
v2-Backend mit expliziter `GOOGLE_NATIVE_CLIENT_ID` und die Google-Registrierung
voraus. Die Werte sind vorbereitet; eine tatsächliche Google-Konsolenänderung
ist damit nicht behauptet. Die Produktionskonfiguration wurde am 2026-09-10
mit der unten dokumentierten Freigabe angewendet.

## Produktionsauslieferung 2026-09-10

Expliziter Nutzerauftrag: „deployment freigegeben“. Dieser Zusatz erweitert den
vorherigen lokalen Scope um Produktionskonfiguration, Migration und Auslieferung
der geprüften API-/Web-/Worker-Images. Eine Google-Konsolenänderung ist mangels
Zugriff weiterhin nicht erfolgt. Owning domain: Deployment, alleiniger Hauptagent.

- Vorheriger Schema-Head `a60908c001`; Backup unter
  `/root/.local/share/cronicl/deployments/20260910-google-v2/before.dump`, Modus 0600,
  Verzeichnis 0700, Archivindex mit `pg_restore --list` geprüft.
- Alte Images unter `cronicl-before-google-v2-{api,web,travel-worker}:20260910`
  gesichert; exakte IDs in `previous-images.json` im selben privaten Verzeichnis.
  Die vorherige API hatte den v1-Login bereits gesperrt.
- API/Worker während der Migration gestoppt. `alembic upgrade head` erfolgreich,
  aktueller Head **`b60908c002`**. Kein DB-Volume ersetzt oder normales To-do gelöscht.
- API und Worker laufen mit Image
  `sha256:4fd190be2b2149283e4d26da62f05a5105774a1c3f314ce0d7e72cd0c6061198`,
  Web mit `sha256:8fa86276bc2609214b06df93cd5b14ce1e546d850f265c3507fa9584558ef975`.
- Native Google-Audience entspricht der oben dokumentierten Web-Client-ID.
  Dauerhafte, öffentliche Standortkonfiguration in der gitignorierten lokalen
  `docker-compose.override.yml`; keine `.env` gelesen oder geändert. Compose wurde
  mit einer privaten temporären Kopie der bereits laufenden Containerkonfiguration
  ausgeführt. Diese temporäre Kopie wurde nach erfolgreicher Auslieferung entfernt.
- Öffentliche Checks: `/api/health` 200, `/login` 200, anonyme `/api/todos` 401,
  `/api/native/google/start` 200 mit erwarteter Audience und `Cache-Control: no-store`,
  alter `/api/native/login` 503. Der synthetische unzugeordnete Login-Testauftrag
  läuft nach fünf Minuten ab; kein Google-Nutzer oder Google-Provider wurde genutzt.
- Alle drei Container laufen; keine ERROR-/Traceback-Zeilen im Startzeitraum.

Noch offen ist ausschließlich die externe Abnahme: Android-OAuth-Client mit dem
Debug-Zertifikat registrieren/bestätigen und die APK auf einem physischen Telefon
mit einem freigegebenen Google-Konto testen; Push gesondert konfigurieren/abnehmen.
Ein erfolgreicher Server-Login-Start ist kein Nachweis einer echten Google-Anmeldung.
