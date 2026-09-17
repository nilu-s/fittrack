import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({args:['--no-sandbox']});
try {
  const page = await browser.newPage({viewport:{width:390,height:844}, serviceWorkers:'block'});
  page.setDefaultTimeout(8000);
  let item = {id:'icon-1',title:'Hafermilch',icon_key:'milk',pictogram_url:'/api/shopping/items/icon-1/pictogram',category_key:'dairy',quantity:null,unit:null,note:null,status:'open',source:'manual'};
  let update = null;
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/auth/me') return route.fulfill({json:{authenticated:true,id:'test',email:'test@example.test',alias_required:false}});
    if (path === '/api/shopping') return route.fulfill({json:{id:'list',items:[item]}});
    if (path === '/api/shopping/items/icon-1/pictogram') return route.fulfill({contentType:'image/svg+xml',headers:{'X-Pictogram-State':'available'},body:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>'});
    if (path === '/api/shopping/items/icon-1' && route.request().method() === 'PUT') {
      update = JSON.parse(route.request().postData() ?? '{}');
      item = {...item, ...update};
      return route.fulfill({json:item});
    }
    return route.fulfill({json:[]});
  });
  await page.goto(process.env.SHOPPING_TEST_URL ?? 'http://127.0.0.1:4182/shopping');
  await page.getByRole('checkbox', {name:'Hafermilch erledigen'}).waitFor();
  await page.waitForSelector('.article-icon[data-icon-key="milk"]');
  assert.equal(await page.locator('.article-icon').evaluate((element) => getComputedStyle(element).filter), 'brightness(0) invert(1)');
  await page.getByRole('checkbox', {name:/Hafermilch erledigen/}).click({button:'right'});
  assert.equal(await page.getByRole('group', {name:'Illustration'}).count(), 0);
  await page.locator('#shopping-edit-title').fill('Haferdrink');
  await page.getByRole('button', {name:'Speichern'}).click();
  await page.getByRole('checkbox', {name:'Haferdrink erledigen'}).waitFor();
  assert.deepEqual(update, {title:'Haferdrink',quantity:null,unit:null,note:null});
  console.log('Shopping pictogram delivery: proxied tile and no browser-side visual override PASS');
} finally { await browser.close(); }
