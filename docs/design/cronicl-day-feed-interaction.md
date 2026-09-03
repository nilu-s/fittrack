# Cronicl Day Feed: Interaktionsvertrag

## Zweck

Die Tagesansicht verbindet persönliche Aufgaben, Ernährung und Training in
einem Ablauf, ohne die unterschiedlichen Funktionen dieser Einträge zu
vereinheitlichen.

## Bereichsmodell

1. **Tagesstatus:** Datum, Fortschritt und höchstens eine relevante nächste
   Handlung.
2. **Biometrie:** Gewicht, Schritte und Schlaf als Beobachtungsbereich;
   niemals durch einen Erledigt-Status verfälschen.
3. **Tagesliste:** offene und erledigte To-dos, Mahlzeiten und Training in
   einer nachvollziehbaren Reihenfolge.
4. **Schnellerfassung:** sichtbarer Einstieg zum Ergänzen einer Aufgabe oder
   eines passenden Tagesinhalts.
5. **Listen-Kontext:** Direkt über der Tagesnavigation im Footer wählt eine
   horizontale, antipp- und wischbare Leiste „Privat“ oder einen gemeinsamen
   Bereich für die allgemeine To-do- und Einkaufsliste. Sie ersetzt keine
   Tagesansicht und beeinflusst weder Datum noch persönliche Tagesinhalte.

## Eintragstypen

| Typ | Darstellung in der Liste | Primäre Aktion | Detailfluss |
| --- | --- | --- | --- |
| To-do | kompakte Zeile mit Status | erledigen | sichtbares Aktionsmenü oder Editor |
| Mahlzeit | informativer Listeneintrag | Status setzen oder öffnen | eigener Meal-Editor mit Zutaten und Nährwerten |
| Training | informativer Listeneintrag | öffnen oder abschließen | eigener Trainingsdetailfluss mit Übungen |
| Biometrie | separater Beobachtungswert | Wert ansehen/bearbeiten, sofern erlaubt | Mess- bzw. Trenddetail |

## Bedienungsregeln

- Jede Hauptaktion ist sichtbar und per Tastatur, Touch und Screenreader
  erreichbar.
- Gesten können beschleunigen, dürfen aber keine notwendige Funktion
  verstecken.
- Dialoge und Sheets stellen Fokus beim Öffnen sinnvoll ein und geben ihn beim
  Schließen zum Auslöser zurück.
- Der Bereichswechsler hat sichtbare Vor-/Zurück-Schaltflächen und einen
  nativen Button für jeden Bereich; Wischen ist nur ein Beschleuniger.
- Erledigte Einträge dürfen nur dann ans Ende wandern, wenn die Zeitreihenfolge
  dadurch nicht die Verständlichkeit des Tages verliert. Die endgültige Regel
  wird vor der Umsetzung an Beispiel-Tagen entschieden.

## Grenzen

Dieser Vertrag entscheidet Informationsstruktur und Verhalten. Farbwerte,
Typografie und Backend-Datenverträge werden hier nicht festgelegt.

Der Tagesfeed bleibt immer ein einheitlicher Ablauf. Private und geteilte
To-dos mit Datum erscheinen gemeinsam in ihrer normalen Zeitreihenfolge;
geteilte Einträge tragen ein kompaktes Bereichs-Label. Biometrie, Mahlzeiten,
Training und Integrationen bleiben privat. Der Listen-Kontext im Footer wählt
nur die jeweils geöffnete allgemeine To-do- oder Einkaufsliste sowie den
Zielbereich für neue Footer-Einträge.
