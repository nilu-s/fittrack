# Cronicl: Kontakte

**Status:** approved  
**Owner:** Cronicl household  
**Last updated:** 2026-09-03

## Ziel

Kontakte sind ein separater, privater Adressbereich für bereits zugelassene
Konten. Sie sind weder Workspace-Mitglieder noch eine Berechtigung. Die
Kontaktaufnahme funktioniert über einen öffentlichen Alias statt über eine
E-Mail-Adresse.

## Regeln

1. Nach dem ersten erfolgreichen Google-Login muss jedes Konto einen
   eindeutigen, unveränderlichen Alias wählen: 3–32 Kleinbuchstaben, Ziffern,
   Punkte, Unterstriche oder Bindestriche, beginnend mit einem Buchstaben oder
   einer Ziffer. Bestehende Konten schließen diesen Onboarding-Schritt beim
   nächsten authentifizierten Aufruf ab.
2. Aliase sind für andere angemeldete, zugelassene Konten per Präfixsuche ab
   zwei Zeichen auffindbar. Ein Suchtreffer enthält nur Alias und Anzeigenamen,
   nie E-Mail-Adresse oder interne Kontokennung.
3. Eine Kontaktanfrage wird an einen Alias adressiert und erst nach Annahme
   beidseitig als Kontakt gespeichert. Nicht vorhandene Aliase werden nicht als
   Konto oder E-Mail offengelegt.
4. Ein Kontakt sieht ausschließlich Alias und Anzeigenamen der anderen Person. Er
   verleiht keinen Zugriff auf private Daten, Workspaces, To-dos oder Listen.
5. Entfernen beendet die Verbindung für beide Konten. Anfragen sind nur für
   die Empfängerin bzw. den Empfänger sichtbar und annehmbar oder ablehnbar.

## Verifikation

`backend/tests/test_contacts_contract.py`, die Alias- und Kontakt-
Account-Isolation-Integrationstests sowie `npm run check`, `npm run
lint:design` und `npm run build`.
