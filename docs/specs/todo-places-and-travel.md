# To-dos mit Ort, KI-Zuordnung und Anreise

**Status:** approved
**Owner:** Cronicl household
**Last updated:** 2026-09-02

## Ziel

Ein persönliches oder Space-To-do kann einen eindeutig bestätigten Zielort und eine
Anreiseart erhalten. Die Schnellerfassung verwendet ein gemeinsames Textfeld:
`+` legt den Text sofort an und öffnet danach ein Detail-Overlay, in dem
Angaben ergänzt oder korrigiert werden können. `✦` öffnet einen allgemeinen,
explizit angeforderten KI-Chat; er speichert keine To-dos, Orte oder
Anreiseüberwachung.

Zusätzlich gibt es eine private allgemeine To-do-Liste für Einträge ohne Datum.
Sie nutzt dieselben To-do-Datensätze und Statuswechsel wie die Tagesliste;
ein Eintrag ohne `due_date` erscheint ausschließlich in diesem Bereich.

## Regeln

1. Ein privater To-do-Ort gehört ausschließlich zum angemeldeten Konto;
   Space-To-dos folgen zusätzlich der Mitgliedschaftsprüfung aus
   `shared-spaces.md`. Browser
   dürfen weder `account_id` noch Google-Zugangsdaten übermitteln.
2. Ein bestätigter Google-Ort wird durch `place_id` referenziert. Name und
   Adresse sind ausschließlich Anzeige-Snapshots und werden nicht als
   Identitätsersatz verwendet.
3. Eine Anreise ist nur für ein offenes To-do mit Datum, Startzeit und Ort
   möglich. Der Nutzer wählt die Anreiseart (`drive`, `bicycle`, `walk`,
   `transit`); der Standardpuffer beträgt zehn Minuten und ist pro To-do
   änderbar.
4. Standortkoordinaten aus dem Browser werden nur für die einzelne
   Routenschätzung an den Server weitergereicht, nicht persistiert und nicht
   als Bewegungsverlauf protokolliert. Fehlen sie, bleibt die Route ein
   bestätigungsbedürftiger Entwurf.
5. Bei aktivierter Überwachung ist der Eintrag in der Tagesliste mit einer
   sachlichen Metazeile versehen. Nur wenn „jetzt los“ gilt oder sich die
   Abfahrt wesentlich verschiebt, wird er als nächste Handlung hervorgehoben.
6. Verkehrsdaten und Place-Suche laufen ausschließlich über serverseitige
   Google-Maps-Schlüssel. Der explizite KI-Chat nutzt den bestehenden internen
   Codex-/Hermes-Proxy und erhält nur die Chat-Eingabe und den gewählten Tag;
   er sieht keine Standortkoordinaten, Sitzungen oder Google-Tokens.
7. Relative Datumsangaben werden gegen den ausgewählten Tag aufgelöst.
   „Nächsten Freitag“ ist der Freitag strikt nach diesem Referenztag; eine
   unpräzisere Angabe bleibt im Detail-Overlay korrigierbar.

## Interaktion

- `+` neben der Schnellerfassung erstellt ein simples To-do aus dem Text und
  öffnet unmittelbar das Detail-Overlay.
- Die Footer-Schaltfläche mit To-do-Symbol links vom Datum öffnet die
  allgemeine Liste als mobilen, höhenverstellbaren Split-Screen (Desktop:
  gleichwertige Seitenleiste). Die Fußzeilen-Eingabe legt dort ein To-do ohne
  Datum an. Sie wird beim Öffnen fokussiert; Escape und „Schließen“ kehren zum
  Auslöser zurück. Einkauf und allgemeine Liste sind nie gleichzeitig offen.
- `✦` öffnet den KI-Chat für Fragen und komplexe Planungswünsche. Er gibt
  Antworten, führt aber keine Datenänderung aus.
- Ein Ortsvorschlag wird über die Place-Suche ausgewählt und bestätigt. Die
  Aktion **Anlegen** bleibt bis dahin eine bewusste, native Schaltfläche.
- Die Schätzung zeigt Quelle, Prüfzeit, Reisedauer, Ankunfts- und Abfahrtszeit.
  Ohne Standortzugriff ist „Standort jetzt verwenden“ der sichtbare Fallback.

## Externe Betriebsgrenze

Die PWA kann bei geöffneter App im Fünf-Minuten-Takt aktualisieren. Eine
zuverlässige Prüfung bei geschlossener App und Push-Mitteilung braucht einen
separat betriebenen Hintergrund-Worker sowie VAPID-/Push-Abonnements; die
Browser-Geolocation liefert dann keinen garantierten Live-Standort. Dieser
erste Schnitt speichert daher keine falsche Live-Position und führt keine
stille Standortüberwachung ein.

## Touchpoints und Verifikation

| Verpflichtung | Prüfung |
| --- | --- |
| Kontoisolation für Orte/Anreise | `backend/tests/test_todo_places_contract.py`, Account-Isolation-Suite |
| Keine clientgesteuerte Identität oder Schlüssel | OpenAPI-/Schema-Test und Quellcodeprüfung |
| Relative KI-Datumsauflösung | `backend/tests/test_todo_places_contract.py` |
| Browser-UI hat sichtbare, native Aktionen | `npm run check`, Accessibility-Review |
| Allgemeine To-dos bleiben datumsfrei und konto-privat | Todo-Contract- und Account-Isolation-Suite |
| API-Vertrag | `backend/scripts/update-openapi`, Contract-Snapshot-Test |
