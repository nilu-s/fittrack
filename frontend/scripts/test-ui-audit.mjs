import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const base=process.env.ENTRY_TEST_URL??'http://127.0.0.1:4179',phase=process.env.UI_AUDIT_PHASE??'after';
const out=new URL(`../../docs/evidence/2026-09-12-ui-audit/${phase}/`,import.meta.url);await mkdir(out,{recursive:true});
const today=new Intl.DateTimeFormat('en-CA').format(new Date());
const fixtures={
 '/auth/me':{authenticated:true,id:'test',display_name:'Alex Beispiel',email:'alex@example.test',alias_required:false},
 '/todos':[{id:'todo-1',title:'Wochenende gemeinsam planen',status:'open',priority:2,due_date:today}],
 '/notes':[{id:'note-1',title:'Ideen für den Herbsturlaub',body:'Wandern und gemeinsam kochen.',status:'active',space_id:null}],
 '/spaces':[{id:'space-1',name:'Familie',role:'owner',members:[]}],
 '/shopping':{id:'shopping-1',items:[{id:'item-1',title:'Haferflocken',quantity:500,unit:'g',category_key:'pantry',icon_key:'pantry',status:'open',source:'manual'}]},
 '/shopping/meal-preview':{plan_name:'Meine Woche',items:[{title:'Haferflocken',quantity:500,unit:'g'}]},
 '/meal-categories':[{id:'category-1',name:'Frühstück',is_active:true,sort_order:0}],
 '/recipes':[{id:'recipe-1',name:'Haferflocken mit Obst',servings:1,status:'active',ingredients:[],instructions:[],nutrition:{kcal:380,protein:15,carbs:50,fat:12}}],
 '/foods':[{id:'food-1',name:'Haferflocken',kcal:380}],'/meal-plans':[{id:'plan-1',name:'Meine Woche',is_active:true,items:[]}],
 '/meal-entries':[{id:'meal-1',category_id:'category-1',name:'Haferflocken mit Obst',recipe_id:'recipe-1',status:'planned',portion_factor:1,nutrition:{kcal:380,protein:15},ingredients:[]}],
 '/training-units':[{id:'unit-1',name:'Ganzkörper',unit_type:'gym',is_active:true}],
 '/templates/rotation':[{slot:0,training_type:'Ganzkörper',weekday:0,frequency_weeks:1,week_offset:0}],
 '/exercises':[{id:'exercise-1',exercise_name:'Kniebeugen',training_type:'Ganzkörper',target_sets:'3',target_reps_low:8,target_reps_high:12,target_rir:2,progression_strategy:'double_progression'}],
 '/training':{training_type:'Ganzkörper',exercises:[]},'/training/next':{training_type:'Ganzkörper',exercises:[{exercise_name:'Kniebeugen',target_sets:'3',target_reps_low:8,target_reps_high:12,target_weight_kg:40,target_rir:2}]},
 '/todo-routines':[{id:'routine-1',title:'Pflanzen gießen',weekdays:[0,3],priority:2,is_active:true,due_time:'18:00'}],
 '/contacts':[{id:'contact-1',display_name:'Robin Beispiel',alias:'robin'}],'/account/body-profile':{height_cm:178,birth_date:null,calculation_sex:null},
 '/goals':{kcal:2200,protein:120,steps:8000,sleep_hours:8},'/auth/google/status':{connected:false},
 '/stats/week':{avg_weight:75,avg_kcal:2100,avg_steps:7600,training_days:3,todo_done:8,todo_total:12},'/stats/trend':{points:[{date:today,value:75}]},
 '/scale-measurements':[{id:'scale-1',weight_kg:75,measured_at:new Date().toISOString()}]
};
const browser=await chromium.launch({headless:true,args:['--no-sandbox']}),results=[];
const routes=['/','/week','/shopping','/contacts','/settings','/settings/profile','/settings/scale','/settings/meals','/settings/sport','/settings/todos','/settings/spaces','/settings/data','/settings/integrations','/settings/goals','/login','/onboarding/alias'];
try{for(const [size,viewport] of Object.entries({small:{width:320,height:568},mobile:{width:390,height:844},desktop:{width:1440,height:1000}})){
 const context=await browser.newContext({viewport,serviceWorkers:'block',locale:'de-DE',timezoneId:'Europe/Berlin',hasTouch:size!=='desktop'});
 await context.route('**/api/**',async route=>{const url=new URL(route.request().url()),path=url.pathname.slice(4);let body=fixtures[path]??[];
 if(path==='/auth/me'){const screen=new URL(route.request().headers().referer??base).pathname;if(screen==='/onboarding/alias')body={...fixtures[path],alias_required:true};if(screen==='/login')body={authenticated:false};}
 if(path==='/day-entries')body={date:url.searchParams.get('date'),weight_kg:75,steps:7600,sleep_hours:7.5,training_type:'Ganzkörper'};
 if(path.startsWith('/google-fit'))body=null;if(path==='/sync')body={changes:{},server_time:new Date().toISOString()};
 await route.fulfill({contentType:'application/json',body:JSON.stringify(body)});});
 const page=await context.newPage();page.setDefaultTimeout(7000);let errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function visit(path){await page.goto(base+path);await page.waitForFunction(()=>document.querySelector('main')?.innerText.trim().length>30);await page.waitForLoadState('networkidle');}
 async function capture(name,dialog=false){await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:new URL(`${size}-${name}.png`,out).pathname,fullPage:!dialog,animations:'disabled'});
 const state=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,overflowElements:[...document.querySelectorAll('main *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1 && getComputedStyle(e).position!=='fixed').slice(0,12).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})),dialogs:[...document.querySelectorAll('dialog[open],[role="dialog"]')].map(d=>({name:d.getAttribute('aria-label')??d.getAttribute('aria-labelledby'),modal:d.matches(':modal'),focus:d.contains(document.activeElement),width:Math.round(d.getBoundingClientRect().width),overflow:d.scrollWidth>d.clientWidth+1}))}));
 results.push({size,name,...state,errors:[...errors]});errors=[];
 if(dialog&&size==='small'&&/editor|planner|unit|training/.test(name)){
  const last=page.locator('dialog[open] button:visible').last();await last.scrollIntoViewIfNeeded();
  const box=await last.boundingBox();assert.ok(box.y>=0&&box.y+box.height<=viewport.height+1,`${name}: last action unreachable`);
  await page.screenshot({path:new URL(`${size}-${name}-end.png`,out).pathname,animations:'disabled'});
 }

 if(dialog&&phase==='after'){
  if(name==='todo-editor')assert.equal(await page.evaluate(()=>{
    const target=document.querySelector('dialog[open]');
    const touch=y=>new Touch({identifier:1,target,clientX:100,clientY:y});
    target.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[touch(100)]}));
    const move=new TouchEvent('touchmove',{bubbles:true,cancelable:true,touches:[touch(180)]});target.dispatchEvent(move);
    target.dispatchEvent(new TouchEvent('touchend',{bubbles:true,changedTouches:[touch(180)]}));return move.defaultPrevented;
  }),false,'Pull-to-refresh captured dialog scroll');
  assert.ok(state.dialogs.every(d=>!d.overflow),`${size}/${name}: dialog overflow`);assert.ok(state.dialogs.every(d=>d.focus),`${name}: opening focus`);assert.ok(state.dialogs.some(d=>d.modal),`${size}/${name}: native modal`);for(let i=0;i<35;i++){await page.keyboard.press('Tab');assert.ok(await page.evaluate(()=>document.activeElement===document.body || document.activeElement?.closest('dialog[open]')),`${name}: focus escaped`);}}}
 async function open(name,button){console.log(size,name);if(name==='todo-detail'){await button.focus();await page.keyboard.press('Enter');}else await button.click();await page.locator('dialog[open],[role="dialog"]').first().waitFor();await capture(name,true);await page.keyboard.press('Escape');if(phase==='after'){await page.locator('dialog[open],[role="dialog"]').waitFor({state:'hidden'});if(await button.count() && await button.isVisible())assert.ok(await button.evaluate(e=>e===document.activeElement),`${name}: focus not restored`);}}
 for(const path of routes){await visit(path);await capture(path==='/'?'day':path.slice(1).replaceAll('/','-'));}
 await visit('/');await open('calendar',page.getByRole('button',{name:/Kalender öffnen/}));
 await visit('/');await open('assistant',page.getByRole('button',{name:'KI-Assistent öffnen'}));
 await visit('/settings/sport');await open('sport-planner',page.getByRole('button',{name:/Ganzkörper Wöchentlich/}));
 await visit('/settings/sport');await page.getByRole('tab',{name:/Einheiten/}).click();await capture('sport-units');await open('sport-create',page.getByRole('button',{name:/Neue Einheit/}));
 await visit('/settings/sport');await page.getByRole('tab',{name:/Einheiten/}).click();await capture('sport-units');await open('sport-unit',page.getByRole('button',{name:/Ganzkörper.*Übung/}));
 await visit('/settings/meals');await open('meal-plan',page.getByRole('button',{name:'Frühstück am Montag: Rezept hinzufügen',exact:true}));

 await visit('/');await page.getByRole('button',{name:/Kontomenü/}).click();await capture('account-menu');await page.keyboard.press('Escape');
 await open('todo-editor',page.locator('.daylist .item').filter({hasText:'Wochenende gemeinsam planen'}));
 await open('todo-detail',page.getByRole('button',{name:/Details zu Wochenende/}));
 await open('training-detail',page.getByRole('button',{name:/Details zu Ganzkörper/}));
 await open('meal-detail',page.getByRole('button',{name:/Details zu Frühstück/}));
 await page.locator('.daylist .item').filter({hasText:'Frühstück'}).click();await open('meal-editor',page.getByRole('button',{name:'Mahlzeit anpassen',exact:true}));
 await open('steps-trend',page.getByRole('button',{name:/Schritte. Details öffnen/}));
 await open('sleep-trend',page.getByRole('button',{name:/Stunden Schlaf. Details öffnen/}));
 await open('nutrition',page.getByRole('button',{name:/Energie.*Details öffnen/}));
 await page.getByRole('button',{name:/Kilogramm Gewicht. Details öffnen/}).click();await capture('weight-detail',true);
 await page.getByRole('button',{name:'Verlauf öffnen'}).click();await capture('weight-trend',true);await page.keyboard.press('Escape');
 await visit('/');await page.getByRole('button',{name:'Notiz-Board öffnen'}).click();await capture('notes');
 await open('note-editor',page.getByRole('button',{name:/Ideen für den Herbsturlaub/}));
 await page.getByRole('button',{name:'Familie öffnen'}).click();await capture('note-planning');
 await visit('/');await page.getByRole('button',{name:'Einkaufsliste öffnen'}).click();await capture('shopping-panel');
 await visit('/shopping');await open('shopping-editor',page.getByRole('button',{name:'Haferflocken bearbeiten'}));
 await open('shopping-import',page.getByRole('button',{name:'Plan übernehmen'}));
 await visit('/settings/meals');await page.getByRole('button',{name:'Verwalten',exact:true}).click();await capture('meal-manage');
 await page.getByRole('button',{name:'Bearbeiten',exact:true}).click();await capture('recipe-editor');

 if(size==='mobile'){
  await context.route('**/api/stats/week?*',r=>r.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await visit('/week');await page.getByRole('alert').waitFor();await capture('week-error');
  await context.unroute('**/api/stats/week?*');await page.getByRole('button',{name:'Erneut versuchen'}).click();await page.getByText('Gewicht',{exact:true}).waitFor();await capture('week-recovered');
  await visit('/');await page.getByRole('button',{name:'KI-Assistent öffnen'}).click();
  await context.route('**/api/todo-planning/assistant',r=>r.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await page.getByLabel('Deine Frage').fill('Hilf mir beim Wochenplan');await page.getByRole('button',{name:'Fragen',exact:true}).click();await page.getByRole('alert').waitFor();await capture('assistant-error',true);await page.keyboard.press('Escape');
  await context.route('**/api/shopping/meal-preview?*',r=>r.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await visit('/shopping');await page.getByRole('button',{name:'Plan übernehmen'}).click();await page.getByRole('alert').waitFor();await capture('shopping-import-error',true);await page.keyboard.press('Escape');
 }

 await visit('/settings/spaces');await page.getByLabel('Bereich auswählen').selectOption('space-1');await capture('space-manager');
 await visit('/settings/sport');await page.getByRole('tab',{name:/Einheiten/}).click();await page.getByRole('button',{name:/Ganzkörper.*Übung/}).click();await page.getByRole('button',{name:'Progression & Details'}).click();await capture('sport-progression',true);await page.keyboard.press('Escape');
 await context.close();
}}finally{await writeFile(new URL('results.json',out),JSON.stringify(results,null,2));await browser.close();}
console.log(`UI audit ${phase}: ${results.length} screenshots; ${results.filter(r=>r.overflow).length} page overflows; ${results.flatMap(r=>r.errors).length} runtime errors`);

if(phase==='after'){assert.deepEqual(results.filter(r=>r.overflow).map(r=>`${r.size}/${r.name}`),[],'Page overflow');assert.deepEqual(results.flatMap(r=>r.errors),[],'Runtime errors');}
