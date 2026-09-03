# Cronicl: Notizen und Bereiche

**Status:** approved  
**Owner:** Cronicl household  
**Last updated:** 2026-09-03

## Ziel

Eine Notiz beginnt immer im privaten Eingang ihres Erstellers. Ein Bereich
ist die einzige gemeinsame Ablage- und Berechtigungsgrenze: Wird eine Notiz
einem Bereich zugeordnet, dürfen ausschließlich dessen aktive Mitglieder sie
sehen und bearbeiten. Die frühere Projekt-Ebene ist für neue Notizen und
geplante To-dos nicht Teil der Produktoberfläche.

Notizen sind ungeplante Inhalte; To-dos sind terminierte, direkt erledigbare
Tagesaufgaben. Das Board macht die erste sichtbar, der Day Feed ausschließlich
die zweite Art sichtbar.

## Modell und Übergänge

1. Eine `Note` hat Titel, optionalen Text, Sortierung, Ersteller und optional
   einen Bereich. Ohne Bereich ist sie privat und nur für den Ersteller lesbar.
2. Der private Eingang zeigt bis zu neun unzugeordnete Notizen als Raster.
   Weitere Einträge bleiben über die vollständige Liste erreichbar.
3. Jede Bereichszuordnung oder der Wechsel in einen anderen Bereich benötigt
   eine explizite Bestätigung. Die Mitgliedschaft wird serverseitig geprüft;
   die Browserdaten entscheiden nie über ein Konto oder eine Berechtigung.
4. Das Ablegen einer Notiz auf einen Kalendertag erzeugt ein ganztägiges To-do;
   das Ablegen auf einen Zeit-Slot erzeugt ein To-do mit Startzeit. Das To-do
   behält die Bereichszuordnung der Notiz und verweist auf seine Ursprungsnotiz.
5. Eine geplante Notiz kann zurück ins Board geholt werden. Der abgeleitete
   offene To-do-Eintrag wird dann entfernt und die Notiz wieder aktiv. Erledigte
   To-dos werden nicht stillschweigend gelöscht.
6. Drag-and-drop ist ein Beschleuniger. Bereichszuordnung, Planung und
   Entplanung haben immer sichtbare native Bedienelemente und Tastaturpfade.

## Bereichs- und Datenschutzregeln

- Private Notizen bleiben kontoprivat, bis der Ersteller das Teilen bestätigt.
- Mitglieder eines Bereichs haben Zugriff auf dessen Notizen und die daraus
  abgeleiteten manuellen To-dos. Das Entfernen der Mitgliedschaft entzieht den
  Zugriff sofort.
- Eine geteilte Notiz wird nicht durch Verschieben in den privaten Eingang
  unsichtbar gemacht. Eine private Kopie ist ein bewusster, späterer Vorgang.
- Kalender-, Google-, Standort- und Routineintegrationen bleiben privat. Ein
  gemeinsames aus einer Notiz geplantes To-do hat keine dieser Integrationen.

## Abnahmebedingungen

| Verpflichtung | Verifikation |
| --- | --- |
| Neue Notiz ist nur für ihren Ersteller sichtbar | API-Isolationstest für `GET /notes` |
| Private Notiz kann ohne `confirm_share` nicht geteilt werden | API-Contract-Test für Bereichszuordnung |
| Bereichsmitglied sieht Notiz und abgeleitetes To-do; Nichtmitglied nicht | API-Isolationstest |
| Tag- und Zeit-Slot-Planung setzen Datum bzw. Startzeit und Bereich korrekt | API-Contract-Test |
| Board bietet für Drag-Ziele sichtbare Button-Alternativen sowie fokussierbare Details | Frontend check/build und Accessibility Review |
| Tagesfeed enthält weiterhin nur terminierte To-dos | Day-Feed-Regressionstest |

## Übergang

`space_projects` und die bestehenden Projektfelder bleiben vorübergehend zur
Lesbarkeit alter Daten und für kompatible API-Antworten bestehen. Sie werden
nicht mehr im Board oder im neuen To-do-Fluss erzeugt bzw. angezeigt. Entfernung
erst nach einer bestätigten Daten-Migrationsentscheidung und wenn keine
unterstützte Installation mehr Projektdaten nutzt.

## Revisionswirkung

Diese Spezifikation supersedes die Aussagen zu Projekten und zur allgemeinen
Footer-To-do-Liste in `shared-spaces.md` und `cronicl-day-feed-interaction.md`.
Die Mitgliedschafts-, Konto- und Gesundheitsgrenzen bleiben unverändert.
