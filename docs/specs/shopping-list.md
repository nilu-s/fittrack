# Cronicl: Einkaufsliste und Mahlzeitenbedarf

**Status:** approved  
**Owner:** Cronicl household  
**Last updated:** 2026-09-02

## Ziel und Grenzen

Jedes Konto besitzt eine private Einkaufsliste. Zusätzlich kann ein Space eine
gemeinsame manuelle Liste besitzen; deren Mitgliedschaft und Grenzen regelt
`shared-spaces.md`. Die private Liste ist ein eigener
Arbeitsbereich, kein Tages-To-do und keine automatische Änderung des
Mahlzeitenplans. Sie kann Zutaten aus dem aktiven Plan für einen explizit
gewählten Horizont von 1 bis 14 Tagen übernehmen.

Vorratsverwaltung, Barcode-Scanning, externe Kataloge und
Produktfotos sind nicht Teil dieses Releases. Artikel verwenden ausschließlich
lokale, skizzierte SVG-Icons.

## Daten- und Übernahmeregeln

* Der Server bestimmt das Konto ausschließlich aus der Session; weder API noch
  Browser akzeptieren ein Owner-Feld.
* Ein Artikel hat Titel, Kategorie, Icon, optionale Menge/Einheit, Status und
  nachvollziehbare Quelle. Fremde Artikel-IDs ergeben 404.
* Die Planübernahme liest den aktiven Plan für das inklusive Datumsintervall
  `heute .. heute + horizon_days - 1`. Sie ändert Plan, Rezepte und bestehende
  Mahlzeiteneinträge nie.
* Direkte Zutaten werden nach Lebensmittel-ID zusammengeführt. Die Menge ist
  `Zutatenmenge × geplante Portionen ÷ Rezeptportionen`; verschachtelte Rezepte
  werden rekursiv in ihre direkten Lebensmittel aufgelöst. Nur Gramm werden
  für Lebensmittel importiert; freie Planplätze ohne Rezept werden übersprungen.
* Offene gleiche Lebensmittelposten werden addiert. Bereits erledigte Artikel
  bleiben historische Kaufnotizen und werden nie verändert. Manuelle Artikel
  bleiben manuell; eine Übernahme kann ihren Ursprung zu `mixed` ergänzen.
* Die Zuordnung Kategorie/Icon ist ein lokaler, deterministischer Katalog mit
  sicherem Fallback `Sonstiges`. Nutzer können Kategorie, Icon und Menge
  anschließend bearbeiten.

## UX-Vertrag

* Der Footer der Tagesansicht hat eine sichtbare Schaltfläche „Einkauf“. Sie
  öffnet einen mobilen, höhenverstellbaren Einkaufsbereich; Ziehen ist nur ein
  Beschleuniger. Der Bereich folgt dem im Fokus-Rad gewählten privaten oder
  gemeinsamen Space-Kontext. Desktop zeigt stattdessen eine rechte,
  gleichwertig bedienbare Seitenleiste.
* Im geöffneten Bereich wird die Tages-To-do-Eingabe eindeutig durch die
  Artikelsuche ersetzt. Beide Eingabewerte bleiben getrennt erhalten.
* Suche schlägt eigene offene und erledigte Artikel sowie den lokalen Katalog
  vor, akzeptiert aber immer freien Text. Checkbox, Detailbearbeitung,
  Schließen und Mahlzeitenübernahme sind sichtbare, native Controls.
* Öffnen fokussiert die Artikelsuche, Schließen stellt den Fokus zum Auslöser
  zurück. Escape und ein sichtbarer Schließen-Button schließen den Bereich.

## Akzeptanz und Verifikation

| Verpflichtung | Verifikation |
| --- | --- |
| Account A kann keine Daten von B lesen oder ändern | `backend/tests/test_shopping_contract.py` |
| Mengen- und Portionsaggregation ist deterministisch | `backend/tests/test_shopping_contract.py` |
| Keine Owner-Felder im Browservertrag, neue Routes sichtbar | `backend/tests/test_shopping_contract.py`, `docs/contracts/openapi.json` |
| Footer, Suche und Verwaltung sind tastatur- und touchbedienbar | `frontend` check/build und Accessibility-Review |
| Bestehende To-do- und Mahlzeitenflüsse bleiben erhalten | Backend- und Frontend-Gesamtgates |
