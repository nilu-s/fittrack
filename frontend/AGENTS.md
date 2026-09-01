# Frontend area rules

Read the governing spec and `docs/design-system.md` before changing a user flow
or shared visual primitive. The browser never sends an account identity; API
calls rely on the verified session and account changes clear private local data.

Keep API/types changes coordinated with the versioned backend contract. Do not
introduce a legacy route, local sync entity, or styling system without an
approved compatibility decision and removal condition.

Run `npm run check`, `npm run lint:design`, and `npm run build`. Add or update a
browser regression for changed authentication, sync, dialog, or critical day
feed behavior once the browser suite exists.
