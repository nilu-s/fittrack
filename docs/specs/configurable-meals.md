# Cronicl: Konfigurierbare Mahlzeiten

**Status:** implemented (online-first)  
**Owner:** Cronicl household
**Last updated:** 2026-09-01

## 1. Zielbild

Jedes Konto kann seine Ernährung unabhängig konfigurieren, Mahlzeiten planen
und den tatsächlichen Verzehr erfassen. Der Bereich trennt dauerhaft drei
Ebenen:

```text
Lebensmittel + Rezepte -> Mahlzeitenplan -> Mahlzeiteneintrag am Tag
         Konfiguration       Planung             tatsächlicher Verlauf
```

Ein später verändertes Lebensmittel, Rezept oder Template darf niemals einen
historischen Tageswert verändern. Tageswerte sind daher stets reproduzierbare
Snapshots. Alle Daten sind privat je Konto; der Browser übermittelt nie einen
Owner oder eine fremde Ressourcen-ID als Berechtigung.

## 2. Umfang und Nicht-Ziele

Im ersten Release enthalten sind frei benennbare Mahlzeitenkategorien,
zwei je Kategorie pflegbare Standardgerichte für die Tages-Schnellauswahl,
Lebensmittel, Rezepte mit Zutaten, Tages-/Wochenpläne, Portionen, Planung und
Verzehr, Nährwert-Summen, Fotos und die Übernahme einer Fotoanalyse nach
expliziter Bestätigung.

Nicht Bestandteil dieses Bereichs sind ein öffentlicher Rezeptmarktplatz,
soziales Teilen, Barcode- oder externe Lebensmittelkataloge, automatische
KI-Übernahme ohne Bestätigung sowie medizinische Bewertungen. Die
Einkaufslisten-Erweiterung wird durch
[`shopping-list.md`](shopping-list.md) geregelt; sie liest den Mahlzeitenplan,
ohne ihn oder seine historischen Einträge zu verändern.

## 3. Fachmodell

| Entität | Zweck | Wesentliche Regeln |
| --- | --- | --- |
| `meal_categories` | Je Konto konfigurierbare Kategorien, z. B. Frühstück oder Snack | Name und Reihenfolge je Konto eindeutig; keine feste Anzahl und keine globalen Slots. |
| `meal_category_recipe_presets` | Schnellauswahl einer Kategorie | Höchstens zwei aktive, konto-eigene Rezepte in expliziter Reihenfolge. |
| `foods` | Lebensmittel mit Nährwerten je 100 g | Einheitliche Dezimalwerte; Quelle und Vertrauensniveau werden gespeichert. |
| `recipes` | Wiederverwendbares Gericht | Entwurf, aktiv oder archiviert; ergibt eine definierte Anzahl Portionen. |
| `recipe_ingredients` | Zutaten bzw. Unterrezepte eines Rezepts | Menge, Einheit und Reihenfolge; keine zyklischen Unterrezepte. |
| `meal_plan_templates` | Persönlicher Tages- oder Wochenplan | Versioniert; aktivierte Version ist klar bestimmt. |
| `meal_plan_template_items` | Ein geplanter Platz im Plan | Kategorie, lokale geplante Uhrzeit, Wochentagsregel, Rezept/freier Platzhalter und Sollportion. |
| `meal_entries` | Eine konkrete Mahlzeit eines Tages | Status `planned`, `consumed` oder `skipped`, Kategorie, Zeitpunkt, Quelle und Nährwert-Snapshot. Mehrere pro Kategorie/Tag sind erlaubt. |
| `meal_entry_items` | Komponenten eines Eintrags | Lebensmittel- oder Rezept-Snapshot, Menge und eigene Nährwert-Summen. |
| `meal_photos`, `meal_photo_analyses` | Foto und nachvollziehbare KI-Auswertung | Analyse enthält Modell-/Schema-Version, Ergebnis, Fehler und explizite Übernahmeentscheidung. |

`Meal`, `Dish` und `MealTemplate` sind retired. Laufzeit, Browser und CLI
verwenden ausschließlich das konto-gebundene `MealEntry`-Modell.

## 4. Verbindliche Regeln

1. Die API bestimmt `account_id` ausschließlich aus der verifizierten Session.
   Jede Ressourcenabfrage enthält zusätzlich `resource.account_id == current_account`.
2. Rezept- und Lebensmittelwerte werden serverseitig mit `Decimal` berechnet.
   Die Oberfläche kann nur eine Vorschau berechnen.
3. Nährwerte eines `meal_entry` und seiner Items sind Snapshots. Eine
   Rezeptänderung wirkt ausschließlich auf neue Einträge.
4. Alle Nährwertangaben sind entweder vollständig bekannt oder je Feld
   `null`; `0` bedeutet einen tatsächlich bekannten Nullwert. Die UI bezeichnet
   aus Fotoanalyse stammende Werte als „Schätzung“.
5. Energie wird in kcal, Masse in g und Flüssigkeit in ml gespeichert.
   Primäre Lebensmittelwerte gelten pro 100 g. Anzeige rundet kcal auf ganze
   Werte und Gramm auf eine Nachkommastelle, niemals die gespeicherten Werte.
6. Ein Plan instanziiert pro Konto, lokalem Datum, Planversion und
   Template-Item höchstens einen Eintrag. Der Vorgang ist idempotent und
   erzeugt nur `planned`-Einträge. Nach einer Planänderung oder einem
   Planwechsel werden offene Plan-Projektionen entfernt, die nicht exakt zur
   aktiven Planversion gehören. Manuelle, verzehrte und übersprungene Einträge
   bleiben unverändert; passende Einträge entstehen bei der nächsten
   Instanziierung erneut.
7. „Verzehrt“ und „übersprungen“ sind explizite Zustände; ein Toggle
   `is_done` ist kein Zieldatenmodell.
8. Fotoanalyse kann einen Entwurf liefern, darf aber keinen Eintrag, kein
   Rezept und kein Lebensmittel automatisch überschreiben oder veröffentlichen.

## 5. API-Spezifikation (v1-Zielvertrag)

Alle Endpunkte liegen unter `/api`, benötigen eine Browser-Session und nehmen
keine Owner-Felder an.

| Ressource | Operationen |
| --- | --- |
| Kategorien | `GET/POST /meal-categories`, `PUT/DELETE /meal-categories/{id}`, Reihenfolge aktualisieren |
| Kategorie-Schnellauswahl | `GET/PUT /meal-categories/{id}/recipe-presets`; maximal zwei aktive Rezepte |
| Lebensmittel | `GET/POST /foods`, `GET/PUT/DELETE /foods/{id}`, Suche nach Name/Tag |
| Rezepte | `GET/POST /recipes`, `GET/PUT/DELETE /recipes/{id}`, Zutaten nur atomar mit dem Rezept schreiben |
| Pläne | `GET/POST /meal-plans`, `GET/PUT/DELETE /meal-plans/{id}`, aktivieren/versionieren |
| Tagesplan | `POST /meal-entries/instantiate?date=`, idempotent; `GET /meal-entries?from=&to=` |
| Einträge | `POST /meal-entries`, `GET/PUT/DELETE /meal-entries/{id}`, `POST /meal-entries/{id}/consume`, `POST /meal-entries/{id}/skip` |
| Fotos | Upload zu einem bereits dem Konto gehörenden Eintrag; Analyse und Übernahme sind getrennte Aktionen |

Responses geben keine internen Owner-Felder aus. Mutationen akzeptieren weder
`account_id` noch `user_id`. Fremde IDs liefern 404, ohne Existenzdetails zu
leaken. Ändernde Requests tragen eine Versionskennung (`updated_at` oder ETag)
zur Konflikterkennung; bei Offline-Konflikten gewinnt nicht stillschweigend
der Client.

## 6. UX-Spezifikation

Die Tagesansicht zeigt zunächst Kategorien und geplante Einträge. Ein Eintrag
zeigt Status, Uhrzeit, Portion und Nährwert-Summe. „Verzehrt“ fließt in die
Tages- und Wochenbilanz ein; „geplant“ bleibt als Plan sichtbar, wird aber
separat ausgewiesen. Nutzer können zusätzliche Einträge in jeder Kategorie
anlegen und Kategorien umbenennen, sortieren oder deaktivieren.

Die Tageskachel heißt **„Nährstoffe“**. Ihre Detailansicht ist eine breite,
nach Makro- und Mikronährstoffen gegliederte Bilanz der als verzehrt markierten
Tagesmahlzeiten; sie zeigt keine Liste verzehrter Gerichte. Makros sind Energie, Protein, Kohlenhydrate, Fett,
Ballaststoffe, Zucker, freie Zucker und gesättigte Fettsäuren. Mikros sind
Natrium, Kalium, Calcium, Magnesium, Eisen, Zink sowie Vitamin A, C, D, B12
und Folat. Mengen werden mit ihrer Einheit angezeigt. Alle Nährwerte sind
Orientierungswerte, keine Messwerte oder medizinische Aussagen: Wenn eine
exakte Referenz fehlt, darf ein plausibler Standardwert verwendet werden und
muss als Schätzung gekennzeichnet sein. Die Übersicht gibt keine medizinischen
Bewertungen oder Zielwert-Ampeln ab.

Lebensmittel pflegen diese Werte pro 100 g. Die Migration ergänzt alle
bestehenden Lebensmittel um die neuen Felder. Neue und geänderte Einträge
übernehmen den gesamten Nährwert-Snapshot. Eine explizite, konto-gebundene
Anreicherung ergänzt historische Mikronährstofffelder aus den aktuell
gepflegten, konto-eigenen Lebensmittel- und Rezeptwerten. Sie verändert niemals
die ursprünglichen Makro-Snapshots; verwendete Standardwerte bleiben als
geschätzt nachvollziehbar. Die Oberfläche benennt sie als „nachträgliche
Anreicherung“, nicht als historische Messung.

Die Einstellungen erhalten einen eigenen Mahlzeitenbereich mit vier klaren
Unterseiten: Kategorien, Lebensmittel, Rezepte und Pläne. Die Tagesansicht
ist der Erfassungsort, nicht der alleinige Konfigurationsort. Der bestehende
Long-Press-Editor wird durch einen sichtbaren Bearbeiten-Dialog ersetzt; alle
Kernaktionen sind per Tastatur erreichbar.

Die bestehende Offline-Datenbank wird beim Konto-Wechsel vollständig gelöscht.
Der neue Mahlzeitenbereich ist bewusst **online-first**: jede Mutation trägt
eine `updated_at`-Revision und erhält bei einem Konflikt einen sichtbaren
Fehler statt eines stillen Last-write-wins. Eine persistente Offline-Outbox
für neue Mahlzeiten ist erst zulässig, wenn sie Abhängigkeiten (Food → Recipe
→ Plan → Entry), temporäre IDs und explizite Konfliktentscheidungen atomar
abbilden kann; sie darf nicht den Legacy-`/sync`-Pfad wiederverwenden.

## 7. Migration und Kompatibilität

Eine additive Alembic-Reihe führt zunächst die neuen Tabellen und Indizes ein.
Dann werden `dishes` als Rezepte und `meals` als Einträge mit erhaltenem
Nährwert-Snapshot überführt; `meal_templates` werden in Planvorlagen
überführt. Vorab prüft eine Rehearsal-Migration Konto-Zuordnung, doppelte
Defaults, ungültige Slots, verwaiste `dish_id`/`meal_id`-Referenzen und
Zeitzonen. Die historischen Tabellen und Endpunkte wurden nach dem Cutover
entfernt. Neue Änderungen dürfen keinen Read-Adapter, Offline-Sync oder
CLI-Befehl für das alte Modell wieder einführen.

## 8. Akzeptanzkriterien

- Konto A kann weder Mahlzeiten, Rezepte, Lebensmittel, Fotos noch Sync-Daten
  von Konto B lesen, ändern, löschen oder referenzieren.
- Eine Rezept- oder Lebensmitteländerung verändert keine historischen
  `meal_entry`-Summen oder -Items.
- Mehrere Einträge je Kategorie und Tag funktionieren; Planinstanziierung
  bleibt bei Wiederholung idempotent.
- Eine Planänderung entfernt nur veraltete offene Plan-Projektionen;
  manuelle, verzehrte und übersprungene Einträge bleiben erhalten.
- Portionen, Zutaten und Unterrezepte ergeben serverseitig korrekte Summen.
- Fotoergebnisse werden erst nach Bestätigung sichtbar als Verzehrwert und
  bleiben als versionierte Schätzung nachvollziehbar.
- Alembic-Migration, Backend-Vertragstests sowie Frontend-Check, Design-Lint
  und Build bestehen.

## 9. Vorgeschlagenes Spezifikationspaket vor der Implementierung

Dieses Dokument ist die gemeinsame Leitlinie. Vor dem jeweiligen
Implementierungspaket wird es in folgende einzeln freizugebende Spezifikationen
zerlegt; keine davon darf durch Codeänderungen stillschweigend entschieden
werden.

| Dokument | Entscheidet |
| --- | --- |
| `meals/00-product-scope-and-glossary.md` | Begriffe, MVP und Nicht-Ziele |
| `meals/01-domain-and-data-lifecycle.md` | ER-Modell, Ownership, Archivierung und Snapshots |
| `meals/02-user-flows-and-ux.md` | Konfiguration, Tageserfassung und Fehlerzustände |
| `meals/03-nutrition-and-portion-rules.md` | Einheiten, Rundung, unbekannte Werte und Quellen |
| `meals/04-api-contract.md` | DTOs, Fehler, Paginierung, Idempotenz und Versionskonflikte |
| `meals/05-offline-sync-and-conflicts.md` | Account-Cache, Outbox, Konfliktauflösung und Foto-Upload |
| `meals/06-photo-analysis-and-privacy.md` | Vorschlagsworkflow, Provenienz, Aufbewahrung und Zugriff |
| `meals/07-migration-and-compatibility.md` | Backfill, Read-Adapter, Rehearsal und Entfernungskriterium |
| `meals/08-authorization-and-test-matrix.md` | A-gegen-B-Matrix, DB-, API-, Sync- und E2E-Gates |
| `meals/09-nonfunctional-operations.md` | SLOs, Limits, Migration, Backups und Observability |
| `meals/10-data-rights-retention-and-export.md` | Export, Aufbewahrung, Löschung und Wiederherstellung |
| `meals/11-accessibility-and-responsive-ux.md` | WCAG, responsive Bedienung und Fehlerkommunikation |

Ergänzend sind vier ADRs vorgesehen: Snapshotting von Rezept zu Eintrag,
Aktivierung/Semantik von Plänen und Kategorien, Strategie für Nährwertquellen,
konto-gebundene Referenzen, Zeitmodell, Sync-Protokoll, Foto-Inferenz sowie
operative SLOs. Die priorisierten Release-Gates stehen im
[`Gap-Review`](../plans/2026-08-31-configurable-meals-gap-review.md).
