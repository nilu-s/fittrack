// Deterministic browser regression. Run against the local Vite server; all API
// traffic is mocked, no household records or live provider requests are used.
import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
const page = await context.newPage();
const now = new Date();
const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Berlin' }).format(now);
const id = '12345678-1234-4234-8234-123456789012';
const todo = { id, title: 'Termin am Zielort', status: 'open', priority: 2, due_date: day, start_time: '18:00:00',
  place_id: 'destination', place_name: 'Bestätigter Zielort', travel_mode: 'drive', travel_buffer_minutes: 10, travel_monitoring_enabled: true };
let state = { id: '22345678-1234-4234-8234-123456789012', todo_id: id, active: true, timezone: 'Europe/Berlin', lead_minutes: 60,
  live_active: false, origin_status: 'fixed', checked_at: now.toISOString(), location_checked_at: null,
  depart_at: new Date(+now + 30 * 60000).toISOString(), arrival_at: new Date(+now + 68 * 60000).toISOString(),
  starts_at: new Date(+now - 30 * 60000).toISOString(), expires_at: new Date(+now + 120 * 60000).toISOString(),
  duration_seconds: 2280, error: null, push_available: false, departure_change_minutes: -8, departure_changed_at: now.toISOString() };
let setups = 0;
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
await page.route('**/api/**', async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  let body = [];
  let status = 200;
  if (url.pathname === '/api/auth/me') body = { authenticated: true, id: '33345678-1234-4234-8234-123456789012', email: 'test@example.test', display_name: 'Test', alias_required: false };
  else if (url.pathname === '/api/travel') body = state ? [state] : [];
  else if (url.pathname === `/api/travel/${id}` && request.method() === 'DELETE') { state = null; status = 204; }
  else if (url.pathname === `/api/travel/${id}` && request.method() === 'PUT') {
    assert.deepEqual(request.postDataJSON(), { origin_place_id: 'origin', lead_minutes: 60, timezone: 'Europe/Berlin' }); setups++;
    body = { active: true };
  }
  else if (url.pathname === '/api/todo-planning/places') body = [{ place_id: 'origin', name: 'Bestätigter Startort', address: 'Testadresse' }];
  else if (url.pathname === '/api/todos') body = url.searchParams.get('date') === day ? [todo] : [];
  else if (url.pathname === '/api/day-entries') body = { date: url.searchParams.get('date'), weight_kg: 75 };
  else if (url.pathname === '/api/shopping') body = { id: 'shopping', items: [] };
  else if (url.pathname.startsWith('/api/training') || url.pathname === '/api/goals') body = {};
  else if (url.pathname.startsWith('/api/google-fit')) body = null;
  await route.fulfill({ status, contentType: 'application/json', ...(status === 204 ? {} : { body: JSON.stringify(body) }) });
});
try {
  await page.goto(process.env.TRAVEL_TEST_URL ?? 'http://127.0.0.1:4179');
  const row = page.locator('.daylist .item').filter({ hasText: 'Termin am Zielort' });
  await row.click();
  const editor = page.locator('dialog[open]').filter({ has: page.getByLabel('Titel', { exact: true }) });
  await editor.waitFor();
  assert.equal(await page.getByRole('dialog', { name: 'To-do-Aktionen' }).count(), 0);
  assert.equal(await page.locator('dialog[open]').count(), 1);
  assert.equal(await page.evaluate(() => document.activeElement?.tagName), 'BUTTON');
  await page.keyboard.press('Escape');
  await row.focus(); await page.keyboard.press('Enter');
  await editor.waitFor();
  await page.keyboard.press('Escape');
  await row.getByRole('button', { name: /Details zu/ }).click();
  await page.getByRole('button', { name: 'Bearbeiten', exact: true }).click();
  await editor.waitFor();
  assert.equal(await page.locator('dialog[open]').count(), 1);
  assert.deepEqual(errors, []);
  console.log('Direct todo edit: PASS');
} finally { await browser.close(); }
