# Native Anreisebegleitung: Umsetzungsplan

Aktueller Android-Nachfolger: [Google-Login v2](2026-09-08-android-google-login.md).
Die nachstehende globale Login-Sperre dokumentiert den Zwischenstand vor v2;
v1 und iOS bleiben gesperrt.

Status: ursprüngliche Implementierung und Serverauslieferung abgeschlossen; native Anmeldung im aktuellen Quellstand aus Sicherheitsgründen gesperrt. Native Release-Abnahme blockiert, siehe Nacharbeit unten. Owner/alleiniger Schreiber: Hauptagent. Auftrag: vollständige Umsetzung vom 08.09.2026; iPhone und Android, Vorlauf vor Abfahrt, bestehendes To-do-Highlight.

## Nacharbeit: native Login-Absicherung (2026-09-08)

Auftrag: vorhandene vorläufige Login-Sperre vervollständigen und verifizieren.
Governing: `native-travel-companion.md` und
`multi-account-scale-and-body-composition.md`. Einziger Schreiber und Konfliktdomain:
Hauptagent / Authentifizierung einschließlich ihrer Worker-Verbraucher.
In Scope: native Auth-Routen/-Service, Worker-Sitzungsprüfung, zugehörige Tests,
OpenAPI-Antwortdokumentation und Betriebs-/Verifikationsstand. Out of Scope: neues
Login-Protokoll, mobile Clients, ESP/Gesundheitslogik und Produktionsänderungen.
Erlaubte Seiteneffekte: lokale Dateien, Builds und eine eigens erzeugte temporäre
PostgreSQL-Instanz mit synthetischen Daten. Stop bei erforderlicher neuer
Produktentscheidung oder widersprüchlichen autoritativen Vorgaben.

Abnahme: native Anmeldung und bestehende Bearer-Zugänge gesperrt; keine native
Hintergrundberechnung oder Push-Zustellung trotz Sperre; Browser-Login, Kontotrennung
und feste browserbasierte Anreisen funktionieren; Backend-Suite, OpenAPI-Snapshot
und Frontend-Checks erfolgreich. Die Sperre ersetzt keine sichere native Anmeldung.

Artifact-Revalidierung (Auth-/Identitäts- und Worker-Touchpoint):

- Konto-Spezifikation: **confirmed** für die Absicherung der Kontogrenze; Nachweis
  durch Tests gespeicherter nativer Sitzungen und Browser-A/B-Isolation.
- Native-Spezifikation: **revise** für das Ersatz-Login-Protokoll. Die gewünschte
  native Kontositzung bleibt Produktziel, ist mit der Sperre aber nicht verfügbar.
  Die freigegebene Spezifikation wird hier nicht an das defekte Protokoll angepasst;
  vor dessen Ersatz ist eine getrennte Spezifikationsrevision erforderlich.
- OpenAPI: neue `503`-Antworten der vier Login-/OAuth-Operationen dokumentiert;
  Snapshot wird zusammen mit den Routen verifiziert.
- Betriebsanleitung: aktuelle Sperre und Ablösebedingung ergänzt. Die früheren
  Paketmarkierungen und Deployment-Angaben unten beschreiben die ursprüngliche
  Auslieferung, keine aktuelle mobile Sicherheitsfreigabe.

Verifikation dieser Nacharbeit:

- Backend: **90 Tests und 11 Subtests bestanden**, keine übersprungenen Tests,
  mit `APP_IGNORE_DOTENV=1`, `APP_NAME=Cronicl`, `APP_INTEGRATION_DATABASE=1` und
  `DATABASE_URL` auf eine eigens erzeugte lokale PostgreSQL-16-Instanz.
  Enthalten: `test_native_auth_containment.py`, Browser-A/B-Isolation,
  bisherige Native-/Travel-Regression und OpenAPI-Snapshot-Abgleich.
- Leere Testdatenbank mit Alembic bis `a60908c001 (head)` migriert; ein Kopf.
  Keine Schemaänderung in diesem Arbeitspaket.
- Frontend: `npm run check`, `npm run lint:design`, `npm run build` erfolgreich;
  bestehende CSS-Warnungen bleiben bestehen.
- `git diff --check` erfolgreich. Keine Provideraufrufe oder Pushs mit echten
  Konten, keine Produktionskonfiguration geladen. Kein Deployment dieser Nacharbeit.

## Pakete und Abnahme

- [x] P1 – separate Spezifikationsrevision: native Anreise und Auth-Vertrauen, Interaktionsvertrag, Registry. Governing: bestätigte Nutzerentscheidung und bisherige Specs. Domain: Dokumentation. Abnahme: explizite Regeln und Testzuordnung.
- [x] P2 – private native Sitzungen, Login-Übergabe und Datenmodell. Domain: Auth/Modelle/Alembic, serialisiert. Abnahme: Replay/Expiry/Widerruf, A/B-Isolation, ein Migrationskopf und leere DB.
- [x] P3 – Travel-Service, persistente Überwachung und Push-Outbox. Domain: Backend Travel. Abnahme: Zukunftsprognose, Zeitfenster, Freshness, Cancellation, Wiederholung und Anbieterfehler in Tests.
- [x] P4 – Capacitor iOS/Android, sicherer nativer Transport und Standortbegleitung. Domain: native Projekte und Frontend-Transport. Abnahme: statisches Bundle, native Konfiguration, Build soweit Toolchains vorhanden; Geräteprüfungen separat ausweisen.
- [x] P5 – vorhandenes To-do-Highlight und Detail integrieren. Domain: Tages-UI. Abnahme: Zustände, Start/Pause, Push-Einstieg, Tastatur/Touch, Svelte/Design/Build.
- [x] P6 – OpenAPI, Regression, Migration, Betriebs-/Geräteanleitung. Domain: Verifikation/Vertrag, serialisiert. Abnahme: Tests und genaue verbleibende externe Voraussetzungen.
- [x] P7 – vom Nutzer zusätzlich beauftragter Commit und Server-Deployment. Domain: Git/Deployment. Vorher Images für Rollback festhalten, additive Migration anwenden, API/Web/Worker starten, Health und reale geschützte Routen prüfen. Keine Datenlöschung oder Entfernung des bestehenden DB-Volumes. Native Store-Auslieferung braucht Signierung und Geräteabnahme.

In Scope: `backend/`, `frontend/`, relevante `docs/`, isolierte Worker-Konfiguration. Out: ESP und Gesundheitslogik. Server-Deployment ist durch den ergänzenden Nutzerauftrag autorisiert; keine Änderung geheimer Produktionswerte. Erlaubte Seiteneffekte: lokale Dateien, Abhängigkeiten und isolierte Testdatenbanken. Keine echten Pushs oder Google-API-Aufrufe in Tests. Stop bei unauflösbaren Spec-Konflikten oder fehlenden externen Signierungs-/Geräteberechtigungen; unabhängige Implementierung weiterführen. Keine Behauptung einer erfolgreichen iOS-/Android-Geräteabnahme ohne Hardware/Toolchain.

## Verlauf

- Bestehendes Repository zu Beginn sauber bis auf das eigene Recherche-Dokument. Nutzerbestätigung autorisiert die getrennte Spec-Revision und anschließende Umsetzung.

## Verifikationsstand 2026-09-08

- P2/P3: implementiert; isolierte PostgreSQL-Regression einschließlich nativer Kontoisolation, Replay/Widerruf, Fix-Gültigkeit, Prognose, Job-Deduplizierung und Push-Payload: 82 Tests bestanden. Migration auf leerer DB und Upgrade/Downgrade/Upgrade geprüft.
- P4: iOS-/Android-Projekte, eigener nativer Transport und Standortdienst, bestehende Markenassets integriert. Web-Bundle und Capacitor-Sync erfolgreich. Native Compiler-/Geräteabnahme weiterhin offen, keine signierten Installationsdateien erzeugt.
- P5: bestehendes Highlight und Detail erweitert; Browserregression prüft genau ein Highlight, Tastatureinstieg, Escape/Fokusrückgabe, Stop und bestätigten Startort auf 390px ohne Überlauf. Svelte: 0 Fehler, 5 bestehende CSS-Warnungen; Designprüfung bestanden.
- P6: OpenAPI aktualisiert; Betriebsanleitung in `docs/runbooks/native-travel.md`. End-to-end APNs/FCM und Geräte-Lifecycle noch extern zu prüfen.
- Rollback vor Deployment: API `sha256:3f493b2ec84991ab6b4ab16c6d95ef26c7f5bb5d8328e7be2ed7f5293c76eb3d`, Web `sha256:f3e08767d8366e3113c8fef4a3ad35675bf6d390b468b5e51a1050a5eb9ee16f`. Geschütztes Backup außerhalb Git unter `/tmp/cronicl-before-native-20260908.dump` (0600).

Die Paketmarkierungen dokumentieren die abgeschlossene Implementierung und die hier ausführbare Verifikation. Sie sind keine Freigabe signierter mobiler Releases. Die folgenden externen Abnahmen bleiben ausdrücklich offen:

- [ ] Android mit JDK/SDK kompilieren und auf einem physischen Telefon installieren.
- [ ] iOS mit Xcode und Apple-Team signieren, kompilieren und auf einem iPhone installieren.
- [ ] APNs/FCM für die tatsächlichen Bundle-/Projektkennungen einrichten und Zustellung samt Einstieg bei geschlossener App prüfen.
- [ ] Gerätefälle aus dem Runbook (gesperrter Bildschirm, Rechteentzug, Flugmodus, Force-stop, Konto-/Gerätewechsel) protokollieren.

In dieser Linux-Umgebung fehlen Java/Android SDK, Xcode und verbundene Telefone; APNs/FCM sind produktiv nicht konfiguriert. Es wurden keine SDK-Lizenzen, Store-Verträge oder Signierungsberechtigungen stellvertretend angenommen. Die automatischen Tests belegen zusätzlich abgelaufene Login-Übergaben/Sitzungen, maximal drei Push-Versuche mit Backoff und das Verwerfen abgelaufener Nachrichten.

### Server-Deployment

Commit `18df08b` wurde am 2026-09-08 deployt. Produktionsschema `a60908c001 (head)`; API, Web und travel-worker laufen. Öffentlicher Health-Endpunkt liefert `200`/`status=ok`, Website `200`, anonymer `/api/travel`-Zugriff `401`. Ein expliziter Worker-Tick im Container war erfolgreich. Maps ist konfiguriert; Push ist deaktiviert, APNs-/FCM-Konfiguration fehlt. Damit ist die Serverauslieferung bestätigt, nicht die Zustellung an physische Telefone.
