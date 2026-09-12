# UI/UX-Prüfung · 12. September 2026

## Auftrag und Grenzen

Alle 16 Frontend-Routen und die aus ihnen erreichbaren Fachdialoge visuell mit
Playwright prüfen und konkrete Bedienungsfehler beheben. Einziger schreibender
Konfliktbereich: Frontend-UI einschließlich gemeinsamer Styles und Browsernachweise.
Erlaubte Nebenwirkungen: lokale Vorschau, synthetische API-Antworten, Screenshots.
Keine Produktdaten, API-Verträge, Authentifizierungslogik, Firmware oder Deployments
wurden geändert. Produktentscheidungen außerhalb der bestehenden Richtung wären
Stop-Bedingung gewesen; sie waren für diese Korrekturen nicht erforderlich.

## Nachvollziehbare Korrekturen

| Befund | Korrektur | Nachweis |
| --- | --- | --- |
| Kalender und Sport-Pop-ups lassen den Fokus im Hintergrund; Trenddialoge sind nur `open` | Native modale Dialoge, Escape, Fokus auf Schließen und Rückgabe zum Auslöser | Kalender, Sport erstellen/planen/bearbeiten, Nährwerte, drei Verläufe |
| Fokus geht beim Wechsel Gewicht → Verlauf bzw. Mahlzeit → Editor verloren | Ursprünglichen Auslöser über den Dialogwechsel erhalten | Gewichtsverlauf, Mahlzeiteneditor |
| Wischen im Dialog erreicht die Aktualisierungsgeste der Seite | Pull-to-refresh bei offenem modalen Dialog unterdrücken | Synthetische Touch-Ereignisse im To-do-Editor |
| Lange Editorinhalte auf kurzen Displays | Viewportbegrenzung, interner Scrollbereich, gesperrter Hintergrund | `small-*-end.png`: letzte Aktion erreichbar |
| Antippen von Mahlzeit/Training tut nichts, Enter öffnet Details | Gleiche Details über Touch, Klick, Enter und Leertaste; Kindbuttons separat bedienen | Mahlzeit und Training; Detailbutton per Enter |
| Sehr blasse Hilfstexte | Sekundäre Text-Tokens abgedunkelt | Alle Seiten; Textkontrast ≥ 4,5:1 auf regulären Flächen einschließlich gedrücktem Zustand |
| Einkauf läuft seitlich aus dem Viewport, Label erscheint doppelt | Gemeinsame `sr-only`-Klasse, sichtbare Formularfelder, zugänglicher Plusbutton | Einkauf bei 320/390 px |
| Mahlzeitenplanung erweitert die gesamte Seite | Gemeinsame Surfaces dürfen unter ihre Inhaltsbreite schrumpfen | Mahlzeiten bei 320/390 px |
| Titel liegen unter Kontobutton; Routinenzeilen sind zu eng | Platz für Kontobutton, Umbruch der Routinenaktionen, begrenztes Kontomenü | Einstellungen, Kontakte, Einkauf, Routinen |
| Kleine Tageswerte, Detail- und Einkaufsaktionen | Größere bedienbare Flächen; lesbare Formulare bei Touch-Eingabe | Tagesansicht, Einkauf, Training |
| Footer ist am Desktop breiter als die Anwendung; Inhalte scheinen beim Scrollen durch | Fußleiste an App-Breite ausrichten, solide Navigations- und Kopfzeilenflächen | Tagesansicht, Notizplanung |
| Unvollständige Tab-/Auswahlsemantik | Sporttabs mit Pfeiltasten/Home/End; Rezeptauswahl als Gruppe nativer gedrückter Buttons | Sport, Mahlzeitenplan |
| KI-Chat verliert beim Deaktivieren des Senden-Buttons den Fokus | Fokus nach der Antwort bzw. dem Fehler im noch offenen Dialog wiederherstellen | `mobile-assistant-error.png` |
| Wochenrückblick lädt nach Fehlschlag endlos | Fehlertext mit Wiederholen; Erfolg nach Wiederholung | `mobile-week-error.png`, `mobile-week-recovered.png` |
| Notiz-/Einkaufseditor öffnet direkt die Tastatur | Schließen statt Texteingabe fokussieren | Beide Editoransichten |

## Abdeckung

Routen: `/`, `/week`, `/shopping`, `/contacts`, `/settings`, sämtliche neun
Settings-Unterseiten, `/login`, `/onboarding/alias`.

Dialoge und Zusatzansichten: Kalender, Konto-Popover, KI-Chat, To-do-Editor und
Details, Trainingsdetails mit Sätzen, Mahlzeitendetails und Editor,
Schritt-/Schlaf-/Gewichtsverlauf, Gewichtseingang, Nährwerte, Notizboard,
Notizeditor und Bereichskalender, Einkaufs-Schnellansicht, Einkaufseditor,
Mahlzeitenimport, Rezepteditor, Mahlzeitenplanung, Sportbibliothek,
Einheitenerstellung, Einheiteneditor, Progression und Rotation, Bereichsverwaltung.

Viewportgrößen: 320×568, 390×844, 1440×1000. Chromium mit Touch-Fähigkeit für die
beiden schmalen Größen, deutscher Sprache und Berliner Zeitzone. Screenshots
beenden CSS-Animationen, damit der Endzustand statt eines Übergangs dokumentiert
wird. Dialogbilder zeigen den Viewport, Seitenbilder die gesamte Seite.

Zusätzlich: HTTP-503 bei Wochenrückblick, KI-Chat und Mahlzeitenimport sowie
Wiederherstellung des Wochenrückblicks. Jeder geprüfte Dialog erhält Tests auf
native Modalität, initialen Fokus, Tab-Navigation, Escape, Fokusrückgabe bei noch
vorhandenem Auslöser und horizontalen Überlauf. Lange Dialoge werden auf dem
kleinsten Viewport bis zur letzten Aktion gescrollt.

Nicht als Geräteabnahme zu verstehen: Browser-Kamera, Google-Anmeldung,
Standort-/Push-Berechtigungen und Bildschirmtastatur auf echten Android-/iOS-Geräten
sind nicht durch diese Mock-Prüfung abgedeckt. Der nicht mehr eingebundene
`TodoAiPlannerSheet` und das nicht aufgerufene alte To-do-Aktionsmenü haben keinen
erreichbaren Screenshot-Einstieg. Native Browserbestätigungen bleiben browserseitig. Die Kontrastprüfung betrifft die allgemeinen Text-Tokens auf den regulären Flächen; sie ist keine pauschale WCAG-Zertifizierung aller Datenfarben und Zustände.

## Reproduzieren

Vom Repository aus:

```bash
cd frontend
npm run check
npm run lint:design
npm run build
npm run preview -- --host 127.0.0.1 --port 4181
# In einem zweiten Terminal im Repository:
ENTRY_TEST_URL=http://127.0.0.1:4181 node frontend/scripts/test-ui-audit.mjs
```

Nach einem erneuten Build die Vorschau neu starten. Sämtliche `/api/`-Anfragen
werden abgefangen; es werden nur erfundene Beispiele verwendet.

Weitere durchgelaufene Regressionen: `test-entry-settings-ui.mjs`,
`test-meal-settings-ui.mjs`, `test-todo-direct-edit-ui.mjs`, `test-travel-ui.mjs`.

## Artefaktprüfung

| Quelle | Touchpoint und Ergebnis |
| --- | --- |
| `docs/design/cronicl-day-feed-interaction.md` | **confirmed**: Fachflüsse bleiben getrennt, Touch/Tastatur gleichwertig, Fokusregeln im Browser geprüft. |
| `docs/design/cronicl-ui-direction.md`, ADR 0002 | **confirmed**: gedämpfte Flächen und semantische Tokens erhalten, Kontrast und Dichte verbessert. |
| `frontend/docs/design-system.md` | **confirmed**: gemeinsame Primitives, native Dialoge und Mindestgrößen; Prüfpfad ergänzt. |
| `docs/specs/unified-entry-and-assistant.md` | **confirmed für diesen UI-Touchpoint**: Nicht-Textaktion beim Öffnen, ein Dialog zur Zeit, Fokus-Rückgabe. Keine Aussage zur vollständigen Assistentenimplementierung. |
| `docs/specs/contacts.md` | **confirmed für Darstellung**: Suche und Aliasfeld visuell verbessert; Einladungen, Identität und Zugriffsregeln unverändert. |
| `docs/specs/multi-account-scale-and-body-composition.md` | Kein fachlicher Touchpoint: Daten-/Sessioncode und Gesundheitsberechnungen unverändert. Gemeinsame Styles wurden mit Profil-/Waagenseite geprüft. |

Die Ordner `before` und `initial` enthalten nur ausgewählte Befunde aus der
Erkundung; `initial` entstand bereits während der ersten Korrekturen und ist kein
vollständiger Vergleich gegen den ursprünglichen Commit. Maßgeblicher Endstand:
`after/results.json` und die Galerie `index.html`.

## Endergebnis

139 geprüfte Zustandsaufnahmen, 143 PNG-Dateien einschließlich Scroll-Enden.
Keine horizontalen Seiten- oder Dialogüberläufe, keine JavaScript-Laufzeitfehler.
Alle Modalitäts-, Fokus-, Escape- und Erreichbarkeitsprüfungen bestanden.
`npm run check`: 0 Fehler, 0 Warnungen; Design-Lint und Produktionsbuild bestanden.

Galerie regenerieren: `python3 frontend/scripts/ui-audit-gallery.py`.
