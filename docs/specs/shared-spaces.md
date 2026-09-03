# Cronicl: Gemeinsame Spaces

**Status:** approved  
**Owner:** Cronicl household  
**Last updated:** 2026-09-03

## Ziel

Ein Bereich ist ein ausdrücklich gemeinsamer Arbeitsbereich, etwa „Haushalt“.
Er fasst geteilte Notizen, daraus geplante To-dos und manuell gepflegte Einkaufslisten zusammen und
ist ein Kontext der vorhandenen Arbeitsabläufe, keine zweite Startseiten- oder
Listenoberfläche.
Persönliche Fitness-, Gesundheits-, Ernährungs-, Trainings- und Google-Daten
bleiben immer kontoprivat. Ein Space erweitert weder die Sitzung noch die
Kontoberechtigungen außerhalb seiner eigenen Ressourcen.

## Zugriff und Mitgliedschaft

1. Ein angemeldetes Konto kann einen Space erstellen und ist dessen Owner.
   Der Owner kann Namen ändern, Mitglieder einladen und entfernen; er kann
   nicht selbst entfernt werden.
2. Einladungen wählen einen bereits bestätigten Kontakt. Erst die sichtbare
   Annahme im Kontakte-Bereich erzeugt dessen Workspace-Mitgliedschaft. Eine
   freie E-Mail-Eingabe in der Workspace-Verwaltung ist ausgeschlossen. Der
   neue Bereich wird beim anderen Konto beim nächsten Fokus oder spätestens
   innerhalb von fünf Sekunden im Wheel geladen.
3. Owner und aktive Mitglieder dürfen die Inhalte eines Space lesen, anlegen,
   bearbeiten, erledigen und löschen. Eine entfernte Mitgliedschaft verliert
   sofort jeden Zugriff. Private Ressourcen eines Kontos werden dadurch nie
   sichtbar.
4. Der Server prüft die Mitgliedschaft für jede Space-Ressource. Eine vom
   Browser mitgelieferte `space_id`, `project_id` oder `assignee_id`
   ist ausschließlich eine Ressourcenreferenz und wird serverseitig gegen die
   Mitgliedschaft validiert; sie bestimmt nie den angemeldeten Account.

## Notizen und To-dos

1. Ein Bereich ist die einzige gemeinsame Ablage- und Berechtigungsgrenze.
   Private Notizen werden erst durch die bewusste Zuordnung zu einem Bereich
   für dessen aktive Mitglieder sichtbar; es gibt keine fachliche
   Projekt-Ebene für neue Notizen oder To-dos.
2. Ein Bereichs-To-do kann keiner oder genau einer aktiven Space-Mitgliedschaft
   zugewiesen sein. Die Antwort enthält nur die notwendige Anzeigeinformation
   (ID und Anzeigename) der zugewiesenen Person.
3. Wiederkehrende To-dos, Google-Kalender-Importe und Standort-/Anreise-Checks
   bleiben privat. Sie können nicht in einen Space verschoben oder dort
   erstellt werden, weil ihr Ausführungs- oder Integrationskontext persönlich
   ist.
4. „Privat“ und jeder Bereich sind getrennte Listen-Kontexte. Der private
   Tagesablauf zeigt nur private To-dos; ein Space zeigt nur dessen To-dos.
   Beide Kontexte verwenden dieselbe Tageslisten-Komponente und denselben
   Detailfluss, nicht separate Oberflächen.
5. Oberhalb des Inhalts zeigt eine schmale Rollenanzeige den aktiven Bereich
   mittig und den vorherigen sowie nächsten Bereich zurückhaltend daneben.
   Ein horizontaler Wisch im gesamten Inhaltsbereich oberhalb der festen
   Footer-Navigation wechselt den Kontext; die sichtbaren Bereichsnamen sind
   zusätzlich antippbar. Der Footer-Einkauf verwendet immer den aktiven
   Kontext. Neue Notizen beginnen dagegen immer privat im Notiz-Board und
   werden erst bewusst einem Bereich zugeordnet.
   Ein Long-Press auf den aktiven Space öffnet dessen Einstellungen als mobilen
   Schnellzugriff. Die mittige Bereichsbezeichnung ist zugleich ein sichtbarer,
   per Tastatur bedienbarer Weg dorthin; „Privat“ hat keinen entsprechenden
   Link. Die Verwaltung bleibt ausschließlich unter Einstellungen verfügbar.
6. In der Tagesansicht bleiben To-dos kompakte, direkt abschließbare Einträge.
   Bereich und Zuweisung sind im Editor als native Auswahlfelder sichtbar.

## Einkaufslisten

1. Jeder Space kann eine aktive gemeinsame manuelle Einkaufsliste haben.
   Alle Mitglieder können Artikel anlegen, bearbeiten und abhaken. Dieselbe
   Einkaufsansicht und derselbe Footer-Drawer werden kontextbezogen genutzt;
   es gibt keinen separaten Space-Einkaufszugang.
2. Die private Einkaufslisten- und Mahlzeitenplan-Übernahme bleibt privat.
   Eine Planübernahme in eine gemeinsame Liste ist ausgeschlossen, da sie
   private Lebensmittel- und Planinformationen offenlegen würde.

## Übergang und Verifikation

Bestehende To-dos und Listen bleiben privat (`space_id = NULL`). Die neue
Migration ist rückwärtskompatibel und hat keine automatische Freigabe.

Mitgliedschaften und Einladungen werden ausschließlich unter Einstellungen
verwaltet. Sie erscheinen nicht als Verwaltungsblock im Tagesfeed. Der
Header darf einen direkten Einstieg in diese Einstellungen anbieten. Kontakte
sind ein separater Bereich gemäß `contacts.md` und geben keine Workspace-
Berechtigung.

| Verpflichtung | Verifikation |
| --- | --- |
| Nichtmitglieder können keine Space-Inhalte lesen oder ändern | `backend/tests/test_shared_spaces_contract.py` |
| Kontakte erzeugen sofort Mitgliedschaft; Entfernen entzieht Zugriff | `backend/tests/test_shared_spaces_contract.py` |
| Bereichsmitgliedschaften begrenzen gemeinsame Notizen und daraus geplante To-dos | `backend/tests/test_notes_contract.py`, account-isolation integration suite |
| Gesundheits-, Integrations- und private Listen bleiben privat | Account-Isolation-Suite und Shopping-Contract |
| Sichtbare und zugängliche Auswahlfelder | `npm run check`, `npm run lint:design`, `npm run build` |
| Long-Press ist nur Beschleuniger; der Dialog ist per Tastatur erreichbar | `npm run check`, `npm run lint:design`, manuelle Tastatur-/Touch-Prüfung |

## Revisionswirkung

Diese Spezifikation revidiert ausschließlich die Aussagen „Haushaltsfreigaben
ausgeschlossen“ in `multi-account-scale-and-body-composition.md`,
`todo-places-and-travel.md` und `shopping-list.md`. Alle übrigen
Kontentrennungs-, Scale- und Gesundheitsregeln bleiben unverändert.
