# 0003: Chronickel startet mit einer sauberen Baseline

## Entscheidung

Chronickel übernimmt weder Daten noch Migrationsgeschichte des Vorgängers.
Die Datenbank beginnt bei Revision `7095ad546555` und wird ausschließlich
gegen eine leere Datenbank migriert.

## Begründung

Das Produkt ist umbenannt und sein Datenmodell wurde grundlegend auf
konto-private Daten und Reiseplanung ausgerichtet. Historische Übergangslogik
wäre nicht ausführbar, nicht testbar und würde veraltete Begriffe im aktiven
Code halten.

## Folgen und Entfernungskriterium

Die alte Datenbank wird nicht von Chronickel gelesen. Die nachfolgende
Migrationskette bleibt genau eine Baseline plus künftige, fachlich begründete
Revisionen. Der separat erhaltene Vorgänger-Docker-Volume darf erst gelöscht
werden, wenn der Produktverantwortliche dessen Entfernung ausdrücklich
bestätigt.
