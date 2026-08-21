# FitTrack Main-led Design System – Implementierungsplan

> **Für Hermes:** Diesen Plan mit `subagent-driven-development` taskweise und mit unabhängigem Review umsetzen.

**Ziel:** Die bestehende Tagesansicht (`/`) wird die verbindliche visuelle Referenz; alle FitTrack-Flächen verwenden danach dieselben Tokens, Komponenten-Primitives und Zustände, ohne die Tagesansicht neu zu erfinden oder Produktlogik zu ändern.

**Architektur:** Das Design-System bleibt CSS-/Svelte-nativ: semantische CSS-Custom-Properties und globale Primitives werden in `src/lib/styles/` zentral gepflegt. Svelte-Komponenten kapseln wiederkehrende interaktive Muster. Seiten und fachliche Komponenten dürfen nur noch Layout-Komposition und ausschließlich lokale, fachlich bedingte Darstellung enthalten. `/` ist der visuelle Vertrag; Settings, Woche, Login und Overlays werden an ihn angeglichen.

**Tech Stack:** Svelte 5, SvelteKit 2, TypeScript, CSS Custom Properties; bestehendes Playwright-Paket wird für Screenshot-/Interaktions-Regressionen aktiviert.

---

## Aktueller, geprüfter Kontext

- `frontend/src/app.css` enthält bereits Basisfarben, Abstände, Radien und globale Card/Button/Modal-Regeln.
- Die Referenzseite ist `/`: `src/routes/+page.svelte` komponiert `UnifiedDay`, `DateNav` und die Sync-Anzeige; das globale Shell-Muster lebt in `src/routes/+layout.svelte`.
- `UnifiedDay.svelte` bildet das gewünschte Verhalten ab: dichte Tages-Informationshierarchie, klare Statusfarben, Progress-Bars, Check-Interaktionen, kleine Datendiagramme und expandierbare Details.
- 25 von 26 Svelte-Dateien besitzen eigene `<style>`-Blöcke; `UnifiedDay.svelte` allein referenziert 169 CSS-Variablen. Das verhindert derzeit konsistente Änderungen an einem Ort.
- Es gibt aktuell weder Testdateien noch einen Test-Script-Eintrag in `frontend/package.json`; `playwright` ist jedoch bereits als Dependency vorhanden.
- Der aktuelle Style-Kommentar verbietet Gradients, Glows und Glassmorphism (`app.css:1–5`), während `routes/settings/+page.svelte:27` dennoch einen Gradient verwendet. Diese Abweichung wird entfernt, nicht weitergetragen.

## Look-&-Feel-Design-Spec (SOT)

| Aspekt | Verbindliche Entscheidung aus der Main-Seite |
|---|---|
| Visuelle Quelle | `/` / Tagesansicht. Neue Screens werden daran angeglichen; die Main-Seite wird nicht für Sekundärseiten verbogen. |
| Farbwelt | Dark-only: sehr dunkler Hintergrund, solide abgestufte Flächen, dezente Borders. Kein Gradient, Glow, Glassmorphism oder dekorative Schatten außerhalb des Modals. |
| Informationshierarchie | Aktion und aktueller Wert zuerst; Kontext/Einheit sekundär; optionale Detaildaten über explizite Expansion. |
| Statusfarbe | Farbe ist semantisch und nie alleiniger Träger: `success/done` grün, `info/measurement` blau, `warning/target` amber, `danger/error` rot; Text/Icon/ARIA ergänzt Farbe. |
| Datenfarben | Makros bleiben konsistent: kcal amber, Protein blau, KH lila, Fett pink, Ballaststoffe grün. Schlafphasen erhalten zentral definierte Datenfarben. |
| Flächen | Standardisierte Card/Section-Card mit 10px Radius, subtiler Border, 10–16px Rhythmus. Nicht jede Komponente definiert eigene Card-Geometrie. |
| Typografie | Systemschrift, tabellarische Ziffern, kompakte 11/13/15/17/18px Skala; Zahlenwerte klarer und stärker als Labels. |
| Interaktion | Mobile-first, sichtbare 38–44px Tap-Ziele, Press-State statt Hover-Abhängigkeit, kein versteckter kritischer Long-Press. |
| Bewegung | Kurz und funktional: 150–200ms für Fade/Expand, `prefers-reduced-motion` deaktiviert nicht essentielle Bewegung. |
| Responsive Shell | 480px mobile App-Shell bleibt Referenz; breitere Ansichten behalten Rahmen und konsistente Innenabstände. |

## Produktvertrag

### In Scope

1. Tokens, Typografie, Abstände, Radien, Borders, Layer und Status-/Datenfarben zentralisieren.
2. Wiederkehrende UI-Muster als konsistente Primitives bereitstellen: Shell/Header, Surface/Section, Button/IconButton, Input/Select, Badge, Progress, Modal, Empty/Loading/Error.
3. Alle produktiven Routen (`/`, `/week`, `/settings`, `/settings/*`, `/login`) auf diese Primitives und das Referenzmuster migrieren.
4. Visuelle und funktionale Regressionen auf Mobile-Viewport automatisiert prüfen.
5. Accessibility-Basis festschreiben: Fokus, Kontrast, sichtbare Labels und reduzierte Bewegung.

### Nicht im Scope

- Neue Produktfeatures, neue Backend-Endpunkte, Änderungen an Mahlzeiten-/Trainings-/Sync-Logik.
- Light Mode, externe Component-Library oder ein zweites Theme.
- Vollständige visuelle Neugestaltung der Main-Seite.

### Pre-Conditions

- Arbeitsbaum ist vor Start geprüft und fremde Änderungen werden nicht überschrieben.
- `frontend/node_modules` ist installiert; die vorhandenen Check-/Build-Kommandos laufen lokal.
- Für Screenshot-Tests steht ein lokaler, authentifizierbarer Fixture-/Mock-Weg bereit. Falls nicht, wird dieser ausschließlich testseitig und ohne Produktionsdaten ergänzt.

### Post-Conditions

- Jede produktive Route rendert innerhalb derselben Design-Tokens und Primitives.
- Es gibt eine dokumentierte, maschinengeprüfte Referenz für `/`, `/week`, `/settings` und mindestens einen Settings-Detail-Screen auf 375px und 480px Breite.
- Kein produktiver Source-Code referenziert entfernte Legacy-Token oder verbotene visuelle Ausnahmen.
- `npm run check`, `npm run build` und die UI-Regressionen sind grün.

### Unbestimmtes Verhalten

- Systemweite High-Contrast- und Light-Mode-Themes werden bewusst nicht spezifiziert.
- Die fachliche Entscheidung, welche Tagesdaten sichtbar sind, bleibt außerhalb des Design-Systems; es standardisiert nur deren Darstellung und Interaktion.

## Canonical Ownership

| Artefakt | Verantwortlichkeit |
|---|---|
| `src/lib/styles/tokens.css` | Einzige Quelle für Farb-, Typografie-, Spacing-, Radius-, Layer- und Motion-Tokens. |
| `src/lib/styles/primitives.css` | Einzige globale Umsetzung der neutralen UI-Primitives. |
| `src/lib/components/ui/*.svelte` | Wiederverwendbare interaktive UI-Bausteine mit Accessibility-Vertrag. |
| Seiten/fachliche Komponenten | Datenbindung, Layout-Komposition und fachlich notwendige Varianten; keine ad-hoc Designwerte. |
| `tests/ui/*.spec.ts` | Sichtbarer, automatisierter Designvertrag der Referenzrouten. |

## Work Packages

### WP 0 – Referenzinventar und Akzeptanzmatrix

**Objective:** Den beobachteten Home-Look als überprüfbaren Vertrag vor jeder Änderung festschreiben.

**Files:**
- Create: `frontend/docs/design-system.md`
- Create: `frontend/tests/ui/design-contract.spec.ts`
- Modify: `frontend/package.json`

**Steps:**
1. In `design-system.md` die oben stehende Spec als produktnahe Regeln übernehmen; zusätzlich je Primitive erlaubte Varianten, Mindesttapziel, Statussemantik und verbotene Effekte nennen.
2. Ein `test:e2e`-Script und eine minimale `playwright.config.ts` ergänzen. Der Web-Server startet im Testmodus; Testdaten/Auth werden über den vorhandenen, isolierten Testweg bereitgestellt, nicht über reale Nutzerdaten.
3. Einen zunächst roten Contract-Test schreiben: `/`, `/week`, `/settings` und `/settings/goals` müssen je Shell, Header, Surface, sichtbaren Fokus und mindestens eine semantische Statusdarstellung besitzen.
4. Screenshots bei `375×812` und `480×900` aufnehmen; Baselines unter `tests/ui/__screenshots__/` versionieren.

**Verification:**
```bash
cd frontend
npm run test:e2e -- --update-snapshots
npm run test:e2e
```
Erwartet: Test läuft reproduzierbar; vor der folgenden Migration darf der Strukturtest gezielt rot sein.

### WP 1 – Tokens als einzige Design-Wahrheit

**Objective:** Die Werte der Main-Seite in semantische Tokens überführen und Legacy-Aliasse entfernen.

**Files:**
- Create: `frontend/src/lib/styles/tokens.css`
- Modify: `frontend/src/app.css`
- Modify: alle Dateien unter `frontend/src/**/*.svelte`, die entfernte Token-Namen verwenden
- Test: `frontend/tests/ui/design-contract.spec.ts`

**Steps:**
1. Den roten Test um Assertions ergänzen, dass Root die Token-Gruppen `--color-*`, `--surface-*`, `--text-*`, `--space-*`, `--radius-*`, `--motion-*` und `--z-*` definiert.
2. `tokens.css` anlegen. Die bisherigen konkreten Werte werden einmalig semantisch abgebildet, z. B.:
```css
:root {
  --color-bg: #0b0c0e;
  --surface-default: #141518;
  --surface-raised: #1b1c20;
  --text-primary: #f0f0f2;
  --text-secondary: #85888f;
  --status-success: #34c759;
  --data-kcal: #ff9f0a;
  --space-1: 6px; --space-2: 10px; --space-3: 12px; --space-4: 16px;
  --radius-control: 8px; --radius-surface: 10px; --radius-modal: 12px;
  --motion-fast: 150ms; --motion-standard: 200ms;
}
```
3. `app.css` auf Reset, globale Accessibility-Regeln und Imports reduzieren. Alle bisherigen Aliasnamen (`--green`, `--card`, `--gap-*`, etc.) in produktivem Code atomar auf die neuen Namen migrieren und danach entfernen; keine zweite Alias-Schicht behalten.
4. Schlafphasen und Diagrammfarben ebenfalls nach `--data-sleep-*` verlagern; keine Hexwerte mehr in Svelte-Markup.
5. Kontrast für Text auf `--color-bg`, `--surface-default` und `--surface-raised` messen und im Doc protokollieren; unzureichende Kombinationen korrigieren.

**Verification:**
```bash
cd frontend
npm run check
npm run build
rg --glob '*.svelte' --glob '*.css' -- '--(green|blue|amber|purple|pink|red|card|gap-sm|gap-md|gap-lg)' src && exit 1 || true
npm run test:e2e
```
Erwartet: Check/Build/E2E grün; die Legacy-Suche liefert keine produktiven Treffer.

### WP 2 – Globale Primitives und Accessibility-Basis

**Objective:** Wiederholte Home-Muster als global verwendbare Primitives etablieren, ohne einen zweiten Stylingpfad einzuführen.

**Files:**
- Create: `frontend/src/lib/styles/primitives.css`
- Modify: `frontend/src/app.css`
- Create: `frontend/src/lib/components/ui/UiButton.svelte`
- Create: `frontend/src/lib/components/ui/UiIconButton.svelte`
- Create: `frontend/src/lib/components/ui/UiSurface.svelte`
- Create: `frontend/src/lib/components/ui/UiModal.svelte`
- Test: `frontend/tests/ui/design-contract.spec.ts`

**Steps:**
1. Tests für `:focus-visible`, `:disabled`, `aria-busy`, den 38px-Control-Mindestwert sowie `prefers-reduced-motion` schreiben.
2. `primitives.css` mit globalen Klassen für `ui-surface`, `ui-section-header`, `ui-field`, `ui-empty`, `ui-loading` und Statusdaten anlegen. Es enthält keine fachlichen Komponentenklassen.
3. Die vier Svelte-Primitives erstellen. Varianten sind begrenzt und typisiert: `UiButton` (`primary|secondary|danger`), `UiIconButton` und `UiSurface` (`default|raised`); alle leiten native Attribute/ARIA weiter und verwenden ausschließlich Tokens.
4. `app.css` importiert `tokens.css` und `primitives.css`; alte global definierte `.card`, `.btn`, `.modal-*`-Implementierungen werden im selben Change entfernt oder durch die kanonischen Primitives ersetzt.
5. Fokus- und Reduced-Motion-Verhalten als globale Regeln hinzufügen:
```css
:focus-visible { outline: 2px solid var(--status-info); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 1ms !important; transition-duration: 1ms !important; } }
```

**Verification:**
```bash
cd frontend
npm run check && npm run build && npm run test:e2e
```
Erwartet: alle drei Gates grün; Control- und Focus-Tests grün.

### WP 3 – Referenzroute stabilisieren, nicht neu gestalten

**Objective:** Die Main-Seite vollständig auf kanonische Tokens/Primitives umstellen und ihre heutige Hierarchie als Screenshot-Baseline sichern.

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`
- Modify: `frontend/src/routes/+page.svelte`
- Modify: `frontend/src/lib/components/UnifiedDay.svelte`
- Modify: `frontend/src/lib/components/DateNav.svelte`
- Modify: `frontend/src/lib/components/PillBadge.svelte`
- Modify: `frontend/src/lib/components/ProgressBar.svelte`
- Modify: `frontend/src/lib/components/MetricRow.svelte`
- Test: `frontend/tests/ui/home.spec.ts`

**Steps:**
1. Vor der Refactor die akzeptierten `/`-Screenshots erfassen und einen Test für Header, Tages-Surfaces, Makrofarben, Check-Control und expandierbare Nährwertdetails schreiben.
2. Lokale Hardcodes/duplizierte Button-, Surface-, Progress- und Statusregeln durch Tokens/Primitives ersetzen.
3. Inline-Farben der Tagesansicht ausschließlich über `--data-*` oder `--status-*` ersetzen.
4. Keine Datenselektoren, Events, Stores oder API-Aufrufe verändern; Diff-Review explizit auf fachliche Gleichheit prüfen.
5. Screenshots nur aktualisieren, wenn die Änderung dem SOT entspricht; bei Layoutdrift Ursache beheben statt Baseline blind zu ersetzen.

**Verification:**
```bash
cd frontend
npm run check && npm run build && npm run test:e2e -- home.spec.ts
```
Erwartet: Struktur, Interaktion und Screenshots der Main-Seite sind grün.

### WP 4 – Sekundärseiten an die Main-Sprache angleichen

**Objective:** Woche, Login und Settings verwenden dieselbe Shell, Flächen, Controls und Datenhierarchie wie `/`.

**Files:**
- Modify: `frontend/src/routes/week/+page.svelte`
- Modify: `frontend/src/routes/login/+page.svelte`
- Modify: `frontend/src/routes/settings/+page.svelte`
- Modify: `frontend/src/routes/settings/sport/+page.svelte`
- Modify: `frontend/src/routes/settings/goals/+page.svelte`
- Modify: `frontend/src/routes/settings/meals/+page.svelte`
- Modify: `frontend/src/routes/settings/integrations/+page.svelte`
- Modify: `frontend/src/routes/settings/data/+page.svelte`
- Modify: `frontend/src/lib/components/SettingsHeader.svelte`
- Modify: `frontend/src/lib/components/SettingsTile.svelte`
- Test: `frontend/tests/ui/secondary-routes.spec.ts`

**Steps:**
1. Für jede Route einen roten Screenshot- und Strukturtest auf Mobile-Viewport schreiben.
2. Settings-Gradient entfernen und die Intro-/Tile-Flächen auf die Surface-Regeln umstellen.
3. Seiten-Header auf das Main-Header-Muster bringen: identischer Seiteneinzug, Icon-Control, Titelhierarchie und Fokusverhalten.
4. Formulare, Tabs, Back-Controls, Tiles, Charts und Empty/Loading-Zustände auf die Primitives migrieren; keine neuen seitenlokalen Farb-, Radius-, Shadow- oder Spacing-Werte einführen.
5. Fachspezifische Dichte erhalten: Wochencharts bleiben Charts, Settings bleiben konfigurierend; nur die visuelle Sprache wird vereinheitlicht.

**Verification:**
```bash
cd frontend
npm run check && npm run build && npm run test:e2e -- secondary-routes.spec.ts
```
Erwartet: alle sekundären Routen bestehen die 375px-/480px-Screenshot- und Strukturtests.

### WP 5 – Komplexe Fachkomponenten und Overlays konsolidieren

**Objective:** Mahlzeiten, To-dos, Trainingsdetail und alle Dialoge bekommen dieselbe Interaktions- und Statussprache.

**Files:**
- Modify: `frontend/src/lib/components/MealCard.svelte`
- Modify: `frontend/src/lib/components/MealGrid.svelte`
- Modify: `frontend/src/lib/components/TodoItem.svelte`
- Modify: `frontend/src/lib/components/TodoSection.svelte`
- Modify: `frontend/src/lib/components/TrainingDetail.svelte`
- Modify: `frontend/src/lib/components/ProgressionHelp.svelte`
- Modify: `frontend/src/lib/components/DayTracker.svelte`
- Test: `frontend/tests/ui/overlays-and-controls.spec.ts`

**Steps:**
1. Testfälle für Modal-Fokus, Escape/Backdrop-Verhalten (wo heute vorgesehen), Buttons, Filter-Pills, Selects und Training-Completion schreiben.
2. Alle Modal-Markups auf `UiModal` migrieren; die Datenaktion bleibt dabei unverändert.
3. Pills, Progress, Loading und Empty/Error vollständig auf die zentralen Primitives/Tokens überführen.
4. Jeder Statuszustand enthält sichtbar erklärenden Text/Icon und nicht nur eine Farbe.
5. Überprüfen, dass Tap-Targets für Kamera, Filter, Satzsteuerung, Navigation und Abschlussaktionen mindestens 38px hoch/breit sind.

**Verification:**
```bash
cd frontend
npm run check && npm run build && npm run test:e2e -- overlays-and-controls.spec.ts
```
Erwartet: grüne Interaktions- und Accessibility-Checks ohne Logikregression.

### WP 6 – One-solution-only Gate, Dokumentation und Abschluss

**Objective:** Design-Konsistenz bleibt nach der Migration technisch durchsetzbar.

**Files:**
- Modify: `frontend/tests/ui/design-contract.spec.ts`
- Modify: `frontend/docs/design-system.md`
- Modify: `frontend/package.json`
- Modify: `frontend/README.md` (falls vorhanden; sonst `frontend/docs/design-system.md` als Einstieg verlinken)

**Steps:**
1. Einen Guardrail-Test bzw. CI-Script `lint:design` ergänzen, der produktive Hardcodes bei Farben, Radien, Shadows und Gradients meldet; dokumentierte Ausnahmen sind auf Daten-SVGs beschränkt und müssen Token referenzieren.
2. Sicherstellen, dass keine alte globale Component-CSS-Schicht parallel zu `primitives.css` aktiv bleibt; alte Pfade im gleichen Change entfernen.
3. Die Dokumentation um Nutzung, Varianten, Do/Don't, Mobile-Screenshot-Update-Prozess und Accessibility-Checkliste ergänzen.
4. Vollständige Regression und einen frischen visuellen Review auf den zwei Standard-Viewports durchführen.

**Verification:**
```bash
cd frontend
npm run lint:design
npm run check
npm run build
npm run test:e2e
```
Erwartet: alle Gates grün, Guardrail findet weder Gradient noch lokale Design-Hardcodes in produktivem UI-Code.

## Abnahme-Matrix

| Akzeptanzkriterium | Nachweis |
|---|---|
| `/` bleibt visuelle Referenz | Home-Screenshot-Tests auf 375px und 480px, manuelle Differenzprüfung. |
| Einheitliche Designwerte | `lint:design` + keine Legacy-Token/Hex-/Gradient-Hardcodes außerhalb erlaubter Token-Datei. |
| Einheitliche Interaktion | E2E für Buttons, Modals, Navigation, Expansion und Completion. |
| Accessibility-Basis | Sichtbarer Fokus, reduzierte Bewegung, Text/Icon zu Statusfarben, Mindesttapziel. |
| Keine Fachlogikregression | Bestehende Daten- und Eventpfade unverändert; E2E-Interaktion gegen Fixture-API. |
| Produktiver Build | `npm run check` und `npm run build` erfolgreich. |

## Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| Ein CSS-Refactor verändert Fachlogik versehentlich | Main-Route zuerst, event-/store-fokussierter Diff-Review und E2E vor Screenshot-Update. |
| Screenshot-Tests sind durch Live-Daten instabil | Deterministische Fixture-/Mock-Daten, feste Zeitzone und feste Viewports. |
| Lokale Styles schleichen wieder ein | `lint:design` als Gate plus klare Owner-Tabelle. |
| Token-Umbenennung erzeugt unbeobachtete Stilbrüche | Legacy-Suche, `npm run check`, routeweise Screenshots, keine Alias-Kompatibilität. |
| Zu starke Abstraktion macht Svelte-Komponenten unlesbar | Primitives nur für echte Wiederholung; fachliche Layout-Komposition bleibt lokal. |

## End-State-Review-Gate

- [x] Finaler Zielzustand: eine produktweit konsistente, Main-led UI-Sprache mit einer zentralen Implementierung.
- [x] Kein Schritt akzeptiert einen degradierten Zwischenzustand als Abschluss.
- [x] Jede Aufgabe liefert einen überprüfbaren Inkrement-Schritt zum Endzustand.
- [x] Kein Dual Path: Legacy-Aliasse und alte globale Primitive werden zusammen mit der jeweiligen Migration entfernt.
- [x] Ein One-solution-only-Guardrail (`lint:design`) ist Bestandteil des Plans.
- [x] Clean-Slate ist nicht nötig: Es gibt ein bestehendes CSS-System, aber keine drei parallelen Theme-/Storage-Backends; der Plan konsolidiert dessen eine UI-Schicht.
