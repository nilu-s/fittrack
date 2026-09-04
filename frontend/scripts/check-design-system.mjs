import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const read = (path) => readFileSync(resolve(root, path), 'utf8');
const readSourceTree = (path) => readdirSync(resolve(root, path), { withFileTypes: true }).flatMap((entry) => {
  const nested = `${path}/${entry.name}`;
  return entry.isDirectory() ? readSourceTree(nested) : /\.(svelte|css|ts)$/.test(entry.name) ? [read(nested)] : [];
});
const expect = (value, label) => {
  if (!value) throw new Error(`Design contract failed: ${label}`);
};

const tokens = read('src/lib/styles/tokens.css');
const primitives = read('src/lib/styles/primitives.css');
const app = read('src/app.css');
const settings = read('src/routes/settings/+page.svelte');
const settingsTile = read('src/lib/components/SettingsTile.svelte');
const sportSettings = read('src/routes/settings/sport/+page.svelte');
const layout = read('src/routes/+layout.svelte');
const manifest = read('static/manifest.json');
const appHtml = read('src/app.html');
const source = readSourceTree('src').join('\n');
const deprecatedTokens = ['bg', 'card', 'card-2', 'border', 'border-2', 'text', 'text-dim', 'text-faint', 'green', 'blue', 'amber', 'purple', 'pink', 'red', 'radius', 'radius-sm', 'radius-md', 'radius-lg', 'radius-xl', 'gap-sm', 'gap-md', 'gap-lg'];

for (const token of ['--color-bg:', '--surface-default:', '--surface-accent:', '--action-primary:', '--text-primary:', '--status-success:', '--data-sleep-deep:', '--space-4:', '--radius-surface:', '--motion-fast:', '--control-min:']) {
  expect(tokens.includes(token), `missing token ${token}`);
}
for (const token of deprecatedTokens) {
  expect(!new RegExp(`var\\(--${token}\\)`).test(source), `deprecated token used: --${token}`);
  expect(!new RegExp(`^\\s*--${token}:`, 'm').test(tokens), `deprecated token declared: --${token}`);
}
for (const primitive of ['.ui-surface', '.ui-button', '.ui-icon-button', '.ui-field', ':focus-visible', 'prefers-reduced-motion']) {
  expect(primitives.includes(primitive), `missing primitive ${primitive}`);
}
expect(app.includes("@import './lib/styles/tokens.css'"), 'app does not import tokens');
expect(app.includes("@import './lib/styles/primitives.css'"), 'app does not import primitives');
expect(!settings.includes('linear-gradient'), 'settings uses a forbidden gradient');
expect(settings.includes('class="settings-list"'), 'settings does not use the calm list composition');
expect(settings.includes('class="intro"'), 'settings does not provide a clear page hierarchy');
expect(settingsTile.includes('class="settings-row"'), 'settings item does not use a calm list row');
expect(!sportSettings.includes('gradient'), 'sport settings retains a competing gradient visual language');
expect(!sportSettings.includes('backdrop-filter'), 'sport settings retains a competing glass visual language');
expect(!sportSettings.includes('rgba('), 'sport settings retains local colour values');
expect(manifest.includes('"theme_color": "#c9cbc0"'), 'manifest does not use the canonical muted-light background');
expect(appHtml.includes('content="#c9cbc0"'), 'HTML shell does not use the canonical muted-light theme colour');
expect(layout.includes('AccountMenu'), 'main shell does not provide the canonical account menu');
console.log('design contract: PASS');
