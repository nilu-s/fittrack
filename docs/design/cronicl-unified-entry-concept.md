# Einheitliche Eingabe: Konzept nach Session-Abgleich

Status: ersetzt durch [Gemeinsame Eingabe und ausführbarer KI-Assistent](../specs/unified-entry-and-assistant.md), autorisiert durch den Umsetzungsauftrag vom 10.09.2026. Dieses Dokument erläutert die Richtung; normative Anforderungen und Abnahme stehen im Nachfolger und im [Umsetzungsplan](../plans/2026-09-10-unified-entry-implementation.md).

## Korrigierte Richtung

Eine kompakte Footer-Eingabe mit Plus und separatem AI-Button bleibt der gemeinsame Einstieg. Der geöffnete Inhalt bestimmt den Zweck: Tages-To-do, Notiz oder Einkaufsartikel. Enter/Plus legt einfache Einträge unmittelbar an. Eindeutige deutsche Datums-, Uhrzeit- und Wiederholungsangaben werden lokal erkannt. KI wird ausschließlich ausdrücklich gestartet.

Der AI-Button öffnet den bestehenden Chat oben am Viewport. Er unterstützt Fragen, Erstellung und gezielte Änderungen. Strukturierte Ergebnisse sind bearbeitbar; zusammenhängende Vorschläge werden bewusst übernommen. Die gespeicherten Inhalte erscheinen in den vorhandenen Fachansichten. Vollständige manuelle Editoren bleiben unabhängig von KI erreichbar. Bekannte Gerichtsauswahl bleibt eine direkte Aktion.

Ein ausdrücklich geöffneter Notizbereich ist das Ziel neuer Notizen aus dem Footer. Ohne Bereichsziel bleiben Notizen privat. Mitgliedschaft wird serverseitig geprüft. Header und Footer bleiben beim Inhaltswechsel stabil. Öffnen einer Ansicht oder eines Dialogs aktiviert keine mobile Tastatur ungefragt; ein Detaildialog zur Zeit.

## Zurückgenommene Annahmen

Der ursprüngliche Entwurf führte eine permanente Typauswahl, eine automatisch erscheinende Attributleiste und eine zusätzliche KI-Vorschaufläche über dem Footer ein. Diese Ansätze passen nicht zur gewünschten kompakten Eingabe und zum bestehenden Chat. Ebenso zurückgenommen sind der Verzicht auf lokale Datumserkennung und die pauschale Regel, neue Notizen müssten auch im geöffneten Bereich erst privat entstehen.

Die Quellen für diese Korrektur sind die Cronicl-Sessions „Analysiere gestrige Sessions“, „Notizboard übersichtlicher gestalten“ und die früheren Eingabe-/KI-Entscheidungen. Insbesondere korrigierte der Nutzer im Notizboard ausdrücklich: Im geöffneten Bereich soll die Footer-Eingabe direkt dort Notizen anlegen. Die kompakte Footer-Richtung ist zusätzlich durch die Commits `622bc76` und `107ae94` nachvollziehbar.

## Umsetzung und Nachweis

Der Umsetzungsplan enthält A1–A15 für direkte Erfassung, manuelle Fachfelder, ausführbare KI-Vorschläge, Paketwiederholung, Kontotrennung und Browserabnahme. Ein bestandener Build allein erfüllt diese Kriterien nicht. Der aktuelle Fortschritt wird ausschließlich dort dokumentiert; dieser Konzepttext behauptet keine abgeschlossene Implementierung.
