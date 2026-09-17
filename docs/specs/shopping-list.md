# Cronicl: Einkaufsliste und Mahlzeitenbedarf

**Status:** approved (revised 2026-09-17: Pictogramicl delivery)
**Owner:** Cronicl household  
**Last updated:** 2026-09-17

## Ziel und Grenzen

Jedes Konto besitzt eine private Einkaufsliste. Zusätzlich kann ein Space eine
gemeinsame manuelle Liste besitzen; deren Mitgliedschaft und Grenzen regelt
`shared-spaces.md`. Die private Liste ist ein eigener
Arbeitsbereich, kein Tages-To-do und keine automatische Änderung des
Mahlzeitenplans. Sie kann Zutaten aus dem aktiven Plan für einen explizit
gewählten Horizont von 1 bis 14 Tagen übernehmen.

Vorratsverwaltung, Barcode-Scanning, externe Kataloge und Produktfotos sind
nicht Teil dieses Releases. Cronicl übernimmt keine Icon-Dateien,
Produktbilder oder geschützte UI-Elemente anderer Einkaufs-Apps. Piktogramme
werden ausschließlich über den account-geschützten Pictogramicl-Proxy bezogen;
vor dessen Antwort zeigt die Kachel Titelinitialen statt eines generischen Symbols.

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
* Der Server übermittelt nur einen öffentlichen, sicheren Begriff an
  Pictogramicl und liefert dessen Bild ausschließlich über eine account- und
  Space-geschützte Item-Route aus. Der Browser erhält keine Service-Zugangsdaten
  und lädt keine direkte Drittanbieter-URL. Für Cache, Retry, zulässige Inhalte
  und Platzhalter ist `pictogram-catalog.md` maßgeblich.
  Für `Sonstiges` sind die ersten ein oder zwei Titelinitialen der verbindliche
  Fallback.
* Eine browserseitige Illustrationauswahl oder Übermittlung visueller Overrides
  existiert nicht. Pictogramicl ist allein für Generierung, Prüfung und
  Veröffentlichung zuständig.

## UX-Vertrag

* Der Footer der Tagesansicht hat eine sichtbare Schaltfläche „Einkauf“. Sie
  ersetzt den Tagesablauf im zentralen Inhaltsbereich; Kopfzeile, Tageswerte
  und Footer bleiben sichtbar. Der Bereich folgt dem im Fokus-Rad gewählten
  privaten oder gemeinsamen Space-Kontext und verwendet auf allen Bildschirmgrößen
  denselben Inhaltsbereich.
* Im geöffneten Bereich wird die Tages-To-do-Eingabe eindeutig durch die
  Artikelsuche ersetzt. Beide Eingabewerte bleiben getrennt erhalten.
* Suche schlägt eigene offene und erledigte Artikel sowie den lokalen Katalog
  vor, akzeptiert aber immer freien Text. Checkbox, Detailbearbeitung,
  Schließen und Mahlzeitenübernahme sind sichtbare, native Controls.
* Das Öffnen fokussiert die Artikelsuche nicht und öffnet keine Bildschirmtastatur.
  Escape und ein sichtbarer Schließen-Button schließen den Bereich.

## Akzeptanz und Verifikation

| Verpflichtung | Verifikation |
| --- | --- |
| Account A kann keine Daten von B lesen oder ändern | `backend/tests/test_shopping_contract.py` |
| Mengen- und Portionsaggregation ist deterministisch | `backend/tests/test_shopping_contract.py` |
| Keine Owner-Felder im Browservertrag, neue Routes sichtbar | `backend/tests/test_shopping_contract.py`, `docs/contracts/openapi.json` |
| Footer, Suche und Verwaltung sind tastatur- und touchbedienbar | `frontend` check/build und Accessibility-Review |
| Unzugeordnete Artikel zeigen Titelinitialen, nicht ein generisches Icon | `frontend/scripts/test-shopping-tiles-ui.mjs` |
| Proxy, Cache und Pictogramicl-Platzhalter schützen Kontodaten | `backend/tests/test_pictogramicl.py` |
| Vor der Piktogramm-Antwort zeigen Kacheln Initialen; keine browserseitige visuelle Übersteuerung existiert | `frontend/scripts/test-shopping-tiles-ui.mjs`, `frontend/scripts/test-shopping-icon-engine-ui.mjs`, `npm run check` |
| Bestehende To-do- und Mahlzeitenflüsse bleiben erhalten | Backend- und Frontend-Gesamtgates |
