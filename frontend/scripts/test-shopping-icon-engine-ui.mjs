import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({args:['--no-sandbox']});
try {
  const page = await browser.newPage({viewport:{width:390,height:844}, serviceWorkers:'block'});
  page.setDefaultTimeout(8000);
  let item = {id:'icon-1',title:'Hafermilch',icon_key:'milk',category_key:'dairy',quantity:null,unit:null,note:null,status:'open',source:'manual'};
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/auth/me') return route.fulfill({json:{authenticated:true,id:'test',email:'test@example.test',alias_required:false}});
    if (path === '/api/shopping') return route.fulfill({json:{id:'list',items:[item]}});
    if (path === '/api/shopping/items/icon-1' && route.request().method() === 'PUT') {
      item = {...item, ...JSON.parse(route.request().postData() ?? '{}')};
      return route.fulfill({json:item});
    }
    return route.fulfill({json:[]});
  });
  await page.goto(process.env.SHOPPING_TEST_URL ?? 'http://127.0.0.1:4182/shopping');
  await page.getByRole('checkbox', {name:'Hafermilch erledigen'}).waitFor();
  assert.equal(await page.locator('.article-icon--dairy').count(), 1);
  await page.getByRole('button', {name:'Hafermilch bearbeiten'}).click();
  await page.getByRole('button', {name:'Pasta auswählen'}).click();
  assert.equal(await page.getByRole('button', {name:'Pasta auswählen'}).getAttribute('aria-pressed'), 'true');
  await page.getByRole('button', {name:'Speichern'}).click();
  await page.waitForSelector('.article-icon--pantry');
  console.log('Shopping icon engine: illustrated tile, keyboard-native picker and persisted choice PASS');
} finally { await browser.close(); }
