/* Start python3 -m http.server 8819 --bind 127.0.0.1 in the checkout.
 * RUOSUEN_BASE_URL targets Pages. RUOSUEN_FONT_FALLBACK=1 explicitly tests
 * system-font rendering when external Google Fonts cannot be reached.
 */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.RUOSUEN_BASE_URL || 'http://127.0.0.1:8819/';
const WORLD='docs/01_プレイヤー向け世界観.md';
const CITY='docs/04_自由迷宮都市と組織.md';
const NEXT='adventures/次の冒険.md';
const PREP='players/キャラクター作成ガイド.md';
const SHARE='players/キャラクター提出テンプレート.md';
const scenes=['opening','vista','cargo','depths','explorers','territory','tavern','next'];
const institutions=['円環商館の酒場','セレド王立地図院','底空船廠','伽藍の塔','聖路教会','深青の石工房'];
const errors=[];
const url=path=>base+'#/'+encodeURIComponent(path);
const paint=page=>page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
async function ready(page,path) {
  await page.waitForFunction(path=>document.querySelector('#article-content').dataset.source===path &&
    document.querySelector('#article-content').getAttribute('aria-busy')==='false',path);
  assert.ok(!(await page.locator('#article-content').innerText()).includes('資料を読み込めませんでした'));
}
async function nativeSeek(page,id,fraction=.27) {
  await page.evaluate(({id,fraction})=>{
    const sequence=document.querySelector('.film-sequence');
    const frames=[...sequence.querySelectorAll('[data-film-scene]')];
    const travel=parseFloat(sequence.style.getPropertyValue('--film-travel'));
    const step=travel/(frames.length-1+.65);
    scrollTo({top:sequence.getBoundingClientRect().top+scrollY+(frames.findIndex(e=>e.id===id)+fraction)*step,behavior:'instant'});
  },{id,fraction});
  await page.waitForFunction(id=>document.querySelector('.film-sequence').dataset.activeScene===id,id);
  await paint(page);
}
async function restored(page,id,y) {
  await page.waitForFunction(({id,y})=>!document.querySelector('#home-view').classList.contains('hidden')&&
    document.querySelector('.film-sequence').dataset.activeScene===id&&Math.abs(scrollY-y)<=2,{id,y});
}
async function atY(page,y) {
  try { await page.waitForFunction(y=>Math.abs(scrollY-y)<=2,y); }
  catch(error) { console.error('Reading restoration', await page.evaluate(y=>({expected:y,actual:scrollY,body:document.body.className,source:document.querySelector('#article-content').dataset.source,entry:visits.get(activeKey),panels:[...document.querySelectorAll('.story-panel')].map(e=>e.className)}),y)); throw error; }
}
async function readAt(page,y=420) {
  const actual = await page.evaluate(y=>{scrollTo({top:y,behavior:'instant'});return scrollY},y);
  await paint(page);
  return actual;
}
async function checkJourney(page,width) {
  await page.goto(base,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.RuosuenStory&&document.querySelector('.is-scroll-story'));
  assert.deepEqual(await page.locator('[data-film-scene]').evaluateAll(es=>es.map(e=>e.id)),scenes);
  assert.deepEqual(await page.locator('.film-sequence [data-film-scene]').evaluateAll(es=>es.map(e=>e.id)),scenes.slice(1));
  const artwork=await page.locator('[data-film-scene] img').evaluateAll(es=>es.map(e=>e.getAttribute('src')));
  assert.equal(new Set(artwork).size,8,'Every film scene needs distinct artwork');
  assert.equal(await page.locator('.film-story-hint,.film-scene-steps,.film-story-progress').count(),0);
  assert.equal(await page.locator('.brand-city-name').innerText(),'ルオスエン');
  assert.equal(await page.locator('#opening h1').textContent(),'自由迷宮都市ルオスエン');
  assert.equal(await page.locator('#vista h2').textContent(),'この街の下には、まだ世界がある。');
  assert.equal(await page.evaluate(()=>window.RuosuenStory.capture()),null,'Opening uses normal document scroll');
  const continuation=await page.locator('#vista').boundingBox();
  assert(continuation.y>0&&continuation.y<900,'Next artwork should peek below the introduction');
  assert.equal(await page.locator('.film-artwalk').count(),0);
  assert.equal(await page.locator('.site-header .nav-start').isVisible(),true);
  const distance = await page.locator('.film-sequence').evaluate(e=>parseFloat(e.style.getPropertyValue('--film-travel')));
  const stageHeight = await page.locator('.film-stage').evaluate(e=>e.clientHeight);
  assert(distance/stageHeight<4.2,'The film should take about four stage-heights of scrolling');
  await nativeSeek(page,'vista',.2);
  assert(await page.locator('#cargo').evaluate(e=>Number(e.style.opacity)>.1),'A small scroll must visibly start the dissolve');
  const menu=page.locator('.header-menu summary');
  if(await menu.isVisible()) await menu.click();
  await page.getByRole('link',{name:'世界を知る',exact:true}).click();await ready(page,WORLD);
  await page.locator('#reader-bottom [data-return-to-story]').click();
  await page.waitForFunction(()=>!document.querySelector('#home-view').classList.contains('hidden'));
  await nativeSeek(page,'vista',0);
  // Actual native scroll, next/previous controls, and deep links all choose the same scenes.
  for(let i=1;i<scenes.length-1;i++) {
    await nativeSeek(page,scenes[i]);
    const img=page.locator('#'+scenes[i]+' img');
    assert(await img.evaluate(i=>i.complete&&i.naturalWidth>0));
    assert.equal(await page.locator('#film-next').getAttribute('href'),'#'+scenes[i+1]);
    await page.locator('#film-next').click();
    await page.waitForFunction(id=>document.querySelector('.film-sequence').dataset.activeScene===id,scenes[i+1]);
    await page.locator('#film-prev').click();
    await page.waitForFunction(id=>document.querySelector('.film-sequence').dataset.activeScene===id,scenes[i]);
  }
  for(const id of scenes) {
    await page.goto(base+'#'+id);
    if(id==='opening') await page.waitForFunction(()=>scrollY<10);
    else await page.waitForFunction(id=>document.querySelector('.film-sequence').dataset.activeScene===id,id);
  }
  assert((await page.locator('#territory').textContent()).includes('願いが叶うという'));
  // Depart without a scene hash: preserve the actual movie position through multiple pages.
  await page.goto(base,{waitUntil:'networkidle'});
  await nativeSeek(page,'next',.2);
  const movieY=await page.evaluate(()=>scrollY);
  await page.locator('#next a').click();await ready(page,WORLD);
  assert.equal(await page.locator('.story-panel').count(),6);
  const worldText=await page.locator('#article-content').innerText();
  for(const term of ['マナ','魔石','純度','大転流','願いが叶う'])assert(worldText.includes(term));
  const readingY=await readAt(page);
  assert(readingY>100);
  await page.goBack();await restored(page,'next',movieY);
  await page.goForward();await ready(page,WORLD);await atY(page,readingY);
  await page.locator('#article-content > p:last-child a').scrollIntoViewIfNeeded();await paint(page);
  const departWorldY=await page.evaluate(()=>scrollY);
  await page.locator('#article-content > p:last-child a').click();await ready(page,CITY);
  assert.equal(await page.locator('.story-panel').count(),10);
  assert.deepEqual(await page.locator('#story-chapters a').allTextContents(),institutions);
  for (const image of await page.locator('.story-panel img').all()) {
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(i=>i.decode());
    assert(await image.evaluate(i=>i.naturalWidth>0));
  }
  await page.locator('#story-chapters').getByRole('link',{name:'伽藍の塔',exact:true}).click();
  const tower=page.locator('.story-panel').filter({has:page.locator('h2',{hasText:'伽藍の塔'})});
  assert(await tower.isVisible());
  await paint(page);
  const cityY=await page.evaluate(()=>scrollY);
  assert(cityY>1000);
  await page.goBack();await ready(page,WORLD);await atY(page,departWorldY);
  await page.goForward();await ready(page,CITY);await atY(page,cityY);
  await page.locator('#reader-bottom [data-return-to-story]').click();await restored(page,'next',movieY);
  // Complete the intended world -> city -> next-session -> creation -> sharing path.
  for(const [path,following] of [[WORLD,CITY],[CITY,NEXT],[NEXT,PREP],[PREP,SHARE]]) {
    await page.goto(url(path));await ready(page,path);
    await page.locator('#reader-bottom .reader-related a').first().click();await ready(page,following);
  }
  await page.goto(url(NEXT));await ready(page,NEXT);
  assert((await page.locator('#article-content').innerText()).includes('準備中'));
  await page.goto(url(PREP));await ready(page,PREP);
  const prep=await page.locator('#article-content').innerText();
  for(const term of ['蘇生','未確定','話し合','アアシマール'])assert(prep.includes(term));
  assert(await page.locator('.table-wrap').count());
  // Curated navigation has five pages and no author-only or archived destinations.
  assert.equal(await page.locator('#journey-nav a').count(),5);
  const hrefs=await page.locator('#journey-nav a').evaluateAll(es=>es.map(e=>decodeURIComponent(e.getAttribute('href'))));
  assert(!hrefs.some(h=>/notes\/|world\/|DECISIONS/.test(h)));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.goto(base+'#guide');
  await page.waitForFunction(()=>document.querySelector('.film-archive-disclosure').open);
  assert.equal(await page.locator('.film-archive-links a').count(),5);
  const close=page.locator('.film-archive-disclosure summary');
  await close.click();assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),false);
  await close.focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),true);
  await page.locator('.film-archive-links a').filter({hasText:'ルオスエンを歩く'}).scrollIntoViewIfNeeded();await paint(page);
  const archiveY=await page.evaluate(()=>scrollY);
  await page.locator('.film-archive-links a').filter({hasText:'ルオスエンを歩く'}).click();await ready(page,CITY);
  await page.locator('#reader-bottom [data-return-to-story]').click();await atY(page,archiveY);
  assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),true);
  for (const path of [WORLD,CITY,NEXT,PREP,SHARE]) {
    await page.goto(url(path));await ready(page,path);
    await page.waitForFunction(()=>window.RuosuenScroll&&document.documentElement.classList.contains('scroll-effects'));
    const illustrated=[WORLD,CITY,NEXT].includes(path);
    const target=page.locator(illustrated?'.story-panel':'.reading-section').last();
    await paint(page);
    const property=illustrated?'--art-shift-y':'--reveal-opacity';
    const before=await target.evaluate((e,p)=>e.style.getPropertyValue(p),property);
    await target.evaluate(e=>scrollTo({top:e.getBoundingClientRect().top+scrollY-120,behavior:'instant'}));await paint(page);
    const after=await target.evaluate((e,p)=>e.style.getPropertyValue(p),property);
    assert.notEqual(before,after,'Native scroll must animate '+path);
  }
  console.log(JSON.stringify({width,journey:'PASS',scenes:8,cityPanels:10,history:true,archiveReturn:true}));
}
(async()=>{
  const proxy=process.env.HTTPS_PROXY||process.env.HTTP_PROXY;
  const executablePath=process.env.RUOSUEN_CHROMIUM||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined);
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{}),args:['--no-sandbox','--disable-dev-shm-usage'],...(proxy?{proxy:{server:proxy,bypass:'127.0.0.1,localhost'}}:{})});
  try {
    async function context(options={}) {
      const c=await browser.newContext(options);
      if(process.env.RUOSUEN_FONT_FALLBACK==='1')await c.route('https://fonts.googleapis.com/**',r=>r.fulfill({contentType:'text/css',body:'/* Explicit system-font validation */'}));
      c.on('page',p=>{p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error'&&!m.location().url?.endsWith('/favicon.ico'))errors.push(m.text())})});
      return c;
    }
    for(const width of [1440,390]) {
      const c=await context({viewport:{width,height:900}});const p=await c.newPage();p.setDefaultTimeout(12000);
      await checkJourney(p,width);await c.close();
    }
    const c=await context({viewport:{width:390,height:844},reducedMotion:'reduce'});const p=await c.newPage();
    await p.goto(base,{waitUntil:'networkidle'});assert.equal(await p.locator('.is-scroll-story').count(),0);
    assert.equal(await p.locator('html.scroll-effects').count(),0);
    await p.locator('#next a').click();await ready(p,WORLD);
    await p.locator('#reader-bottom [data-return-to-story]').click();assert(await p.locator('#next').isVisible());
    // Existing public URLs continue to resolve after consolidation.
    for(const [old,path] of [['docs/03_魔石と魔術.md',WORLD],['docs/08_街角の風景.md',CITY],['docs/06_種族と信仰.md',PREP],['players/characters/README.md',SHARE]]) {
      await p.goto(url(old));await ready(p,path);
    }
    const unsafe=await p.evaluate(()=>markdownToHtml('[bad](javascript:alert(1))\n\n![bad](../notes/private.png)','docs/01_プレイヤー向け世界観.md'));
    assert(!unsafe.includes('href=')&&!unsafe.includes('<img'));
    await c.close();
    const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:568}});const q=await nojs.newPage();await q.goto(base,{waitUntil:'domcontentloaded'});
    assert(await q.locator('#opening h1').isVisible());assert((await q.locator('#territory').innerText()).includes('願いが叶う'));
    await nojs.close();
    assert.deepEqual(errors,[],'Unexpected browser errors');
    console.log(JSON.stringify({result:'PASS',fontMode:process.env.RUOSUEN_FONT_FALLBACK==='1'?'system fallback':'external fonts',reducedMotion:true,noJavaScript:true,legacyLinks:true,safeMarkdown:true}));
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
