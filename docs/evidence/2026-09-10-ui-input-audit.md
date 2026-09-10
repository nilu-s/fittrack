# UI/UX-Prüfung: Eingabeabdeckung

Stand: 2026-09-10. Ergebnis: Die geplanten Funktionen sind in der Oberfläche nur teilweise vollständig bedienbar. Besonders fehlen erreichbare To-do-Details und freie Mahlzeitenerfassung.

## Prüfrahmen

- Ziel: geplante Benutzerfunktionen gegen erreichbare Eingaben, Bearbeitbarkeit und Speicherlogik prüfen.
- Grundlage: aktive Spezifikationen aus `docs/specs/README.md`, deren ausdrückliche Revisionen sowie `docs/design/cronicl-day-feed-interaction.md`. Sport, Ziele und Routinen zusätzlich anhand ihrer bestehenden Oberfläche; hierfür wird kein neuer Produktumfang behauptet.
- Umfang: `frontend/src/routes/`, `frontend/src/lib/components/`, API-Client und relevante Typen; Spezifikationen lesend.
- Schreibbereich und einziger Konfliktbereich: dieser Prüfbericht. Keine Anwendung, API, Spezifikation oder vorhandene Benutzeränderung geändert; keine produktiven Daten benutzt.
- Methode: statische Quellcodeprüfung einschließlich Aufrufern und Schreib-Payloads. Kein vollständiger Browserdurchlauf, keine visuelle Mobilgeräteabnahme, kein Nachweis realer Google-/Gerätefunktionen. „Vorhanden“ bedeutet im Code vorhanden, nicht Ende-zu-Ende abgenommen.
- Abnahme dieses Reviews: Feature-Matrix, belegte Lücken, getrennte Produktfragen und reproduzierbare Prüfschritte. Bei widersprüchlichen Anforderungen keine stillschweigende Entscheidung oder Umsetzung.

## Feature-Matrix

| Feature | Vorhandene Eingaben/Aktionen | Bewertung |
| --- | --- | --- |
| Login und Alias | Google-Button, Warte-/Fehlerzustand; Alias mit Format-/Längenregeln | Grundlegende Controls vorhanden; native Geräteabnahme separat. iOS-Ersatzlogin ausdrücklich noch nicht freigegeben/implementiert. |
| Kontakte | Alias-Suche, Anfrage, Annehmen/Ablehnen, Entfernen | Für den geplanten Kontaktumfang passende Controls vorhanden. |
| Bereiche | Name bei Anlage, Bereichsauswahl, Kontakt einladen, Mitglied entfernen | Umbenennen fehlt (F8). |
| Notizen | Titel, Inhalt, Bereich, Datum, Uhrzeit; Kalender-Zeitblock mit Dauer; Entplanen | Wesentliche Eingaben vorhanden. Bestätigungslogik für Teilen vorhanden; Tastatur-/Touchabnahme noch offen. |
| To-dos | Footer-Titel; erreichbarer Editor für Titel, Kategorie, Priorität, Datum, Uhrzeit | Ausführliche Details nicht erreichbar: Ort, Anreise, Bereich und Zuständigkeit fehlen praktisch (F1). |
| Routinen | Titel, Wochentage, Uhrzeit, Priorität bei Anlage; aktiv/inaktiv, Löschen | Bestehende Routine nicht inhaltlich bearbeitbar (F9). |
| Anreise | Im Detail bereits vorbereiteter To-dos: Startort, Verkehrsmittel im unverbundenen Editor, Start/Pause/Beenden | Einrichtung durch F1 blockiert; Puffer fehlt, Vorlauf eingeschränkt (F7). |
| Mahlzeit am Tag | Bestehenden Eintrag verzehrt/geplant setzen; Rezept-/Lebensmittelauswahl | Freie Anlage, Zusatzmahlzeit, überspringen, Mengen- und Zeitpunktkorrektur fehlen (F2/F3). |
| Fotoanalyse | Datei/Kamera, Vorschau, Gramm, Lebensmittelzuordnung, Bestätigen/Verwerfen | Prüfung vorhanden; benötigt bereits vorhandene Mahlzeit und eigene Lebensmittel. Fehlende Stammdaten im Dialog nicht anlegbar. |
| Lebensmittel | Name, Makro-/Mikronährstoffe je 100 g, Bearbeiten | Breite Feldabdeckung; neue Felder nur mit Platzhaltern beschriftet; unbekannte kcal beim Anlegen verboten (F6/F11). |
| Rezepte | Anlage mit Name, Portionen, Lebensmittel/Gramm, Notizen, Anleitung; Archivieren | Name und Portionsertrag später nicht bearbeitbar; Unterrezepte nicht auswählbar (F5). |
| Mahlzeitenkategorien | Name bei Anlage, Reihenfolge, Aktivierung, zwei Standardrezepte | Umbenennen fehlt (F5). |
| Mahlzeitenplan | Planname bei Anlage, Wochenraster, Rezept, Portionen, Aktivierung | Geplante Uhrzeit und freier Platzhalter fehlen (F4). |
| Einkauf | Freitext/Suche, Status, Titel, Menge, Einheit, Kategorie, Icon, Notiz | Kernfelder vorhanden; Import-Zeitraum und Vorschau können auseinanderlaufen (F10). |
| Training planen | Einheitstyp, Cardio-Dauer, Übungen, Sätze/Wiederholungen/RIR, Progression, Wochenrotation | Breite Abdeckung vorhanden; einzelne Validierungs- und Bearbeitungsfragen bleiben. |
| Training erfassen | Satztyp, Wiederholungen, kg, RIR; Cardio-Minuten | RIR 0 wird zu leer; Satzfelder ohne zugängliche Namen (F6/F11). |
| Körperprofil | Größe mit cm, Geburtsdatum, Berechnungsparameter | Passende grundlegende Eingaben vorhanden. BIA-Werte sind keine Benutzereingabe und bleiben von echter Impedanz abhängig. |
| Gewicht/Waage | Manuelles Tagesgewicht, Verlauf, zugeordnete Messung entfernen | Bereichseinrichtung für neue Konten nicht erreichbar; Betriebs-/Produktfrage (F13). |
| Schritte/Schlaf | Anzeige und Verlauf | Keine manuelle Erfassung im aktuellen Detail. Ob Fallback erwünscht ist, bleibt Produktfrage; keine eindeutig belegte Pflicht zur manuellen Eingabe. |
| Tagesziele | Energie, Makros, Zucker, Schritte, Schlaf | Felder vorhanden, aber ohne verknüpfte Labels, Wertebereiche und sichtbaren Speicherfehler (F11). |
| Integrationen | Verbindungsstatus, Trennen, erneute Statusabfrage | Unverbundener Zustand nur mit Erklärung, ohne direkten Verbinden-Weg. Aktuelle Android-Spezifikation nimmt neue Kalenderfreigabe aus dem Paket aus. |
| Wochenübersicht | Auswertung und Trends | Beobachtungsansicht; keine zusätzlichen Eingabefelder erforderlich. |
| KI-Chat | Frage, Senden, Antwort | Passend zum aktuellen Vertrag: beantwortet Fragen, speichert keine Aufgaben oder Pläne. Unbenutzter KI-Planer ist kein erreichbarer Erfassungsweg. |
| Daten/Export | JSON-/CSV-Button | Exportiert nur Ziele; allgemeine Kontodatenfunktionen fehlen (F12). |

## Priorisierte Befunde

P1 = zentrale geplante Handlung blockiert oder Eingabewert verfälscht. P2 = eingeschränkte Bearbeitung, Verständlichkeit oder Verlässlichkeit.

### F1 — P1: Ausführlicher To-do-Editor ist nicht erreichbar

`frontend/src/routes/+page.svelte:28` initialisiert `todoDetails` mit `null`. Die einzige weitere Verwendung ist das Binding des Dialogs in Zeile 247 einschließlich Zurücksetzen auf `null`; kein Öffnungspfad weist ein To-do zu. Die Footer-Anlage (Zeile 108) legt nur einen privaten Eintrag an. Der erreichbare Bearbeitungsfluss in `UnifiedDay.svelte:236` und `:934` nutzt einen eigenen reduzierten Editor.

Auswirkung: Nutzer können dort weder Zielort/Anreise noch Bereich/Zuständigkeit setzen. Ein vorhandenes Formular in `TodoDetailsSheet.svelte` erfüllt diese Features nicht, solange es unerreichbar ist. Auch die Anreisebegleitung kann erst erscheinen, wenn Ort, Modus und Startzeit bereits vorhanden sind.

Korrektur: Einen gemeinsamen Detaildialog an die sichtbare Bearbeiten-Aktion anbinden. Prüfung: Neues To-do ausschließlich über UI anlegen, Ort bestätigen, Datum/Startzeit/Modus speichern und Begleitung öffnen; manuelles Bereichs-To-do einem Mitglied zuweisen. Private Integrationen dabei privat halten.

### F2 — P1: Mahlzeitenmengen sind fest verdrahtet

`MealEntryEditorSheet.svelte:55–78`: Rezeptauswahl schreibt sofort `quantity: 1, unit: 'serving'`; Lebensmittelauswahl sofort `quantity: 100, unit: 'g'`. Die normalen Dialogfelder enthalten keine Mengen- oder Komponentenbearbeitung. Die komplette Item-Liste wird durch genau ein Item ersetzt.

Korrektur: Auswahl zunächst in einen Entwurf übernehmen, Menge und Einheit sichtbar bearbeiten, mehrere Komponenten ermöglichen, explizit speichern. Prüfung: 150 g Lebensmittel und 1,5 Rezeptportionen erfassen; nach erneutem Öffnen müssen Menge und Nährwertsumme erhalten bleiben. Kein unbemerkter Verlust weiterer Komponenten.

### F3 — P1: Zusätzliche Tagesmahlzeiten und „übersprungen“ fehlen

`api.createMealEntry` und `api.deleteMealEntry` sind in `frontend/src/lib/api.ts` definiert, aber haben keine Aufrufer in `frontend/src`. Die Tagesansicht arbeitet mit Planinstanziierungen; ihr Statuswechsel in `UnifiedDay.svelte:311–340` kennt nur `planned`/`consumed`. Die Spezifikation verlangt zusätzliche Einträge je Kategorie/Tag und einen expliziten Zustand `skipped`.

Korrektur: Sichtbares „Mahlzeit hinzufügen“ mit Kategorie, Datum, Uhrzeit und Komponenten; explizite Statusauswahl. Prüfung: Ohne aktiven Plan essen erfassen; zweiten Snack derselben Kategorie anlegen; geplante Mahlzeit überspringen, ohne sie als verzehrt zu zählen.

### F4 — P2: Im Plan fehlen Uhrzeit und freier Platzhalter

`settings/meals/+page.svelte:87` verlangt zwingend ein Rezept und baut den Slot ohne `planned_time` auf. Dialog Zeile 119 bietet nur Rezept und Portionen. Beim Ersetzen eines vorhandenen Slots wird eine vorhandene Planzeit nicht übernommen.

Korrektur: Uhrzeit optional, Rezept oder benannter freier Platzhalter. Prüfung: „Mittagessen auswärts“, 12:30 Uhr, ohne Rezept planen und später konkretisieren; reine Portionsänderung muss die Zeit erhalten.

### F5 — P2: Stammdaten lassen sich nur teilweise pflegen

`settings/meals/+page.svelte:65–70,113,115`: Rezeptanlage hat Name und Portionsertrag, Bearbeitung dagegen nur Zutaten, Notizen und Anleitung. Zutaten können nur Lebensmittel in Gramm sein; vorhandene Unterrezepte würden mit der Lebensmittelanzeige unverständlich dargestellt. Kategorien zeigen ihren Namen nur als Text, obwohl Umbenennen ausdrücklich spezifiziert ist.

Korrektur: Name/Portionsertrag auch im Editmodus, Zutatentyp Lebensmittel/Rezept samt sinnvoller Einheit, bearbeitbarer Kategoriename. Mengen vorhandener Zutaten direkt ändern statt entfernen und neu hinzufügen. Prüfung: Rezept von zwei auf vier Portionen korrigieren und Unterrezept hinzufügen; historische Einträge bleiben unverändert.

### F6 — P1: Training verliert den gültigen Wert RIR 0

`TrainingDetail.svelte:69` verwendet für Wiederholungen, Gewicht und RIR `parseFloat(value) || null`. Dadurch wird `0` zu `null`. RIR 0 ist ein sinnvoller Eingabewert; auch gewichtsloses Training darf nicht durch diese Umwandlung seine Eingabe verlieren.

Korrektur: Leere/ungültige Eingabe ausdrücklich prüfen, Nullwert erhalten. Prüfung: RIR 0 eingeben, Training abschließen, gespeicherten Payload kontrollieren. Dezimale Gewichte mit geeigneter Schrittweite und negative Werte gezielt prüfen.

### F7 — P2: Anreisepuffer fehlt, Vorlaufbereich unvollständig

`TodoDetailsSheet.svelte` bietet kein `travel_buffer_minutes`-Feld. Der Wert wird sonst nur angezeigt beziehungsweise im unverbundenen KI-Planer auf zehn Minuten gesetzt. `TravelCompanion.svelte:90` bietet 30/60/90/120 Minuten, obwohl 15–180 Minuten spezifiziert sind. Die Zeitzone ist beim Speichern auf Europe/Berlin festgelegt (Zeile 40).

Zusätzlich fehlt „Ort entfernen“: der Detaildialog fällt beim Speichern auf die bisherigen Ortsfelder zurück. Dies wird nach Behebung von F1 sichtbar relevant.

Korrektur: Puffer in Minuten; vollständiger Vorlaufbereich; Ort bewusst entfernen können. Zeitzonenwahl nur ergänzen, wenn Produktbedarf bestätigt ist; zunächst verwendete Zeitzone verständlich anzeigen. Prüfung: Puffer 20, Vorlauf 15 und 180, Ziel löschen.

### F8 — P2: Bereiche können nicht umbenannt werden

`SpaceManager.svelte:25–27` enthält Name nur bei Anlage, danach Überschrift, Mitgliedsliste und Einladung. `shared-spaces.md` erlaubt dem Owner ausdrücklich Namensänderung.

Korrektur: Name und Speichern im Owner-Bereich. Prüfung: Bereich umbenennen, Picker und Mitgliederansicht aktualisieren; Nicht-Owner erhält keine entsprechende Mutation.

### F9 — P2: Routinen nur anlegen, aktivieren oder löschen

`settings/todos/+page.svelte:57–69`: Titel, Wiederholung, Zeit und Priorität nur beim Anlegen. Bestehende Zeilen haben lediglich Aktivierung und Löschen.

Bewertung: konkrete Bedienlücke des bestehenden Features, keine neu erfundene Spezifikationspflicht. Korrektur: bestehende Routine im selben Formular bearbeiten. Prüfung: Einnahmezeit ändern, ohne die Routine löschen und neu erstellen zu müssen; bereits erzeugte Tagesaufgaben nach festgelegter Semantik behandeln.

### F10 — P1: Einkaufsimport kann einen anderen Zeitraum als die Vorschau übernehmen

`ShoppingMealImport.svelte:9–14`: Die reaktive Vorschau referenziert `open`, `startDate` und `dialog`, aber nicht `days`. In dieser Svelte-Legacy-Reaktivität wird die Abhängigkeit nicht aus dem Funktionskörper von `load()`/`endDate()` abgeleitet. Die Änderung von 7 auf 14 Tage stößt daher keine neue Vorschau an; `confirm()` berechnet das aktuelle Enddatum dennoch neu. Außerdem ist Bestätigen nicht während `loading` gesperrt.

Korrektur: Vorschau explizit an beide Datumsparameter binden; alte Vorschau bei Änderung ungültig machen; nur exakt die bestätigte Vorschau importieren. Prüfung: sieben auf vierzehn Tage ändern und mit verzögerter Antwort testen; angezeigte und übernommene Zutaten müssen übereinstimmen.

### F11 — P2: Beschriftung, Validierung und Speicherfeedback uneinheitlich

- `settings/goals/+page.svelte:32–40`: Text in `span` statt zugeordneter Labels, keine Min-/Max-Werte oder explizite Dezimalschritte; `saveGoals` verschluckt Fehler. Eine lokale Änderung erscheint ohne Information über fehlende Serverspeicherung.
- `TrainingDetail.svelte:69`: Satzfelder für Wiederholungen, kg und RIR ohne eigene Labels oder `aria-label`.
- `UnifiedDay.svelte:938–949`: erreichbarer To-do-Editor mit Platzhaltern, Datum/Zeit/Priorität ohne zugängliche Namen; `saveEdit` schließt vor bestätigtem Erfolg und zeigt keinen Fehler.
- `settings/meals/+page.svelte:110`: neue Nährwertfelder haben `aria-label`, aber visuell nur verschwindende Platzhalter. `addFood` verlangt kcal trotz Erklärung „Leere Werte bleiben unbekannt“ und nullable Fachmodell.

Korrektur: dauerhaft sichtbare Labels und Einheiten, fachlich begründete Wertebereiche, unterscheidbare Zustände leer/0/ungültig; Fehlermeldung am Formular und Eingabeerhalt. Prüfung mit Tastatur, Screenreader sowie leeren, nullwertigen und dezimalen Eingaben; Netzwerkfehler darf keinen scheinbaren Speichererfolg ergeben.

### F12 — P2: „Daten exportieren“ exportiert nur Tagesziele

`settings/data/+page.svelte:9–13` serialisiert ausschließlich `goals` und Exportzeitpunkt. Keine Tageshistorie, Messungen, Mahlzeiten oder Trainingsdaten. Die Seite erklärt außerdem ausdrücklich, hier keine Löschung anzubieten; der Kontodatenumfang aus der Account-Spezifikation ist dadurch nicht abgedeckt.

Korrektur: kurzfristig exakte Bezeichnung „Tagesziele exportieren“; vollständigen privaten Datenexport und Löschumfang als eigenes Paket behandeln. Prüfung: Dateiinhalt gegen angezeigten Exportumfang abgleichen. Kein beliebiges zusätzliches Textfeld notwendig, sondern ein vollständiger Workflow.

### F13 — Klärung: Neue Konten haben keinen sichtbaren Weg zur Waagenzuordnung

Die Android-Anmeldespezifikation verlangt einen inaktiven Gewichtsbereich bis zur bewussten Konfiguration. `settings/scale/+page.svelte` bietet nur Verlauf/Aktualisieren/Entfernen; Körperprofil nur Größe, Geburtstag und Berechnungsparameter. Im Frontend existiert kein Gewichtsbereich-Editor.

Das ist eine Einrichtungslücke; aus den Vorgaben geht hier nicht eindeutig hervor, ob der Nutzer oder ein Betreiber konfigurieren soll. Vor Umsetzung Verantwortlichkeit festlegen. Mindestens muss der nicht eingerichtete Zustand erklärt werden. Keine freie Kontozuweisung von Messungen und keine Geräte-Kontowahl ergänzen.

## Empfohlene Interaktion und Referenzen

Empfehlung: Schnellerfassung beibehalten, dahinter je Fachfunktion einen vollständig erreichbaren Editor mit beschrifteten Feldern und bewusstem Speichern verwenden.

| Referenz | Übertragbares Muster | Nutzen und Grenze |
| --- | --- | --- |
| [MyFitnessPal: Lebensmittel erfassen](https://support.myfitnesspal.com/hc/en-us/articles/360032274592-How-do-I-add-a-food-to-my-food-diary) | Portionsgröße/-anzahl und Mahlzeitenzuordnung beim Erfassen | Passt zu F2/F3; dessen Katalog- und Premiumumfang wird nicht übernommen. |
| [Todoist: Datum und Uhrzeit](https://www.todoist.com/help/todoist/features/set-a-fixed-time-or-floating-time-for-a-task-YUYVp27q) | Datum/Zeit sowohl beim Anlegen als auch Bearbeiten zugänglich | Passt zum gemeinsamen To-do-Editor; keine automatische Übernahme fremder Zeitzonenregeln. |
| [W3C: Formulare beschriften](https://www.w3.org/WAI/tutorials/forms/labels/) | Controls ausdrücklich mit Labels verknüpfen | Grundlage für verständliche und zugängliche Felder; ersetzt keine praktische Bedienprüfung. |

Verglichene Optionen: Alle Felder in den Footer zu legen würde die Schnellerfassung überladen. Ausschließliche Inline-Bearbeitung passt zu einem einzelnen Wert, skaliert aber schlecht für Zutaten und Anreise. Ein Fachdialog hinter einer kurzen Erfassung nutzt die vorhandene Struktur und bietet genügend Platz für Prüfung und Fehlerfeedback. Tastatur: native Controls, sinnvoller Anfangsfokus und Rückkehr zum Auslöser. Touch: einspaltige Feldgruppen auf kleinen Displays; Dialog scrollbar, Aktionen erreichbar. Vorhandene Tokens und `UiButton`, `UiSurface`, `TodoDetailsSheet`, `MealEntryEditorSheet` wiederverwenden; keine zusätzliche Bibliothek erforderlich.

Erstes Umsetzungspaket: ausschließlich To-do-Dialog verbinden und den reduzierten Doppel-Editor ersetzen; danach F2/F3 als eigenes Mahlzeitenpaket. F6 und F10 sind unabhängig behebbare Speicherfehler. Jeder Fix benötigt den oben beschriebenen gezielten Verhaltenstest sowie die vorgeschriebenen Frontend-Prüfungen; deren Erfolg wird in diesem Review nicht behauptet.

## Artefaktbewertung und offene Entscheidungen

Touchpoint ist die nachgewiesene Abweichung der Eingabe-/Bearbeitungsflüsse. Die bestehenden Produktanforderungen bleiben maßgeblich; dieser Bericht ersetzt keine Spezifikation.

- `configurable-meals.md`: **revise** für den pauschalen Implementierungsstatus/Verifikationsnachweis angesichts F2–F5. Der freigegebene Umfang wird nicht reduziert; keine Freigabe zur stillen Anpassung der Spezifikation an den Code.
- `shared-spaces.md`: **revise** für die widersprüchliche Verifikationszeile „Kontakte erzeugen sofort Mitgliedschaft“ gegenüber der ausdrücklich geforderten Einladungsannahme. Die UI folgt dem Annahmefluss. Dies ist eine getrennte Dokumentkorrektur, kein Anlass, die Mitgliedschaftslogik zu ändern. F1/F8 bleiben Implementierungslücken.
- `todo-places-and-travel.md`, `native-travel-companion.md` und Day-Feed-Vertrag: unerfüllte UI-Verpflichtungen F1/F7/F11 dokumentiert; keine vollständige `confirmed`-Abnahme, keine belegte Notwendigkeit zur Änderung der Produktentscheidung.
- Kontakte/Notizen/Körperprofil: betrachtete Feldabdeckung plausibel, aber keine vollständige Spec-Revalidierung oder Kontoisolationsabnahme durchgeführt. Kein pauschales `confirmed`, keine Registry-Änderung.

Produktfragen für spätere Umsetzung: Wer richtet den Gewichtsbereich ein? Soll es manuelle Schritte-/Schlafeingaben als Import-Fallback geben? Welcher vollständige Export-/Löschumfang wird in einem eigenen Paket umgesetzt? Diese Fragen blockieren die belegten UI-Korrekturen nicht.
