# ADR 0002: Gedämpft helles Product UI

**Status:** Accepted  
**Datum:** 2026-09-01

## Entscheidung

FitTrack entwickelt die Produktoberfläche als gedämpft helles, datenorientiertes
Interface weiter. Es wird kein reinweißes Theme und kein zweites paralleles
Theme-System eingeführt.

Die Startseite gliedert sich sichtbar in Bereiche. Die gemischte Tagesliste
bleibt ihr handlungsorientierter Kern. Mahlzeiten und Training sind darin
erkennbar eigene Feature-Elemente mit spezialisierter Detail- und
Bearbeitungsfunktion; einfache Aufgaben bleiben kompakte Zeilen. Biometrische
Daten werden beobachtet, nicht als To-do behandelt.

## Begründung

Die bisherige dunkle Ausrichtung passt nicht mehr zur gewünschten visuellen
Richtung. Reines Weiß wäre für die datenreiche tägliche Nutzung zu hart. Eine
gedämpfte, helle Flächenhierarchie schafft klare Trennung ohne Kartenstapel,
starke Schatten oder dekorative Effekte.

## Folgen

- Die Regel "Dark only" in `frontend/docs/design-system.md` ist überholt und
  wird im Design-System-Migrationspaket durch diese Entscheidung ersetzt.
- Neue UI nutzt semantische Tokens und keine neuen lokalen Farbpaletten.
- Gradients, Glow und Glassmorphism bleiben ausgeschlossen.
- Long-Press, Double-Tap und Drag dürfen keine unverzichtbaren Aktionen sein.
- Das Redesign verändert keine API-, Account-, Sync- oder Gesundheitsdaten-
  Verträge.

## Verwandte Dokumente

- `docs/design/fittrack-ui-direction.md`
- `docs/design/fittrack-day-feed-interaction.md`
