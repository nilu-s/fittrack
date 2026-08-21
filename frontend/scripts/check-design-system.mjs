import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const read = (path) => readFileSync(resolve(root, path), 'utf8');
const expect = (value, label) => {
  if (!value) throw new Error(`Design contract failed: ${label}`);
};

const tokens = read('src/lib/styles/tokens.css');
const primitives = read('src/lib/styles/primitives.css');
const app = read('src/app.css');
const settings = read('src/routes/settings/+page.svelte');
const layout = read('src/routes/+layout.svelte');
const manifest = read('static/manifest.json');
const appHtml = read('src/app.html');

for (const token of ['--color-bg:', '--surface-default:', '--text-primary:', '--status-success:', '--data-sleep-deep:', '--space-4:', '--radius-surface:', '--motion-fast:', '--control-min:']) {
  expect(tokens.includes(token), `missing token ${token}`);
}
for (const primitive of ['.ui-surface', '.ui-button', '.ui-icon-button', '.ui-field', ':focus-visible', 'prefers-reduced-motion']) {
  expect(primitives.includes(primitive), `missing primitive ${primitive}`);
}
expect(app.includes("@import './lib/styles/tokens.css'"), 'app does not import tokens');
expect(app.includes("@import './lib/styles/primitives.css'"), 'app does not import primitives');
expect(!settings.includes('linear-gradient'), 'settings uses a forbidden gradient');
expect(manifest.includes('"theme_color": "#0b0c0e"'), 'manifest does not use the canonical background');
expect(appHtml.includes('content="#0b0c0e"'), 'HTML shell does not use the canonical theme colour');
expect(layout.includes('UiIconButton'), 'main shell does not use the canonical icon button');
console.log('design contract: PASS');
