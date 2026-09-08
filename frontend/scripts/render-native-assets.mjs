// Render the existing vector brand asset; no new logo or design direction.
import { readFile, readdir } from 'node:fs/promises';
import { chromium } from 'playwright';

const svg = await readFile(new URL('../static/brand-icon.svg', import.meta.url), 'utf8');
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage({ deviceScaleFactor: 1 });
async function render(path, width, height, fraction = .62) {
  await page.setViewportSize({ width, height });
  await page.setContent(`<html><body style="margin:0;background:#c9cbc0;display:grid;place-items:center;width:100vw;height:100vh"><img style="width:${Math.round(Math.min(width,height)*fraction)}px;height:auto" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}"></body></html>`);
  await page.locator('img').evaluate((image) => image.decode());
  await page.screenshot({ path });
}
try {
  await render('ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png', 1024, 1024);
  const sizes = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
  for (const [density, size] of Object.entries(sizes)) {
    for (const name of ['ic_launcher.png', 'ic_launcher_round.png']) await render(`android/app/src/main/res/mipmap-${density}/${name}`, size, size);
    await render(`android/app/src/main/res/mipmap-${density}/ic_launcher_foreground.png`, size * 2.25, size * 2.25, .44);
  }
  // Preserve platform-generated splash dimensions, replace template artwork.
  for (const folder of await readdir('android/app/src/main/res')) {
    if (!folder.startsWith('drawable')) continue;
    const path = `android/app/src/main/res/${folder}/splash.png`;
    try { const png = await readFile(path); await render(path, png.readUInt32BE(16), png.readUInt32BE(20), .22); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  for (const name of ['splash-2732x2732.png', 'splash-2732x2732-1.png', 'splash-2732x2732-2.png']) await render(`ios/App/App/Assets.xcassets/Splash.imageset/${name}`, 2732, 2732, .22);
  console.log('Native icons and splash assets rendered from the existing brand SVG.');
} finally { await browser.close(); }
