# FitTrack Design System

## Canonical reference

The daily page (`/`) is FitTrack’s visual source of truth. Secondary routes inherit its hierarchy: current action/value first, contextual information second, optional detail on explicit expansion.

## Rules

- **Dark only:** `--color-bg` with solid `--surface-*` layers and subtle borders. Gradients, glow and glassmorphism are not part of the system.
- **Semantic colour:** use `--status-*` for state and `--data-*` for stable data categories. Colour is always paired with readable text, an icon, or an accessible name.
- **One token source:** tokens are defined in `src/lib/styles/tokens.css`; shared implementation is in `src/lib/styles/primitives.css`.
- **Mobile interaction:** controls have at least `--control-min` (38px); press states are available without hover.
- **Motion:** use `--motion-fast` or `--motion-standard`; reduced-motion support is global.
- **Local styles:** route/component styles may compose layout and domain-specific data visualisation. They must consume tokens rather than introduce a new palette, radius scale, or elevation model.

## Primitives

| Primitive | Use |
|---|---|
| `ui-surface` / `UiSurface` | Stable card/section surface |
| `ui-button` / `UiButton` | Primary, secondary or danger action |
| `ui-icon-button` / `UiIconButton` | Icon-only action with accessible name |
| `ui-field` | Inputs/selects that need the shared field treatment |
| `ui-empty`, `ui-loading`, `ui-spinner` | Empty and loading states |
| `modal-overlay`, `modal-card` | Standard dialog surface/layer |

## Verification

Run `npm run lint:design` after UI changes. It asserts the token contract, global imports, main-shell primitive usage and the no-gradient Settings rule. Follow it with `npm run check` and `npm run build`.
