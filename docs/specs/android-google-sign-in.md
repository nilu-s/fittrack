# Android Google-Anmeldung

Status: approved by user instruction 2026-09-08. Owner: Cronicl household.

## Eigenständige Revision

Diese Entscheidung ersetzt ausschließlich den Android-Login-Abschnitt von
`native-travel-companion.md`. Die Kontogrenzen von
`multi-account-scale-and-body-composition.md` bleiben verbindlich. Android verwendet
Google Credential Manager über das eigene Capacitor-Modul; iOS-Login-v1 bleibt
gesperrt und benötigt eine eigene Implementierung. Website-Login bleibt bestehen.

## Vertrag

1. Ein bewusster Klick auf „Mit Google anmelden“ öffnet die Google-Kontoauswahl.
   Die App nutzt den Button-Flow `GetSignInWithGoogleOption`, ohne stille Kontowahl.
2. Das native Modul erzeugt einen geheimen zufälligen Verifier. `/api/native/google/start`
   speichert dessen SHA-256-Challenge, einen Hash einer zufälligen Nonce, Android als
   Plattform, Protokollversion 2 und fünf Minuten Ablauf. Antwort: Auftrags-ID, Nonce,
   konfigurierte Google-Web-Client-ID. Keine Client-Auswahl eines Kontos.
3. Credential Manager erhält Client-ID und Nonce. Das Modul übergibt ID-Token,
   Auftrags-ID und Verifier ausschließlich per HTTPS an `/api/native/google/exchange`.
   Der Server prüft Google-Signatur, issuer, audience, Ablauf, verifizierte E-Mail,
   serverseitige Freigabeliste, Nonce und Verifier. Fehler erzeugen keine Sitzung.
   Einlösung ist transaktional, einmalig und unter parallelen Requests replayfest.
4. Kontoauflösung ausschließlich über den verifizierten Google-`sub`; keine Kontowahl
   aus dem Request. Neue Konten erhalten nur eigene Defaults; ein neuer
   Gewichtszuteilungsbereich bleibt bis zur bewussten Konfiguration inaktiv,
   damit die Anmeldung keine überlappenden aktiven Bereiche erzeugt. Native Anmeldung
   speichert keine Google-Zugriffstokens und erteilt keine Kalenderberechtigung.
   Bestehende Google-Integrationen bleiben dem jeweiligen Konto zugeordnet.
5. Neue opaque Sitzungen sind Version 2, 30 Tage gültig und serverseitig widerrufbar.
   Ein neuer Credential-Präfix und eine persistente Versionsprüfung schließen v1 aus.
   Migration widerruft alte native Sitzungen, entfernt ihre Push-Zuordnung, beendet
   zugehörige Überwachungen und entwertet alte Login-Aufträge. Browserdaten bleiben.
6. Verifier, Google-ID-Token und Sitzung verbleiben im nativen Modul; Sitzung wird
   mit Android Keystore verschlüsselt. Kein Credential in Web Storage, URLs, Logs
   oder generischen Bridge-Antworten. Generischer Bridge-Transport sperrt Login-Routen.
7. Logout widerruft online die Sitzung, stoppt Standortdienste, löscht lokalen
   Sitzungszustand und ruft `clearCredentialState` auf. Offline gilt die bestehende
   dokumentierte Widerrufsgrenze. Ein Kontowechsel erfolgt über Logout und neue
   Anmeldung; private lokale Webdaten werden vor Nutzung des neuen Kontos gelöscht.
8. Fehlende native Google-Client-ID ergibt `503`, keine stillschweigende Aktivierung.
   Alte `/native/login`, `/native/exchange` und native Browser-Callbacks bleiben
   gesperrt, solange ausgelieferte v1-Clients diese noch aufrufen können. Nach deren
   Ablösung dürfen diese Ablehnungsrouten entfernt werden; v1 wird nie reaktiviert.

## Interaktion

Vorhandene Anmeldeseite und Google-Schaltfläche bleiben. Während der Anmeldung ist
der Button gegen Doppelklick gesperrt, mit verständlichem Wartezustand. Abbruch
kehrt ohne Fehlermeldung zum Button zurück; Netzwerk-, Freigabe- und
Konfigurationsfehler erlauben einen erneuten Versuch und werden zugänglich angezeigt.
Erfolg prüft `/auth/me`, löscht gegebenenfalls fremden Cache und öffnet Alias-Onboarding
oder Tagesansicht. Keine Navigation allein aufgrund eines lokalen Erfolgsflags.
Tastatur und Touch nutzen denselben nativen Button; Fokus bleibt nach Abbruch dort.

## Abnahme und Touchpoints

- Backend: `backend/tests/test_google_native_auth.py`: Signatur/aud/iss/exp,
  Nonce/Verifier, Ablauf/Replay/Parallelität, Freigabe, bestehendes/neues Konto,
  A/B-Isolation, Widerruf und v1-Abweisung. Providerantworten synthetisch.
- Migration: leere DB sowie v1-Datensätze vor Upgrade; ein Kopf, alte Sitzungen
  bleiben auch nach einem Downgrade widerrufen.
- Frontend: check/design/build/mobile build; `frontend/scripts/test-native-login-ui.mjs`
  für Erfolg, Abbruch, Fehler, Doppelklick und iOS-Sperre mit synthetischer Bridge.
- Android: Gradle-Kompilierung; Geräteabnahme für echte Google-Auswahl, Neustart,
  Kontowechsel, Offline und Logout. Google-Clientregistrierung muss zu Paketname und
  Signaturzertifikat passen. Kein Geräteerfolg ohne tatsächliche Durchführung.

Revalidieren bei Auth-/Bridge-/Kontogrenzen, Protokoll, Migration, Google-Konfiguration,
Login-UI und nativem Lebenszyklus. Kalenderberechtigung, iOS-Ersatzlogin, Deployment
und Store-Verteilung sind außerhalb dieses Android-Arbeitspakets.
Die Integrationsanzeige muss dennoch den echten Google-Datenzugriff getrennt vom
Cronicl-Anmeldestatus anzeigen; sie verwendet hierfür die bestehende Status-API.

Quellen: [Credential Manager](https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation),
[Google-Tokenprüfung](https://developers.google.com/identity/sign-in/android/backend-auth).
