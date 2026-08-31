# Umsetzungsplan: konfigurierbare Mahlzeiten

**Status:** proposed — nach Freigabe der Spezifikation umsetzbar  
**Autoritative Grundlage:** [`../specs/configurable-meals.md`](../specs/configurable-meals.md)

## Ausgangslage

Die bestehende Anwendung besitzt bereits Tages-`meals`, `dishes`,
`meal_templates`, Standardgerichte, Portionsfaktoren und Fotoanalyse. Das ist
ein brauchbarer Prototyp, vermischt jedoch Katalog, Plan und Tagesverzehr. Die
nachstehende Reihenfolge erhält vorhandene Daten und vermeidet einen Big-Bang.

## Arbeitspakete

1. **Sicherheits- und Vertragsfundament**
   - Alle ID-Routen für Meal, Dish, Foto und Sync zusätzlich explizit mit dem
     aktuellen `account_id` filtern; Fremdzugriff erhält 404.
   - Contract-Tests für A-gegen-B, fremde Verknüpfungen, Soft-Delete und
     Offline-Replay ergänzen.
   - API-Schemas in Command-DTOs teilen: servergesteuerte Felder (Status,
     Analyse, Links) sind keine frei patchbaren Browserfelder.

2. **Neue persistente Domäne**
   - Per neuer, additiver Alembic-Revision `meal_categories`, `foods`,
     `recipes`, `recipe_ingredients`, `meal_plan_templates`,
     `meal_plan_template_items`, `meal_entries`, `meal_entry_items`,
     `meal_photos` und `meal_photo_analyses` anlegen.
   - Alle Tabellen mit nicht-null `account_id`, FK, Account-Indizes,
     Zeitstempeln und passenden Constraints erstellen; keine historische
     Migration ändern.
   - Berechnungs- und Instanziierungslogik in testbare Services auslagern.

3. **API und Datenmigration**
   - Zielvertrag aus der Spezifikation implementieren, OpenAPI-Snapshot und
     Request/Response-Contract-Tests ergänzen.
   - Rehearsal-Migration mit anonymisiertem Fixture: Dishes zu Rezepten,
     Meals zu Entries inklusive Nährwert-Snapshot, Templates zu Plänen.
   - Legacy-Endpunkte als klar markierte Read-Adapter betreiben. Ihr
     Entfernen wird erst freigegeben, wenn kein Client sie verwendet.

4. **Frontend und Offline-Sync**
   - Eine produktive Mahlzeitenoberfläche bestimmen; die ungenutzten
     Parallelkomponenten (`MealGrid`/`MealCard`) entfernen oder bewusst
     konsolidieren.
   - Konfigurationsseiten für Kategorien, Lebensmittel, Rezepte und Pläne
     bauen; Tagesansicht auf Entries und Status umstellen.
   - Dexie-Schema versionieren, Konto-Scope sicherstellen und Konflikt-UI
     statt stillem Last-write-wins liefern.

5. **Fotoanalyse, Qualität und Entfernung**
   - Foto zuerst einem autorisierten Eintrag zuordnen, Analyse versioniert
     speichern und nur über „Übernehmen“ in einen Eintrag übertragen.
   - Accessibility-, Mobil- und Offline-Tests ergänzen. Backend `pytest -q`
     sowie Frontend-Check, Design-Lint und Build ausführen.
   - Nach einer dokumentierten Kompatibilitätsperiode Legacy-Modelle,
     -Endpunkte und ungenutzte UI entfernen.

   Der Übergang ist nun durch die additive Revision `023` vorbereitet:
   Fotoanalyse ist für neue `meal_entries` ein eigener Vorschlag mit
   `pending|accepted|rejected|failed`. Nur ein expliziter Accept-Command mit
   vom Nutzer gewählten Food-/Recipe-Items darf einen Snapshot verändern.

## Reihenfolge und Gates

WP1 ist ein zwingendes Gate vor jeder neuen Funktion. WP2 und WP3 können
teilweise parallel vorbereitet werden, aber die Datenmigration benötigt das
finale Schema. WP4 beginnt gegen den stabilen Zielvertrag. WP5 entfernt erst
nach produktiver Verifikation alte Pfade. Keine externe Lebensmittelquelle,
Barcode-Funktion oder KI-Automation wird ohne eigene Spezifikation ergänzt.
