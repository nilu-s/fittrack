# Cronicl: Gemeinsame Spaces

**Status:** approved  
**Owner:** Cronicl household  
**Last updated:** 2026-09-03

## Ziel

Ein Space ist ein ausdrücklich gemeinsamer Arbeitsbereich, etwa „Haushalt“.
Er fasst Projekte, To-dos und manuell gepflegte Einkaufslisten zusammen.
Persönliche Fitness-, Gesundheits-, Ernährungs-, Trainings- und Google-Daten
bleiben immer kontoprivat. Ein Space erweitert weder die Sitzung noch die
Kontoberechtigungen außerhalb seiner eigenen Ressourcen.

## Zugriff und Mitgliedschaft

1. Ein angemeldetes Konto kann einen Space erstellen und ist dessen Owner.
   Der Owner kann Namen ändern, Mitglieder einladen und entfernen; er kann
   nicht selbst entfernt werden.
2. Einladungen adressieren eine bereits zugelassene Konto-E-Mail. Sie geben
   weder Konto-IDs noch andere Daten an den Browser preis. Erst die explizite
   Annahme erzeugt eine Mitgliedschaft. Nur eingeladene Konten können die
   Einladung sehen oder annehmen/ablehnen.
3. Owner und aktive Mitglieder dürfen die Inhalte eines Space lesen, anlegen,
   bearbeiten, erledigen und löschen. Eine entfernte Mitgliedschaft verliert
   sofort jeden Zugriff. Private Ressourcen eines Kontos werden dadurch nie
   sichtbar.
4. Der Server prüft die Mitgliedschaft für jede Space-Ressource. Eine vom
   Browser mitgelieferte `space_id`, `project_id` oder `assignee_id`
   ist ausschließlich eine Ressourcenreferenz und wird serverseitig gegen die
   Mitgliedschaft validiert; sie bestimmt nie den angemeldeten Account.

## Projekte und To-dos

1. Projekte gehören genau zu einem Space und enthalten beliebig viele
   To-dos. Ein To-do kann privat bleiben oder genau einem Space und optional
   einem Projekt angehören. Ein Projekt ohne passenden Space ist ungültig.
2. Ein Space-To-do kann keiner oder genau einer aktiven Space-Mitgliedschaft
   zugewiesen sein. Die Antwort enthält nur die notwendige Anzeigeinformation
   (ID und Anzeigename) der zugewiesenen Person.
3. Wiederkehrende To-dos, Google-Kalender-Importe und Standort-/Anreise-Checks
   bleiben privat. Sie können nicht in einen Space verschoben oder dort
   erstellt werden, weil ihr Ausführungs- oder Integrationskontext persönlich
   ist.
4. In der Tagesansicht bleiben To-dos kompakte, direkt abschließbare Einträge.
   Space und Zuweisung sind im Editor als native Auswahlfelder sichtbar; bei
   Änderung des Space wird ein unpassendes Projekt oder eine unpassende
   Zuweisung zurückgesetzt. Tastatur, Touch und Screenreader erreichen alle
   Funktionen gleichwertig.

## Einkaufslisten

1. Jeder Space kann eine aktive gemeinsame manuelle Einkaufsliste haben.
   Alle Mitglieder können Artikel anlegen, bearbeiten und abhaken.
2. Die private Einkaufslisten- und Mahlzeitenplan-Übernahme bleibt privat.
   Eine Planübernahme in eine gemeinsame Liste ist ausgeschlossen, da sie
   private Lebensmittel- und Planinformationen offenlegen würde.

## Übergang und Verifikation

Bestehende To-dos und Listen bleiben privat (`space_id = NULL`). Die neue
Migration ist rückwärtskompatibel und hat keine automatische Freigabe.

| Verpflichtung | Verifikation |
| --- | --- |
| Nichtmitglieder können keine Space-Inhalte lesen oder ändern | `backend/tests/test_shared_spaces_contract.py` |
| Einladung braucht Annahme; Entfernen entzieht Zugriff | `backend/tests/test_shared_spaces_contract.py` |
| Projekte, Zuweisungen und To-dos sind im selben Space | `backend/tests/test_shared_spaces_contract.py` |
| Gesundheits-, Integrations- und private Listen bleiben privat | Account-Isolation-Suite und Shopping-Contract |
| Sichtbare und zugängliche Auswahlfelder | `npm run check`, `npm run lint:design`, `npm run build` |

## Revisionswirkung

Diese Spezifikation revidiert ausschließlich die Aussagen „Haushaltsfreigaben
ausgeschlossen“ in `multi-account-scale-and-body-composition.md`,
`todo-places-and-travel.md` und `shopping-list.md`. Alle übrigen
Kontentrennungs-, Scale- und Gesundheitsregeln bleiben unverändert.
