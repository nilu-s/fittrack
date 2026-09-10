# Gemeinsame Eingabe und ausführbarer KI-Assistent

Status: approved for implementation durch Nutzerauftrag 10.09.2026 nach historischem Abgleich. Owner: Cronicl household.

## Entscheidung

Die Tagesoberfläche behält eine kompakte Eingabe mit Plus und separatem KI-Button. Keine dauerhafte Typauswahl oder automatisch wachsende Werkzeugleiste. Plus verarbeitet eindeutige Datums-, Zeit- und einfache Wiederholungsangaben regelbasiert und legt direkt an. Details bleiben bewusst erreichbar, öffnen sich nicht nach jeder Erfassung. Notizen und Einkauf verwenden dasselbe kontextbezogene Footerfeld; sie ersetzen weiterhin nur den Inhaltsbereich. Explizit geöffnete Notizbereiche erlauben direkte Erstellung in diesem Bereich nach serverseitiger Mitgliedschaftsprüfung. Ohne Bereichsziel bleiben Notizen privat.

KI wird ausschließlich ausdrücklich gestartet und öffnet einen Chat am oberen Viewportrand. Antworten können strukturierte bearbeitbare Vorschläge enthalten; Fragen allein ändern keine Daten. Zusammenhängende Vorschläge werden einmal bewusst übernommen; Fachaktionen wie bekannte Gerichtsauswahl bleiben direkt. Nach Übernahme erscheinen Inhalte in den bestehenden Fachansichten und im gemischten Tagesfeed. Es gibt keinen parallelen KI-Datenbestand.

## Fachlicher Umfang

Erstellen und gezieltes Bearbeiten: To-dos, Notizen, Einkauf, Routinen, Lebensmittel, Rezepte, Mahlzeiten, Mahlzeitenpläne, Trainingseinheiten/Übungen und Rotation. Vollständige manuelle Bearbeitung aller dabei angebotenen Fachfelder ist Voraussetzung. Referenzen auf eigene bestehende Ressourcen dürfen wiederverwendet werden; neue abhängige Ressourcen eines Pakets werden sichtbar getrennt. Bestehende Inhalte dürfen nicht durch bloße Namensähnlichkeit überschrieben werden. Änderungsziele und Umfang müssen eindeutig vor Übernahme sichtbar sein.

Das System validiert alle Vorschläge wie manuelle Eingaben. KI-Ausgabe bestimmt niemals Konto, Berechtigung oder Besitzer. Private Ernährung, Training und Gesundheitsdaten werden nicht über einen Bereichsfilter geteilt. Zugriff auf benötigte eigene Ressourcen erfolgt serverseitig; Kontextnutzung wird im Chat angezeigt und bewusst gewählt. Keine Sitzung, Zugangsdaten, aktuellen Koordinaten oder vollständigen Gesundheitshistorien gehen an das Modell. Nährwerte werden fachlich berechnet; Schätzungen bleiben Schätzungen. Anreiseüberwachung/Standortrechte und Planaktivierung sind ausdrückliche Aktionen.

## Eingabe und Zustände

- Tagesbezug ist der sichtbar ausgewählte Referenztag. Erkannte Termine werden mit konkretem Datum rückgemeldet. Unsichere Angaben werden nicht erfunden.
- Lokale Schnellerkennung benötigt weder KI noch externe Ortssuche. Ort/Anreise können anschließend bewusst ergänzt werden.
- Ein vollständig manueller Fachweg existiert auch bei KI-Ausfall. Alle Zahlenfelder unterscheiden leer, 0 und ungültig und zeigen Einheiten.
- Chat erhält den Gesprächskontext für Folgeaufträge. Manuelle Entwurfskorrekturen werden nicht durch verspätete Antworten überschrieben.
- Fehler lassen Eingaben bestehen. Nur erfolgreiche Speicherung wird als angelegt bezeichnet. Doppelklick ist gesperrt; Paketwiederholung wiederholt keine bereits erfolgreichen Teile. Teilfehler benennen erfolgreiche und offene Aktionen ausdrücklich.
- Ein offener Dialog zur Zeit; sichtbare Schließen-/Bearbeiten-Aktionen, Escape, Fokus-Rückgabe. Öffnen fokussiert eine Nicht-Textaktion, damit keine mobile Tastatur ungefragt erscheint.
- Bestehende Notizplanung per Kalender/Drag-and-drop sowie private Rücknahme bleiben erhalten. Manuelle Controls sind gleichwertig.

## Revisionswirkung und Verifikation

Revidiert ausschließlich: `todo-places-and-travel.md` (rein beratender Chat zu bestätigten Schreibvorschlägen und lokalem Parser), `notes-and-areas.md` und Day-Feed-Vertrag (direkte Anlage im bewusst geöffneten Notizbereich), die Fachverträge um KI-Erstellung mit denselben manuellen Regeln. Alle Account-, Snapshot-, Bereichs- und Geräteinvarianten bleiben verbindlich. Kein zusätzlicher Export-/Lösch- oder Waagenadministrationsumfang.

Touchpoints: gemeinsame Eingabe/Chat/Editoren, Assistentenschemas/-services, Proxy-Prompt, Kontextbereitstellung, Ausführungsreferenzen und Fehler-/Wiederholungsbehandlung. Verifikation: Abnahmekriterien A1–A15 in `../plans/2026-09-10-unified-entry-implementation.md`; konkrete Tests und Ergebnisse werden im selben Paket dort nachgeführt. Legacy-KI-Planerdialog wird nach Anschluss des neuen Chats entfernt, damit kein zweiter inkompatibler Erfassungsweg bleibt.
