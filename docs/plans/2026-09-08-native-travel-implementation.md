# Native Anreisebegleitung: Umsetzungsplan

Status: in Arbeit. Owner/alleiniger Schreiber: Hauptagent. Auftrag: vollständige Umsetzung vom 08.09.2026; iPhone und Android, Vorlauf vor Abfahrt, bestehendes To-do-Highlight.

## Pakete und Abnahme

- [x] P1 – separate Spezifikationsrevision: native Anreise und Auth-Vertrauen, Interaktionsvertrag, Registry. Governing: bestätigte Nutzerentscheidung und bisherige Specs. Domain: Dokumentation. Abnahme: explizite Regeln und Testzuordnung.
- [ ] P2 – private native Sitzungen, Login-Übergabe und Datenmodell. Domain: Auth/Modelle/Alembic, serialisiert. Abnahme: Replay/Expiry/Widerruf, A/B-Isolation, ein Migrationskopf und leere DB.
- [ ] P3 – Travel-Service, persistente Überwachung und Push-Outbox. Domain: Backend Travel. Abnahme: Zukunftsprognose, Zeitfenster, Freshness, Cancellation, Wiederholung und Anbieterfehler in Tests.
- [ ] P4 – Capacitor iOS/Android, sicherer nativer Transport und Standortbegleitung. Domain: native Projekte und Frontend-Transport. Abnahme: statisches Bundle, native Konfiguration, Build soweit Toolchains vorhanden; Geräteprüfungen separat ausweisen.
- [ ] P5 – vorhandenes To-do-Highlight und Detail integrieren. Domain: Tages-UI. Abnahme: Zustände, Start/Pause, Push-Einstieg, Tastatur/Touch, Svelte/Design/Build.
- [ ] P6 – OpenAPI, Regression, Migration, Betriebs-/Geräteanleitung. Domain: Verifikation/Vertrag, serialisiert. Abnahme: Tests und genaue verbleibende externe Voraussetzungen.
- [ ] P7 – vom Nutzer zusätzlich beauftragter Commit und Server-Deployment. Domain: Git/Deployment. Vorher Images für Rollback festhalten, additive Migration anwenden, API/Web/Worker starten, Health und reale geschützte Routen prüfen. Keine Datenlöschung oder Entfernung des bestehenden DB-Volumes. Native Store-Auslieferung braucht Signierung und Geräteabnahme.

In Scope: `backend/`, `frontend/`, relevante `docs/`, isolierte Worker-Konfiguration. Out: ESP und Gesundheitslogik. Server-Deployment ist durch den ergänzenden Nutzerauftrag autorisiert; keine Änderung geheimer Produktionswerte. Erlaubte Seiteneffekte: lokale Dateien, Abhängigkeiten und isolierte Testdatenbanken. Keine echten Pushs oder Google-API-Aufrufe in Tests. Stop bei unauflösbaren Spec-Konflikten oder fehlenden externen Signierungs-/Geräteberechtigungen; unabhängige Implementierung weiterführen. Keine Behauptung einer erfolgreichen iOS-/Android-Geräteabnahme ohne Hardware/Toolchain.

## Verlauf

- Bestehendes Repository zu Beginn sauber bis auf das eigene Recherche-Dokument. Nutzerbestätigung autorisiert die getrennte Spec-Revision und anschließende Umsetzung.

## Verifikationsstand 2026-09-08

- P2/P3: implementiert; isolierte PostgreSQL-Regression einschließlich nativer Kontoisolation, Replay/Widerruf, Fix-Gültigkeit, Prognose, Job-Deduplizierung und Push-Payload: 80 Tests bestanden. Migration auf leerer DB und Upgrade/Downgrade/Upgrade geprüft.
- P4: iOS-/Android-Projekte, eigener nativer Transport und Standortdienst, bestehende Markenassets integriert. Web-Bundle und Capacitor-Sync erfolgreich. Native Compiler-/Geräteabnahme weiterhin offen, keine signierten Installationsdateien erzeugt.
- P5: bestehendes Highlight und Detail erweitert; Browserregression prüft genau ein Highlight, Tastatureinstieg, Escape/Fokusrückgabe, Stop und bestätigten Startort auf 390px ohne Überlauf. Svelte: 0 Fehler, 5 bestehende CSS-Warnungen; Designprüfung bestanden.
- P6: OpenAPI aktualisiert; Betriebsanleitung in `docs/runbooks/native-travel.md`. End-to-end APNs/FCM und Geräte-Lifecycle noch extern zu prüfen.
- Rollback vor Deployment: API `sha256:3f493b2ec84991ab6b4ab16c6d95ef26c7f5bb5d8328e7be2ed7f5293c76eb3d`, Web `sha256:f3e08767d8366e3113c8fef4a3ad35675bf6d390b468b5e51a1050a5eb9ee16f`. Geschütztes Backup außerhalb Git unter `/tmp/cronicl-before-native-20260908.dump` (0600).

Die offenen Kontrollkästchen bleiben bis zur vollständigen Paketabnahme offen; implementierter Quellcode allein ersetzt keine native Geräteprüfung.
