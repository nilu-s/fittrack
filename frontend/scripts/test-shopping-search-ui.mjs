import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({ args: ['--no-sandbox'] });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
  let items = [{ id: 'done-milk', title: 'Milch', category_key: 'dairy', icon_key: 'milk', pictogram_url: '', status: 'done', source: 'manual', sort_order: 0, updated_at: '2026-09-15T12:00:00Z' }];
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === '/api/auth/me') return route.fulfill({ json: { authenticated: true, id: 'test', email: 'test@example.test', alias_required: false } });
    if (path === '/api/shopping' && request.method() === 'GET') return route.fulfill({ json: { id: 'list', items } });
    if (path === '/api/shopping/items' && request.method() === 'POST') {
      const { title } = request.postDataJSON();
      const item = { id: `new-${items.length}`, title, category_key: 'other', icon_key: 'initials', pictogram_url: '', status: 'open', source: 'manual', sort_order: 0, updated_at: '2026-09-17T12:00:00Z' };
      items = [...items, item];
      return route.fulfill({ json: item });
    }
    return route.fulfill({ json: [] });
  });

  await page.goto(process.env.SHOPPING_TEST_URL ?? 'http://127.0.0.1:4182/shopping');
  await page.getByRole('button', { name: 'Milch hinzufügen' }).click();
  await page.getByRole('checkbox', { name: /Milch erledigen/ }).waitFor();
  await page.locator('#shopping-add').fill('to');
  await page.getByRole('button', { name: 'Tomaten hinzufügen' }).click();
  await page.getByRole('checkbox', { name: /Tomaten erledigen/ }).waitFor();
  assert.equal(await page.locator('#shopping-add').inputValue(), '');
  console.log('Shopping search: suggestions are filtered and add immediately PASS');
} finally {
  await browser.close();
}
