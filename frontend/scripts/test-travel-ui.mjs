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
  await page.getByRole('button', { name: 'Anreise ansehen', exact: true }).waitFor();
  assert.equal(await page.locator('.todo-highlight').count(), 1);
  assert.match(await page.locator('.todo-highlight').innerText(), /8 Min. früher/);
  assert.match(await page.locator('.todo-highlight').innerText(), /Ab bestätigtem Startort/);
  await page.screenshot({ path: '/tmp/cronicl-travel-highlight.png', fullPage: true, animations: 'disabled' });
  const trigger = page.getByRole('button', { name: 'Anreise ansehen', exact: true });
  await trigger.focus(); await page.keyboard.press('Enter');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('dialog[open]'));
  assert.equal(await trigger.evaluate((button) => button === document.activeElement), true);
  await page.keyboard.press('Enter');
  const companion = page.getByRole('region', { name: 'Anreisebegleitung', exact: true });
  await page.screenshot({ path: '/tmp/cronicl-travel-detail.png', fullPage: true, animations: 'disabled' });
  await companion.getByRole('button', { name: 'Überwachung beenden', exact: true }).click();
  await companion.getByRole('combobox', { name: /^Startort/ }).selectOption('place');
  await companion.getByLabel('Startort suchen', { exact: true }).fill('Startort');
  await companion.getByRole('button', { name: 'Orte suchen', exact: true }).click();
  await companion.getByRole('button', { name: /Bestätigter Startort/ }).click();
  await companion.getByRole('button', { name: 'Startort bestätigen und überwachen', exact: true }).click();
  await page.waitForFunction(() => document.body.innerText.includes('Überwachung eingerichtet.'));
  assert.equal(setups, 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  assert.deepEqual(errors, []);
  console.log('travel browser regression: PASS (one highlight, keyboard detail, stop, confirmed origin, no overflow)');
} catch (error) { console.error(await page.locator('body').innerText()); throw error; } finally { await browser.close(); }
