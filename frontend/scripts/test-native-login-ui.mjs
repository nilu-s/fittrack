// Synthetic native bridge; no Google accounts, tokens, or provider calls.
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const base = process.env.LOGIN_TEST_URL ?? 'http://127.0.0.1:4179';
try {
  for (const scenario of ['android', 'android-home', 'ios']) {
    const platform = scenario === 'ios' ? 'ios' : 'android';
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
    await context.addInitScript(({ platform, scenario }) => {
      window.CapacitorCustomPlatform = { name: platform };
      window.loginTest = { calls: 0, outcome: 'cancel', authenticated: sessionStorage.getItem('synthetic-login') === 'yes', alias: scenario !== 'android-home' };
      window.Capacitor = {
        PluginHeaders: [
          { name: 'CroniclNative', methods: ['request', 'googleLogin', 'locationState', 'clearSession', 'stopLocation'].map(name => ({ name, rtype: 'promise' })) },
          { name: 'PushNotifications', methods: [{ name: 'addListener', rtype: 'callback' }, { name: 'removeListener', rtype: 'promise' }] },
        ],
        nativeCallback: () => 'synthetic-listener',
        nativePromise: async (plugin, method, options) => {
          if (method === 'googleLogin') {
            window.loginTest.calls++;
            await new Promise(resolve => { window.loginTest.finish = resolve; });
            if (window.loginTest.outcome === 'cancel') throw Object.assign(new Error('Anmeldung abgebrochen.'), { code: 'LOGIN_CANCELLED' });
            if (window.loginTest.outcome === 'denied') throw Object.assign(new Error('Dieses Google-Konto ist für Cronicl nicht freigegeben.'), { code: 'LOGIN_NOT_ALLOWED' });
            window.loginTest.authenticated = window.loginTest.outcome !== 'unverified';
            if (window.loginTest.authenticated) sessionStorage.setItem('synthetic-login', 'yes');
            return;
          }
          if (method === 'request') {
            const path = new URL(options.path, 'https://synthetic.test').pathname;
            let body = [];
            if (path === '/api/auth/me') body = window.loginTest.authenticated
              ? { authenticated: true, id: '33345678-1234-4234-8234-123456789012', email: 'test@example.test', alias_required: window.loginTest.alias }
              : { authenticated: false, email: null };
            if (path === '/api/auth/google/status') body = { connected: false, email: null };
            if (path === '/api/shopping') body = { items: [] };
            if (path === '/api/day-entries') body = { date: '2026-09-08' };
            return { status: 200, body: JSON.stringify(body), contentType: 'application/json' };
          }
          if (method === 'locationState') return { active: false };
        },
      };
    }, { platform, scenario });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/login');
    const button = page.getByRole('button', { name: 'Mit Google anmelden', exact: true });
    await button.waitFor();
    if (platform === 'ios') {
      await button.click();
      await page.getByRole('alert').filter({ hasText: 'iPhone' }).waitFor();
      assert.equal(await page.evaluate(() => window.loginTest.calls), 0);
    } else {
      await button.focus(); await page.keyboard.press('Enter');
      await page.waitForFunction(() => window.loginTest.finish);
      assert.equal(await page.getByRole('button', { name: 'Anmeldung läuft …' }).isDisabled(), true);
      await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => window.loginTest.calls), 1);
      await page.evaluate(() => window.loginTest.finish());
      await button.waitFor();
      await page.waitForFunction(() => document.activeElement?.tagName === 'BUTTON');
      assert.equal(await page.getByRole('alert').count(), 0);
      for (const outcome of ['denied', 'unverified', 'success']) {
        if (outcome === 'success') await page.evaluate(async () => {
          const { db } = await import('/src/lib/db.ts');
          await db.todos.add({ title: 'Synthetic previous-account record', status: 'open' });
          localStorage.setItem('app_account_id', 'previous-account');
        });
        await page.evaluate(outcome => { window.loginTest.outcome = outcome; window.loginTest.finish = null; }, outcome);
        await button.click();
        await page.waitForFunction(() => window.loginTest.finish);
        await page.evaluate(() => window.loginTest.finish());
        if (outcome === 'success') await page.waitForURL(scenario === 'android-home' ? base + '/' : '**/onboarding/alias');
        else {
          await page.getByRole('alert').waitFor();
          assert.match(await page.getByRole('alert').innerText(), outcome === 'denied' ? /nicht freigegeben/ : /Sitzung konnte nicht geprüft/);
          assert.match(page.url(), /\/login$/);
        }
      }
      assert.equal(await page.evaluate(() => localStorage.getItem('app_account_id')), '33345678-1234-4234-8234-123456789012');
      assert.equal(await page.evaluate(async () => {
        const { db } = await import('/src/lib/db.ts');
        return db.todos.filter(row => row.title === 'Synthetic previous-account record').count();
      }), 0);
    }
    if (scenario === 'android-home') {
      await page.goto(base + '/settings/integrations');
      await page.getByText(/Noch kein Zugriff auf Google-Daten/).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Trennen', exact: true }).count(), 0);
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(errors, []);
    await context.close();
  }
  console.log('Native login UI: cancellation, retry, denial, duplicate click, session verification, onboarding and iOS gate passed.');
} finally { await browser.close(); }
