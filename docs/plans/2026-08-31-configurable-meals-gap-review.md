# Deep-Gap-Review: konfigurierbare Mahlzeiten

**Status:** superseded (historical) — review input captured before implementation; the active source is [`../specs/configurable-meals.md`](../specs/configurable-meals.md).
**Grundlage:** [`../specs/configurable-meals.md`](../specs/configurable-meals.md)  
**Methode:** unabhängige lesende Reviews von Produkt/UI, Daten/API und Betrieb/Offline

## Ergebnis

Das Zielmodell ist tragfähig, benötigt jedoch folgende Ergänzungen. **P0** ist
eine Release-Voraussetzung für den Mahlzeitenbereich, **P1** muss vor der
Datenmigration geklärt werden, **später** ist bewusst nicht Teil des MVP.

## P0 — Schutz, Datenwahrheit und Kernabläufe

| Bereich | Verbindliche Ergänzung | Nachweis/Gate |
| --- | --- | --- |
| Ressourcenrechte | Jede ID-Abfrage und jede Mutation filtert explizit nach `id` **und** `account_id == current_account`; Referenzobjekte werden einzeln im selben Konto geprüft. Der ORM-Context ist eine zusätzliche, nicht die einzige Barriere. | A kann keine Ressource oder Referenz von B lesen, ändern, löschen, konsumieren, synchronisieren oder mit Foto verknüpfen. Fremde IDs liefern 404 ohne Teilmutation. |
| Schreibvertrag | Keine generischen Browser-Patches für Snapshot, Analyse, Archivierung oder Status. Erlaubte fachliche Commands sind explizit und allow-listed. | Owner-, Analyse-, Snapshot- und interne Link-Felder im Browser-DTO liefern 422. |
| Tageserfassung | Einträge können unabhängig vom Plan als Rezept, Lebensmittel oder manuelle Gesamtsumme angelegt werden; Kategorie und Zeitpunkt sind optional. | Mehrere Einträge pro Kategorie, Einträge ohne Kategorie und rückdatierte Einträge funktionieren. |
| Statusmodell | Zustandsautomat `draft? -> planned -> consumed|skipped` mit Rücknahme, Zeitstempeln und klarer Storno-/Archivregel. | Nur `consumed` beeinflusst Ist-Summen, Wochenwerte und Zielerfüllung. |
| Plan | Genau eine eindeutige, unveränderliche aktive Planversion pro Konto und Datum; Ausnahmen sind explizit. Die Instanziierung ist eine Aktion, kein GET-Nebeneffekt. | Datenbank-Unique auf Konto, Datum, Planversion und Template-Item verhindert Duplikate auch bei parallelen Requests. |
| Historie | Kategorien, Planitems, Rezepte und Food-Werte werden in Einträgen gesnapshottet. Löschen/Deaktivieren ist bei historischer Referenz Archivierung oder eine explizite Migration. | Änderungen an Food/Rezept/Plan lassen alte Einträge und Statistik bytegleich. |
| Nährwerte | Nur ein Nutrition-Service schreibt Items und Entry-Summen atomar. Mengen/Portionen positiv, Werte nicht negativ, Einheiten gültig; unbekannt ist `null`, niemals 0. | Tests decken Decimal, Rundung erst in der Anzeige, Portionen, Unterrezepte, unbekannte Werte und Überläufe ab. |
| Zeitmodell | Konto besitzt IANA-Zeitzone; `consumed_at` ist UTC, `local_date` und verwendete Zeitzone sind historisch gespeichert. | Plan und Tageszuordnung funktionieren bei Mitternacht, DST und nicht-Berliner Konten. |
| Fotoanalyse | Autorisierten Entry prüfen, dann validiert hochladen, Analyse als Vorschlag speichern, erst danach explizit übernehmen. Kein automatisches Konsumieren, Überschreiben oder Rezeptanlegen. | Fehler, Ablehnung, erneute Analyse und Übernahme sind nachvollziehbar; Schätzungen sind sichtbar markiert. |

## P0 — Offline, Datenschutz und Betrieb

| Bereich | Verbindliche Ergänzung | Nachweis/Gate |
| --- | --- | --- |
| Sync v2 | Pro Operation: UUID/Idempotency-Key, erwartete Revision und Ergebnis `applied|duplicate|conflict|validation_error`. Nur erfolgreiche/duplizierte Operationen verlassen die Outbox. | Retry, Timeout, Clock-Skew, Teilfehler und zwei Geräte verlieren oder duplizieren keine Daten. |
| Konflikte | Cursor-basierter Change-Feed statt Zeitstempelvergleich; Tombstones und pro Entität dokumentierte Konfliktstrategie. Keine stille Client-wins-Regel. | UI zeigt Server-/Client-Wert und erlaubt bewusste Entscheidung. |
| Offline-Umfang | MVP erlaubt lokale textuelle Entwürfe; Fotoanalyse/-upload bleibt online. Jede IndexedDB-Tabelle, Blob-Cache und Outbox ist konto-gebunden und wird bei Logout **und** Authverlust gelöscht. | Kein Accountwechsel kann lokale Daten eines anderen Kontos zeigen. |
| Foto-Privatsphäre | MIME per Inhalt prüfen, Größen-/Pixel-Limits, EXIF/GPS entfernen, zufälliger konto-getrennter Object-Key, autorisierter Download statt Dateisystempfad. | Fremde Entry-ID, manipulierte/zu große Datei und Analysefehler sind sicher und verständlich behandelt. |
| Datenrechte | Serverautorisierter Ernährungsexport; bestätigte Löschflüsse für Foto, Analyse, Eintrag und Konto. | Export hat Schema-/Zeitzonen-Manifest; Löschung und Wiederherstellung sind getestet. |
| Betrieb | Korrelation ohne Gesundheitsinhalte, Sync-/Foto-/DB-Metriken, Limits, Pagination, Backup/Restore-Test, Migrations-Backup und Feature-Flag. | Tagesansicht hält Query-Budget; Restore- und Migrations-Rehearsal sind dokumentiert und erfolgreich. |

## P1 — Vor der Migration verbindlich entscheiden

1. **Planregeln:** Mehrere Pläne erlauben, aber genau einen aktiv; Regeln für
   Training/Ruhetag sind später. Planversionen erhalten `effective_from` und
   überlappen nicht.
2. **Portionen und Einheiten:** Speicherung in g, ml und Stück; Haushaltsmaß
   nur mit hinterlegter Umrechnung. Rezeptausbeute ist eindeutig als Portionen,
   Gesamtgewicht oder beides definiert.
3. **Nährwertvollständigkeit:** Bei einem unbekannten Item ist eine Summe als
   unvollständig markiert, nicht scheinbar exakt. Snapshotformat ist für
   spätere Nährstoffe erweiterbar.
4. **Unterrezepte:** Maximaler Verschachtelungsgrad, Zyklusprüfung und
   Verhalten bei parallelen Änderungen werden festgelegt.
5. **Ziele:** Versionierung und Wirksamkeit von Tageszielen; Mindestwert,
   Zielbereich und Obergrenze unterscheiden; Tageshistorie bleibt erklärbar.
6. **Fotoaufbewahrung:** Standardfrist und sofortige Löschung, KI-Anbieter,
   Opt-in, Reanalyse sowie Export mit/ohne Fotos.
7. **Archivierung:** Verhalten für Rezept/Kategorie/Planitem mit historischen
   Referenzen; konsumierte Einträge werden nicht still gelöscht.

## Erforderliche Nutzer- und Fehlerflüsse

- Erstkonfiguration ohne Plan; die Tageserfassung bleibt direkt nutzbar.
- Plan-Eintrag essen, Portion ändern, ersetzen oder überspringen.
- Spontanen Snack und mehrteilige Mahlzeit (z. B. Brot, Belag, Getränk)
  erfassen.
- Rezept entwerfen, Zutaten prüfen, Ausbeute definieren, aktivieren und
  archivieren.
- Foto aufnehmen, Analyse prüfen, manuell korrigieren, übernehmen oder
  verwerfen.
- Offline-Entwurf, Wiederverbindung, Konfliktentscheidung und erneuter Sync.
- Korrektur eines verzehrten Eintrags mit nachvollziehbarer Bilanzänderung.

Alle Mutationen brauchen sichtbare Lade-, Erfolg- und Fehlerzustände. Dialoge
erfüllen Tastatur-, Fokus-, Screenreader-, Kontrast-, 200%-Zoom- und
44x44-Touch-Ziel-Anforderungen. Dezimaltrennzeichen folgen der Locale.

## Bewusst später

Barcode und externe Kataloge, Einkaufsliste, Vorrat/Meal-Prep, Favoriten,
Kopieren/Wiederholung, Import, Mikronährstoffe/Allergene, Trainingsperiodisierung,
Erinnerungen, vollständiger Offline-Fotoupload, Live-Sync, CRDT-Merge und
lokale Verschlüsselung. Jedes Paket braucht eine eigene Spezifikation.

## Zusätzliche Spezifikationen und ADRs

Zusätzlich zum bestehenden Paket werden vorgeschlagen:

- `meals/09-nonfunctional-operations.md` — SLOs, Performance, Limits,
  Backups, Migration, Observability und Incident-Runbook.
- `meals/10-data-rights-retention-and-export.md` — Datenklassen, Export,
  Löschung, Aufbewahrung und Wiederherstellung.
- `meals/11-accessibility-and-responsive-ux.md` — WCAG 2.2 AA, responsive
  Bedienung und Fehlerrückmeldungen.
- ADRs für konto-gebundene Referenzen, Zeitmodell, Nährwertvollständigkeit,
  Sync-Protokoll, Foto-Datenfluss/Retention und operative SLOs.

## Erweiterte Testmatrix

- API: A-gegen-B für Listen, IDs, Referenzen, Statusänderungen, Fotos und Sync.
- Datenmodell: Constraints, atomare Summen, unbekannte Werte, Unterrezept-Zyklus,
  parallele Instanziierung und DST.
- Offline: doppelte Operation, Teilbatch, Tombstone, Konflikt, Authverlust und
  Cache-Löschung.
- Foto: fremde ID, Typ/Größe/EXIF, Abbruch, Fehler, Ablehnung, Übernahme und
  vollständige Löschung.
- Migration: anonymisiertes produktionsnahes Fixture samt unzuordenbaren und
  beschädigten Legacy-Daten; Zählwerte vor/nach und kein Wertverlust.
- E2E: Konfiguration → Planung → Verzehr → Offline → Konflikt → Wochenbilanz.
