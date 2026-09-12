import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({args:['--no-sandbox']});
try {
  const page = await browser.newPage({serviceWorkers:'block'}); page.setDefaultTimeout(8000); page.on('pageerror', console.error);
  let item = {id:'tile-1',title:'Äpfel',icon_key:'initials',category_key:'other',quantity:2,unit:'kg',status:'open',source:'manual'};
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let body = [];
    if(path === '/api/auth/me') body = {authenticated:true,id:'test',email:'test@example.test',alias_required:false};
    else if(path.includes('/toggle')) {item = {...item,status:item.status === 'open' ? 'done' : 'open'};body=item;}
    else if(path === '/api/shopping') body = {id:'list',items:[item]};
    await route.fulfill({json:body});
  });
  for (const width of [320,390,1440]) {
    await page.setViewportSize({width,height:844});
    await page.goto(process.env.SHOPPING_TEST_URL ?? 'http://127.0.0.1:4182/shopping');
    const tile=page.getByRole('checkbox');
    await tile.waitFor(); console.log('loaded',width);
    const box=await page.locator('.shopping-list li').boundingBox();
    assert.ok(Math.abs(box.width-box.height)<1);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.equal(await page.locator('.shopping-list .initials').textContent(),'Ä');
    await tile.focus(); await page.keyboard.press('Space');
    await page.getByRole('checkbox',{checked:true}).waitFor(); console.log('toggled');
    await page.waitForFunction(()=>document.activeElement?.getAttribute('role')==='checkbox');
    await page.keyboard.press('Space');
    await page.getByRole('checkbox',{checked:false}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Äpfel bearbeiten'}).count(),1);
  }
  console.log('Shopping tiles: initials fallback, square, responsive, keyboard toggle and return focus PASS');
} finally {await browser.close();}
