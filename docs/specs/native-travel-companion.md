# Native App und private Anreisebegleitung

Status: approved for implementation by user instruction 2026-09-08. Owner: Cronicl household.

## Entscheidung und Revisionsumfang

iPhone und Android erhalten eine Capacitor-App mit gebündelter vorhandener Svelte-Oberfläche. Die Begleitung verwendet die bestehende To-do-Highlight-Fläche. Dieser eigenständige Revisionsschritt erweitert `todo-places-and-travel.md` um native, ausdrücklich aktivierte Hintergrundbegleitung und `multi-account-scale-and-body-composition.md` um widerrufbare native Kontositzungen. Browser-Einzelabfragen speichern weiterhin keinen Ursprung. Space-Berechtigungen bleiben unverändert: Anreisen sind privat.

## Verbindliches Verhalten

1. Eine Überwachung gehört genau einem offenen privaten To-do mit Datum, Startzeit, bestätigtem Ziel und Verkehrsmittel. Sie wird ausdrücklich im Anreisedetail aktiviert; vorhandene Vordergrund-Checkboxen erzeugen keine stille native Freigabe.
2. Standardvorlauf ist 60 Minuten vor der geschätzten Abfahrt, einstellbar von 15 bis 180 Minuten. Der Server prüft den bestätigten Startort selbständig und passt die Prüfung an die Abfahrt an. Der initiale Startort ist eine bewusst bestätigte Einzelposition, alternativ eine bestätigte Place-ID. Als fester Startort darf er bis zum Ende der Überwachung gespeichert werden; dies ist keine Live-Position.
3. Native Live-Begleitung wird sichtbar aus der App gestartet. Das Betriebssystem darf einen automatischen Start verhindern: eine Erinnerung im Vorlauf öffnet das To-do zum Starten. Der Server läuft davon unabhängig. Keine Garantie für Force-stop, fehlende Rechte, Offlinezustand oder sekundengenaue Zustellung.
4. Pro Überwachung genau ein ausgewähltes natives Gerät. Native Fixes benötigen Messzeit und Genauigkeit; Zukunftszeiten, unbrauchbare Genauigkeit, alte oder falsch geordnete Fixes werden abgelehnt. Letzter Fix maximal 15 Minuten verwendbar, nach Ablauf löschen. Kein Verlauf und keine sensiblen Payloads in Logs/Push/KI/Space-Daten.
5. Begleitung endet beim ausdrücklichen Beenden, Erledigen/Löschen, Deaktivieren, Änderung von Ziel/Termin/Modus, Sitzungswiderruf oder spätestens 30 Minuten nach Terminbeginn. Native Dienste besitzen zusätzlich eine lokale Ablaufzeit. Ankunft kann vom Nutzer bestätigt werden; Navigation-Öffnen bedeutet nicht automatisch Ankunft/Erledigung.
6. Zukünftige Autofahrten werden mit künftiger Abfahrt geschätzt, höchstens zwei Anbieteraufrufe je Prüfung. Für Transit gewünschte Ankunft und Verbindungszeiten beachten. Zeitbasis ist die gespeicherte IANA-Zeitzone (Standard Europe/Berlin); ungültige/nicht existente lokale Zeiten zurückweisen, mehrdeutige Zeiten deterministisch dokumentieren.
7. Persistente Jobs und Outbox mit Sperren, Ablauf, begrenzten Retries und semantischer Deduplizierung. Vor Berechnung und Versand Besitz, Sitzungsstatus und Planversion erneut prüfen. Verkehrsänderung ab fünf Minuten, Übergang „jetzt los“ und Vorlaufbeginn können benachrichtigen; keine Nachricht für jede Abfrage. Pushs enthalten nur generische Handlungsinformation und interne Ressourcenreferenzen; beim Öffnen neu autorisieren und laden.
8. Status zeigt getrennt: aktive/pausierte Begleitung, fester versus aktueller/alter Startort, Verkehrs-Prüfzeit, Providerfehler und Push-Verfügbarkeit. Keine Live-Kennzeichnung ohne frische native Position. Maximal ein bestehendes Highlight; keine zusätzliche Highlight-Fläche oder Kartenstartseite.

## Native Sitzung

Login erfolgt über Systembrowser und vorhandenen serverseitigen Google-OAuth-Broker. Kurzlebiger Login-Auftrag ist an einen kryptografischen Challenge/Verifier gebunden; einmalige Einlösung nach verifiziertem Google-Login. Keine Google-Tokens oder Kontowahl aus dem Client. Native opaque Sitzung nur im OS-geschützten Speicher; Server speichert ausschließlich Hash und Ablauf (30 Tage), prüft Widerruf und Account bei jedem Request. Der native Transport injiziert das Credential nur an den fest konfigurierten HTTPS-API-Origin. Browser-Cookies bleiben unabhängig. Logout widerruft die native Sitzung und beendet ihre Überwachungen, auch wenn die UI keine weiteren Requests sendet. Offline-Logout entfernt lokal Credential/Dienste; bis zum serverseitigen Widerruf spätestens Sitzungs-/Überwachungsablauf.

## Verifikation und Touchpoints

| Verpflichtung | Prüfung |
| --- | --- |
| Native Login-Proof, Replay, Ablauf, Kontotrennung und Widerruf | `backend/tests/test_native_travel.py`, isolierte DB-Tests |
| Ein Kopf, Upgrade bestehender und leerer DB | `backend/scripts/verify_migrations.py`, Alembic heads |
| Planung, Freshness, Job-/Outbox-Deduplizierung | `backend/tests/test_native_travel.py` |
| API-Identität nicht clientgesteuert | OpenAPI-Snapshot, A/B-Isolation |
| Highlight, Dialog, Native-Fallbacks | Frontend check/design/build und Browserabnahme |
| Tatsächlicher Hintergrundbetrieb | Geräteprotokoll iOS/Android: Sperre, Suspend, Force-stop, Rechteentzug, Offline, Ablauf, Akku |

Revalidieren bei Auth-, Schema-, Provider-, Speicher-/Lösch-, Worker-, nativen Lebenszyklus- oder UI-Zustandsänderungen. Bestehende `/estimate`-Route bleibt als bewusster Web-Einzelabfragemodus unterstützt, nicht als temporärer Legacy-Endpunkt. Verteilung, Signierung, Push-Credentials und Geräteabnahme sind externe Releasevoraussetzungen, keine durch Quellcode allein erfüllbaren Checks.
