# Einheitliche Eingabe: Umsetzung und Abnahme

Status: in Arbeit. Autorisiert durch den Umsetzungsauftrag vom 10.09.2026.

## Arbeitspaket

Ziel: Das nach Session-Abgleich korrigierte Konzept vollständig umsetzen: kompakte gemeinsame Eingabe, lokale Schnellerkennung, ausdrücklich gestarteter KI-Chat mit bearbeitbaren und ausführbaren Vorschlägen, vollständige manuelle Fachbearbeitung.

Governing artifact: `docs/specs/unified-entry-and-assistant.md`. Es revidiert die ausdrücklich benannten Eingabeverträge. Owning conflict domain: unified-entry; ein schreibender Agent. API/Typen/OpenAPI werden seriell aktualisiert. Vorhandene Änderungen an nativer Anmeldung/Anreise bleiben erhalten.

In scope: Frontend-Eingabe, Fachdialoge und betroffene Einstellungen; Backend-Assistent und Validierung; bestehender interner KI-Proxy; gezielte Regressionen; Vertrags- und Abnahmedokumentation. Out of scope: Deployment, Signierung, Produktion, Firmware, Authentifizierungsumbau, freie Kontozuweisung, manuelle synthetische BIA-Werte. Export/Löschung und Waagenbereich-Einrichtung sind gesonderte Produktfragen, keine Voraussetzungen der Eingabe. Zulässige Seiteneffekte: lokale Dateien, Builds und synthetische Testdaten. Stopbedingungen: nicht auflösbarer Berechtigungskonflikt oder notwendige nicht autorisierte Produktentscheidung; unabhängige Arbeiten fortsetzen.

## Reihenfolge

1. [ ] Korrigierten Interaktionsvertrag und Feldumfang verbindlich festhalten.
2. [ ] Lokale Datums-/Zeit-/Routine-Erkennung; direkte Anlage, gemeinsame Eingabe und erreichbare vollständige To-do-Details.
3. [ ] Fachliche Eingabelücken schließen: Mahlzeiten/Mengen/Status, Rezepte/Pläne/Kategorien, Routinen, Bereiche, Training und Anreisepuffer.
4. [ ] KI-Chat: Gespräch, strukturierte Vorschläge, manuelle Korrektur, Ausführen, Kontext und verständliche Fehler.
5. [ ] Mehrteilige Ernährungs-/Trainingsvorschläge mit Abhängigkeiten und nachvollziehbarer Übernahme.
6. [ ] Backend-/Isolationstests, Browserabnahme mobil/Desktop, Frontend-Gates und Vertragsprüfung.
7. [ ] Abschlussaudit gegen jede unten stehende Anforderung; kein Abschluss allein aufgrund grüner Buildchecks.

## Verbindliche Abnahmekriterien

| ID | Kriterium | Erforderlicher Nachweis |
| --- | --- | --- |
| A1 | Titel + Enter legt genau ein Tages-To-do an, ohne Dialog oder KI-Aufruf | Browserregression mit Request-/Dialogprüfung |
| A2 | Eindeutige deutsche Datums-/Zeitangaben und wöchentliche Routinen funktionieren lokal; Mehrdeutigkeit wird nicht erfunden | Parserfälle inklusive Referenztag/Grenzen und Browserflow |
| A3 | Notizen/Einkauf nutzen das Footerfeld; explizit geöffneter Notizbereich ist Anlageziel; kein Tastatur-Autofokus beim Öffnen | Mobile Browserregression, sichtbares Ziel, Servermitgliedschaftstest |
| A4 | Vollständiger To-do-Editor erreichbar: Termin, Priorität, Bereich/Zuweisung, Ziel entfernen/bestätigen, Modus/Puffer | Browserflow speichern/erneut öffnen; Private-/Space-Grenze |
| A5 | Mahlzeit ohne Plan und zweiter Eintrag derselben Kategorie möglich; 150 g/1,5 Portionen, mehrere Komponenten, Zeitpunkt, skip und Korrektur | Browserflow und serverseitige Snapshot-/Berechnungstests |
| A6 | Rezeptname/Ertrag/Zutaten/Unterrezepte, Kategoriename, Planzeit/freier Platzhalter manuell pflegbar | Browserregression, gespeicherte Payloads und neue Serverantwort |
| A7 | Bestehende Routinen und Bereichsnamen editierbar; RIR 0 erhalten; Zielwerte beschriftet/validiert; Vorlauf 15–180 | Gezielte Browser-/Verhaltenstests |
| A8 | Einkaufsimport bestätigt exakt den sichtbaren Zeitraum; laufende/veraltete Vorschau nicht übernehmbar | Verzögerte Browserantworten und Zeitraumwechsel |
| A9 | KI ausschließlich nach ausdrücklicher Aktion; Chat hält Gespräch, bietet ausführbare bearbeitbare Vorschläge statt nur Text | Synthetische Providerantworten + Browserflow; kein Modellaufruf bei Plus |
| A10 | To-do, Notiz, Einkauf, Routine, Lebensmittel, Rezept, Mahlzeit, Ernährungsplan, Trainingseinheit/-planung erstellen; bestehende Inhalte gezielt ändern | Typweise Server-/Clientverifikation und repräsentative Browserabläufe |
| A11 | Mehrteiliger Plan zeigt Ziele/Abhängigkeiten; Übernahme meldet echten Erfolg, Fehler oder Teilerfolg; Wiederholung dupliziert erfolgreiche Teile nicht | Fehlereinspielung und Retrytest mit gespeicherten IDs |
| A12 | Fremde IDs und KI-Ausgaben verleihen keine Rechte; keine Tokens/Standorte an KI; private Fachinhalte bleiben privat | A/B-Isolation, Eingabeschema-/Kontexttests |
| A13 | Nur ein Detaildialog; Overlays oben; Fokus zurück; keine neue permanente Typ-/Attributleiste; vorhandener gemischter Feed bleibt | Mobil/Desktop mit Tastatur, Geometrie und Screenshots |
| A14 | Eingaben bleiben bei Fehler erhalten; veraltete KI-Antworten ersetzen keine neuen Entwürfe; explizite Abbruch-/Wiederholwege | Browser-/Serviceregression |
| A15 | Vollständige Backendtests, Frontend check/design/build, OpenAPI-Snapshot und erforderliche DB-Isolation bestanden | Tatsächliche Kommandoausgaben; übersprungene relevante Tests zählen nicht als bestanden |

Externe echte KI-Qualität/Verfügbarkeit wird getrennt von deterministischen Tests berichtet. Kein Zugriff auf produktive persönliche Daten zur Abnahme. Offene Kriterien bleiben offen, bis konkrete Evidenz vorliegt.

## Arbeitsnachweis 10.09.2026 — Zwischenstand

- Konzeptentwurf durch korrigierte Richtung mit eindeutigem normativem Nachfolger ersetzt; Registry und alte Notiz-/To-do-Verträge kennzeichnen die Revision. Fachabnahme bleibt offen.
- Lokaler Parser: Unicode-Wortgrenze für „übermorgen“ korrigiert. `node frontend/scripts/test-quick-entry.mjs`: 13 Fälle bestanden, einschließlich Jahreswechsel, Schaltjahr, wöchentlicher Routine und ungültiger Angaben. A2 ist ohne Browserflow noch nicht vollständig nachgewiesen.
- Einkaufsimport: Vorschau und Übernahme verwenden denselben gespeicherten Zeitraum; veraltete Antworten werden verworfen, Datumsfelder beim Speichern gesperrt, Fehler abgefangen. Dialog oben mit Fokus auf Schließen und Rückgabe. A8/A13 bleiben bis zur Browserregression offen.
- Frontend-Typprüfung: 0 Fehler; Designvertrag PASS. Nicht mehr verwendete Styles des entfernten zweiten To-do-Editors bereinigt. Keine vollständige Backend-/Browserabnahme in diesem Zwischenstand.

### Manuelle Routinen und Bereichsnamen

- Routinen im bestehenden Formular bearbeitbar, ohne Statusänderung oder Neuanlage. Erklärung der bestehenden Materialisierungssemantik: bereits erzeugte To-dos bleiben erhalten.
- Bereichsname für Besitzer über vorhandenen PUT-Vertrag bearbeitbar; Eingabegrenze entspricht dem Serverschema (100 Zeichen).
- `frontend/scripts/test-entry-settings-ui.mjs`: PASS im mobilen Chromium (390×844), mit synthetischen API-Antworten. Prüft Bearbeiten/Speichern/Neuladen einer inaktiven Routine, erhaltenen Aktivstatus, geänderte Uhrzeit, Owner-Umbenennung und fehlendes Bearbeitungsfeld für Mitglieder. Dies ersetzt keinen serverseitigen Isolationstest.
- Typcheck 0 Fehler/5 bestehende CSS-Warnungen, Design-Lint PASS. A7 bleibt für Ziele/RIR/Vorlauf-Gesamtnachweis offen.

### Ernährungsverwaltung — Implementierung, Browserabnahme ausstehend

Rezeptname und Ertrag bearbeitbar; Unterrezepte in der Zutatenauswahl mit Portionseinheit ergänzt. Kategorien umbenennbar. Planplätze unterstützen freie Bezeichnung und geplante Uhrzeit. Rezept-/Slotdialog schließen erst nach erfolgreichem Speichern. Slotdialog öffnet oben mit Nicht-Textfokus und Fokusrückgabe. API-Serialisierung entfernt reine Antwortfelder aus Zutaten und erhält explizite erwartete Versionsnummern von Rezepten/Plänen. A6 bleibt bis zur Browser- und Serververifikation offen.

### Browsernachweis Ernährung und Gesprächsgrundlage

- `frontend/scripts/test-meal-settings-ui.mjs`: PASS, mobil 390×844. Prüft Rezeptname/1,5 Portionen, erhaltenen Entwurf nach 422, bereinigte Zutatenpayloads, erwartete Versionsnummer, freien Planplatz/Uhrzeit/Neuladen und oberen Dialog mit Schließen-Fokus. Unterrezepte und Kategorien benötigen noch zusätzliche Browserfälle.
- Assistent erhält begrenzten Verlauf (20 Beiträge, Rollen user/assistant), keine frei wählbare Systemrolle oder Identitätsfelder. Schließen entwertet laufende Antworten; Textänderungen während Anfrage werden nicht gelöscht. Vollständige strukturierte Vorschläge/Ausführung bleiben offen.
- OpenAPI aus dem aktuellen App-Schema regeneriert. Backend mit `APP_IGNORE_DOTENV=1 /tmp/fittrack-backend-test-venv/bin/python -m pytest -q`: 84 passed, 16 skipped, 19 subtests passed. Die übersprungenen Isolationstests sind weiterhin erforderlich; A12/A15 nicht erfüllt. System-Python hatte fehlende Abhängigkeit pydantic_settings; Testlauf erfolgte in der vorhandenen Testumgebung.

### Strukturierte KI-Vorschläge — Grundlage, Ausführung noch offen

Der Proxy erhält statische öffentliche Eingabeschemata und liefert Nachricht plus Aktionen. Der Backend-Service `app/services/assistant.py` prüft Vorschläge mit denselben Fachschemata, eindeutigen Kennungen und expliziten Änderungszielen. Identitäts-/unbekannte Felder, Herkunftsmanipulation, Löschen, erfundene bestätigte Orte und implizite Plan-/Anreiseaktivierung werden abgewiesen. Prioritäten sind nun in beiden To-do-Eingabeschemata auf 1–3 begrenzt. Der Chat bewahrt die strukturierte Antwort und kennzeichnet Vorschläge als ungespeichert. Bearbeiten, Übernahme, Ressourcen-Kontext und Paketabhängigkeiten sind noch nicht angeschlossen; A9–A12 bleiben offen.

Nachweise: `tests/test_assistant_proposals.py` 15 passed; vollständige Suite vor den drei zusätzlichen Herkunfts-/Ortsfällen 96 passed, 16 skipped, 19 subtests passed. Frontend-Typcheck und Design-Lint bestanden. OpenAPI regeneriert. Kein Modell-Qualitätsnachweis oder produktiver Schreibvorgang.

### Freigabe des Zwischenstands zum Commit/Deployment

Nutzerauftrag „Dann setz das um“ nach expliziter Nachfrage zum Commit-/Deploymentstand autorisiert die Veröffentlichung des aktuellen Zwischenstands. Das ursprüngliche Gesamtziel bleibt aktiv: KI-Bearbeitung/Übernahme, Pakete und weitere A1–A15-Nachweise sind nicht abgeschlossen.

Vor Veröffentlichung: Frontend check/design/build bestanden; Parser 13 Fälle bestanden. Vollständiger Backendlauf mit separatem frischem PostgreSQL und allen Migrationen: **115 passed, 19 subtests passed**, keine Skips. Produktionsschema read-only geprüft: `b60908c002 (head)`, keine weitere Produktionsmigration erforderlich. Vorhandene native Login-/Anreiseänderungen werden mitgesichert und nicht zurückgesetzt.
