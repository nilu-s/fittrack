import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless:true, args:['--no-sandbox'] });
const page = await browser.newPage({viewport:{width:390,height:844}, serviceWorkers:'block'});
const errors=[]; page.on('pageerror',e=>errors.push(e.message));
let recipe={id:'recipe-1',name:'Porridge',servings:1,status:'active',updated_at:'2026-09-10T10:00:00Z',ingredients:[{id:'ingredient-1',food_id:'food-1',quantity:100,unit:'g',sort_order:0}],instructions:[],nutrition:{kcal:300}};
let plan={id:'plan-1',name:'Woche',is_active:true,items:[],updated_at:'2026-09-10T10:00:00Z'};
let category={id:'category-1',name:'Frühstück',is_active:true,sort_order:0,updated_at:'2026-09-10T10:00:00Z'};
let failRecipe=true, recipeWrites=0;
await page.route('**/api/**',async route=>{
 const req=route.request(),path=new URL(req.url()).pathname;let body=[],status=200;
 if(path==='/api/auth/me')body={authenticated:true,id:'test',alias_required:false};
 else if(path==='/api/meal-categories')body=[category];
 else if(path==='/api/foods')body=[{id:'food-1',name:'Hafer',kcal:300}];
 else if(path==='/api/recipes')body=[recipe];
 else if(path==='/api/meal-plans')body=[plan];
 else if(path==='/api/recipes/recipe-1'&&req.method()==='PUT'){
  const data=req.postDataJSON();assert.equal(data.expected_updated_at,recipe.updated_at);assert.equal('id' in data.ingredients[0],false);
  if(failRecipe){status=422;body={detail:'Synthetic rejected update'};failRecipe=false;}
  else{recipe={...recipe,...data};recipeWrites++;body=recipe;}
 }else if(path==='/api/meal-plans/plan-1'&&req.method()==='PUT'){
  const data=req.postDataJSON();assert.equal(data.expected_updated_at,plan.updated_at);plan={...plan,...data};body=plan;
 }else if(path==='/api/meal-categories/category-1'&&req.method()==='PUT'){category={...category,...req.postDataJSON()};body=category;}
 await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
});
try{
 await page.goto(`${process.env.ENTRY_TEST_URL??'http://127.0.0.1:4179'}/settings/meals`);
 await page.getByRole('button',{name:'Verwalten',exact:true}).click();
 await page.getByRole('button',{name:'Bearbeiten',exact:true}).click();
 await page.getByLabel('Rezeptname',{exact:true}).last().fill('Frühstücksbrei');
 await page.getByLabel('Ertrag in Portionen').fill('1.5');
 await page.getByRole('button',{name:'Speichern',exact:true}).click();
 await page.getByRole('alert').waitFor();
 assert.equal(await page.getByLabel('Ertrag in Portionen').inputValue(),'1.5');
 await page.getByRole('button',{name:'Speichern',exact:true}).click();
 await page.getByText('Rezept und Nährwerte aktualisiert.',{exact:true}).waitFor();
 assert.equal(recipeWrites,1);assert.equal(recipe.name,'Frühstücksbrei');assert.equal(recipe.servings,1.5);
 await page.getByRole('button',{name:'Wochenplan',exact:true}).click();
 await page.getByRole('button',{name:'Frühstück am Montag: Rezept hinzufügen',exact:true}).click();
 const dialog=page.getByRole('dialog');
 assert.equal(await page.evaluate(()=>document.activeElement?.getAttribute('aria-label')),'Schließen');
 assert.ok((await dialog.boundingBox()).y<=1);
 await dialog.getByLabel('Bezeichnung des Platzhalters').fill('Essen unterwegs');
 await dialog.getByLabel('Geplante Uhrzeit').fill('12:30');
 await dialog.getByLabel('Portionen',{exact:true}).fill('1.5');
 await dialog.getByRole('button',{name:'Übernehmen'}).click();
 await page.getByRole('button',{name:/Frühstück am Montag: Essen unterwegs/}).waitFor();
 assert.equal(plan.items[0].planned_time,'12:30');assert.equal(plan.items[0].recipe_id,null);
 await page.reload();
 await page.getByRole('button',{name:/Frühstück am Montag: Essen unterwegs/}).click();
 assert.equal(await dialog.getByLabel('Geplante Uhrzeit').inputValue(),'12:30');
 assert.equal(await dialog.getByLabel('Bezeichnung des Platzhalters').inputValue(),'Essen unterwegs');
 assert.deepEqual(errors,[]);
 console.log('Meal settings browser: PASS (recipe failure retention/name/yield, version payload, placeholder/time/reload/top dialog)');
}finally{await browser.close();}
