import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
const errors = []; page.on('pageerror', e => errors.push(e.message));
let routine = { id: 'routine-1', title: 'Pflanzen', weekdays: [1], due_time: '18:00:00', priority: 2, is_active: false };
let space = { id: 'space-1', name: 'Haushalt', role: 'owner', members: [] };
let routineWrites = 0, spaceWrites = 0;
await page.route('**/api/**', async route => {
  const req = route.request(), path = new URL(req.url()).pathname;
  let body = [];
  if (path === '/api/auth/me') body = { authenticated: true, id: 'account-1', display_name: 'Test', alias_required: false };
  else if (path === '/api/todo-routines') body = [routine];
  else if (path === '/api/todo-routines/routine-1' && req.method() === 'PUT') {
    const data = req.postDataJSON(); assert.equal('is_active' in data, false);
    routine = { ...routine, ...data }; routineWrites++; body = routine;
  } else if (path === '/api/spaces') body = [space];
  else if (path === '/api/spaces/space-1' && req.method() === 'PUT') {
    assert.deepEqual(req.postDataJSON(), { name: 'Familie' });
    space = { ...space, ...req.postDataJSON() }; spaceWrites++; body = space;
  }
  await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
});
const base = process.env.ENTRY_TEST_URL ?? 'http://127.0.0.1:4179';
try {
  await page.goto(`${base}/settings/todos`);
  await page.getByRole('button', { name: 'Pflanzen bearbeiten' }).click();
  assert.equal(await page.evaluate(() => document.activeElement?.tagName), 'H2');
  await page.getByLabel('Bezeichnung').fill('Pflanzen gießen');
  await page.getByLabel('Uhrzeit').fill('19:30');
  await page.getByRole('button', { name: 'Änderungen speichern' }).click();
  await page.getByRole('button', { name: 'Pflanzen gießen bearbeiten' }).waitFor();
  assert.equal(routineWrites, 1); assert.equal(routine.is_active, false); assert.equal(routine.due_time, '19:30');
  await page.reload();
  await page.getByRole('button', { name: 'Pflanzen gießen bearbeiten' }).click();
  assert.equal(await page.getByLabel('Uhrzeit').inputValue(), '19:30');
  await page.goto(`${base}/settings/spaces`);
  await page.getByLabel('Bereich auswählen').selectOption('space-1');
  await page.getByLabel('Bereichsname').fill('Familie');
  await page.getByRole('button', { name: 'Namen speichern' }).click();
  await page.getByRole('heading', { name: 'Familie', exact: true }).waitFor();
  assert.equal(spaceWrites, 1);
  space.role = 'member'; await page.reload();
  await page.getByLabel('Bereich auswählen').selectOption('space-1');
  assert.equal(await page.getByLabel('Bereichsname').count(), 0);
  assert.deepEqual(errors, []);
  console.log('Entry settings browser regression: PASS (routine edit/reload/inactive, owner rename/member controls)');
} finally { await browser.close(); }
