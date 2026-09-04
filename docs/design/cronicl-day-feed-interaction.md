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
   einer nachvollziehbaren Reihenfolge. Notizen und Einkauf können genau
   diesen Inhaltsbereich ersetzen, ohne Kopfzeile, Tageswerte oder Footer zu
   verändern.
4. **Schnellerfassung:** sichtbarer Einstieg zum Ergänzen einer Aufgabe oder
   eines passenden Tagesinhalts.
5. **Bereichsfokus:** Oberhalb des Inhalts zeigt eine schmale Rollenanzeige
   den aktiven Bereich mittig sowie den vorherigen und nächsten Bereich
   zurückhaltend daneben. Nur der austauschbare Inhaltsbereich unterhalb der
   Tageswerte und oberhalb der festen Footer-Navigation wechselt den Bereich
   per horizontalem Wisch; die sichtbaren Bereichsnamen sind zusätzlich
   antippbar.

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

Der Bereich ist ein Datenfilter, keine zweite Tagesdarstellung: Die identische
Tageslisten-Komponente zeigt im privaten Bereich nur private To-dos; in einem
gemeinsamen Bereich nur dessen To-dos. Neue Footer-Notizen starten immer
privat im Notiz-Board und werden erst durch eine bewusste Bereichszuordnung
geteilt; der Footer-Einkauf verwendet weiterhin den aktiven Bereich.
Biometrie, Mahlzeiten, Training und Integrationen bleiben privat. Die
Tageswerte Gewicht, Schritte, Schlaf und Energie bleiben beim Bereichswechsel
sichtbar; nur private Mahlzeiten und Training erscheinen nicht in der
gemeinsamen Tagesliste. Das private Notiz-Board bleibt beim Bereichswechsel
unverändert sichtbar; nur die Einkaufsliste lädt ihren aktiven Space-Kontext
nach.
