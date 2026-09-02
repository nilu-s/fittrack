# Cronicl CNL-Checkbox

## Zweck

`cronicl-cnl-master.svg` ist die Masterdatei für das Cronicl-Zeichen.
Sie überführt die freigegebene gestalterische Idee in eine editierbare,
skalierbare SVG. Die Datei ist bewusst transparent: Der Hintergrund kommt
immer von der jeweiligen Produktfläche.

## Zeichenlogik

Das Logo ist keine Checkbox mit drei hineingesetzten Buchstaben. Es ist eine
offene, zusammenhängende CNL-Konstruktion:

- Das obere, linke und untere Außenband zeichnet ein weiches, bewusst offenes
  **C** und zugleich die Andeutung einer Checkbox.
- Der linke Stamm des **N** beginnt im unteren linken Bruch. Das N wächst
  dadurch aus der Außenkontur, statt im Rahmen zu stehen.
- Die lange untere Führung und der rechte Aufzug tragen das **L** als Teil der
  Außenform.
- Der salbeigrüne Haken steht für erledigt. Er bleibt vom dunklen Monogramm
  getrennt und verbindet die Form nur optisch über seine Diagonale.

Die Unterbrechungen und Freiräume sind Teil des Zeichens. Sie dürfen nicht
geschlossen, symmetrisiert oder durch einen Standard-Checkbox-Rahmen ersetzt
werden.

## Form- und Farbregeln

- Die Masterdatei nutzt einen `512 × 512`-ViewBox ohne feste Ausgabegröße.
- Dunkle Struktur: `#264235`.
- Haken/Aktion: `#8ba47d`.
- Keine Verläufe, Schatten, Glow, zusätzlichen Piktogramme oder Wortmarke in
  der Masterdatei.
- Die Strichenden sind rund; der N-Zug hat absichtlich einen kantigeren
  Abschluss.
- Das Zeichen darf für enge Flächen skaliert, aber nicht horizontal oder
  vertikal gestaucht werden.

## Verwendung

Die Masterdatei ist ein Entwurfsasset und ersetzt noch keine Dateien in
`frontend/static/`. Erst nach einer visuellen Freigabe wird sie in die
Favicon- und PWA-Varianten übertragen und in kleinen Größen geprüft.

## Dateien

| Datei | Rolle |
| --- | --- |
| `cronicl-cnl-master.svg` | Transparente, editierbare Quelle des Zeichens. |
| `README.md` | Konzept und Schutzregeln für spätere Anpassungen. |
