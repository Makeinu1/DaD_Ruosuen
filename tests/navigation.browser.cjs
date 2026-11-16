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
const OLD_SHARE='players/キャラクター提出テンプレート.md';
const scenes=['opening','vista','trail','cargo','depths','explorers','territory','tavern','next'];
const institutions=['円環商館の酒場','セレド王立地図院','底空船廠','伽藍の塔','聖路教会','深青の石工房'];
const errors=[];
const url=path=>base+'#/'+encodeURIComponent(path);
async function clickVisible(page,link) {
  const box=await link.boundingBox();
  assert(box&&box.y>=0&&box.y+box.height<=900);
  await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
}
async function clickWorld(page) {
  await clickVisible(page,page.getByRole('link',{name:'世界を知る',exact:true}));
}
const paint=page=>page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
async function ready(page,path) {
  await page.waitForFunction(path=>window.RuosuenStory && !restoring && !pendingRoute && document.querySelector('#article-content').dataset.source===path &&
    document.querySelector('#article-content').getAttribute('aria-busy')==='false',path);
  assert.ok(!(await page.locator('#article-content').innerText()).includes('資料を読み込めませんでした'));
}
async function nativeSeek(page,id,fraction=.27) {
  await page.waitForFunction(()=>window.RuosuenStory && !restoring);
  // Wait for actual image decoding before checking a same-scene dissolve.
  // An unchanged active-scene label alone can describe the previous paint.
  const index=scenes.indexOf(id);
  await Promise.all(scenes.slice(index,index+2).map(scene=>page.locator('#'+scene+' img').evaluate(i=>i.decode())));
  await page.evaluate(({id,fraction})=>{
    const sequence=document.querySelector('.film-sequence');
    const frames=[...sequence.querySelectorAll('[data-film-scene]')];
    const travel=parseFloat(sequence.style.getPropertyValue('--film-travel'));
    const step=travel/(frames.length-1+.65);
    scrollTo({top:sequence.getBoundingClientRect().top+scrollY-document.querySelector('.site-header').getBoundingClientRect().height+(frames.findIndex(e=>e.id===id)+fraction)*step,behavior:'instant'});
  },{id,fraction});
  await page.waitForFunction(({id,fraction})=>{
    const sequence=document.querySelector('.film-sequence');
    const frames=[...sequence.querySelectorAll('[data-film-scene]')];
    const index=frames.findIndex(e=>e.id===id);
    return sequence.dataset.activeScene===id && (fraction>0 && index<frames.length-1
      ? Number(frames[index+1].style.opacity)>.01 : Number(frames[index].style.opacity)>.99);
  },{id,fraction});
  await paint(page);
}
async function restored(page,id,y) {
  try { await page.waitForFunction(({id,y})=>!document.querySelector('#home-view').classList.contains('hidden')&&
    document.querySelector('.film-sequence').dataset.activeScene===id&&Math.abs(scrollY-y)<=2,{id,y}); } catch(e) { console.error(await page.evaluate(()=>({y:scrollY,scene:document.querySelector('.film-sequence').dataset.activeScene,snapshot:window.RuosuenStory.capture(),entry:visits.get(activeKey)})));throw e; }
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
  assert.deepEqual(await page.locator('.film-sequence [data-film-scene]').evaluateAll(es=>es.map(e=>e.id)),scenes);
  const artwork=await page.locator('[data-film-scene] img').evaluateAll(es=>es.map(e=>e.getAttribute('src')));
  assert.equal(new Set(artwork).size,9,'Every film scene needs distinct artwork');
  assert.equal(await page.locator('.film-story-hint,.film-scene-steps,.film-story-progress').count(),0);
  assert.equal(await page.locator('.brand-city-name').innerText(),'ルオスエン');
  assert.equal(await page.locator('#opening h1').textContent(),'自由迷宮都市ルオスエン');
  assert.equal(await page.locator('#vista h2').textContent(),'この街の下には、まだ世界がある。');
  assert.equal((await page.evaluate(()=>window.RuosuenStory.capture())).position,0);
  await nativeSeek(page,'opening',.2);
  assert(await page.locator('#vista').evaluate(e=>Number(e.style.opacity)>.1),'The city opening must dissolve into the second artwork');
  await nativeSeek(page,'opening',0);
  assert.equal(await page.locator('.film-artwalk').count(),0);
  assert.equal(await page.locator('.site-header .nav-start').isVisible(),true);
  const distance = await page.locator('.film-sequence').evaluate(e=>parseFloat(e.style.getPropertyValue('--film-travel')));
  const stageHeight = await page.locator('.film-stage').evaluate(e=>e.clientHeight);
  assert(distance/stageHeight>6&&distance/stageHeight<6.5,'Nine scenes use a moderate .74 viewport pace');
  await nativeSeek(page,'vista',.2);
  assert(await page.locator('#trail').evaluate(e=>Number(e.style.opacity)>.1),'A small scroll must visibly start the dissolve');
  const menu=page.locator('.header-menu summary');
  if(await menu.isVisible()) await clickVisible(page,menu);
  await clickWorld(page);await ready(page,WORLD);
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
  assert.equal(await page.locator('#next a').count(),0);
  if(await menu.isVisible()) await clickVisible(page,menu);
  await clickWorld(page);await ready(page,WORLD);
  assert.equal(await page.locator('.story-panel').count(),7);
  assert.equal(await page.locator('.storybook .story-caption').count(),7);
  for(const caption of await page.locator('.storybook .story-caption').all()) {
    assert.equal(await caption.locator('p').count(),2,'World scenes preserve explanatory paragraphs');
    assert.equal(await caption.evaluate(e=>getComputedStyle(e).position),'relative');
  }
  const worldText=await page.locator('#article-content').innerText();
  for(const term of ['マナ','魔石','純度','大転流','願いが叶う'])assert(worldText.includes(term));
  const readingY=await readAt(page);
  assert(readingY>100);
  await page.goBack();await restored(page,'next',movieY);
  await page.goForward();await ready(page,WORLD);await atY(page,readingY);
  await page.locator('#article-content > p:last-child a').scrollIntoViewIfNeeded();await paint(page);
  const departWorldY=await page.evaluate(()=>scrollY);
  await page.locator('#article-content > p:last-child a').click();await ready(page,CITY);
  assert.equal(await page.locator('.story-panel').count(),6);
  assert.deepEqual(await page.locator('#story-chapters a').allTextContents(),institutions);
  for(const caption of await page.locator('.storybook .story-caption').all()) {
    assert.equal(await caption.locator('p').count(),3,'Each institution includes explanation and a character connection');
    assert.equal(await caption.locator('.story-hook').count(),0,'Organization names stay inside explanatory prose');
  }
  assert((await page.locator('#article-content').innerText()).includes('ほんの入口'));

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
  // World and city lead directly to creation; next-session details remain optional.
  for(const [path,following] of [[WORLD,CITY],[CITY,PREP],[NEXT,PREP],[PREP,NEXT]]) {
    await page.goto(url(path));await ready(page,path);
    const onward=page.locator('#reader-bottom .reader-related a').first();
    await onward.scrollIntoViewIfNeeded();await paint(page);
    await clickVisible(page,onward);await ready(page,following);
  }
  await page.goto(url(NEXT));await ready(page,NEXT);
  assert((await page.locator('#article-content').innerText()).includes('準備中'));
  await page.goto(url(PREP));await ready(page,PREP);
  const prep=await page.locator('#article-content').innerText();
  for(const term of ['蘇生','未確定','話し合','アアシマール'])assert(prep.includes(term));
  assert(await page.locator('.table-wrap').count());
  // Curated navigation has four pages and no author-only or archived destinations.
  assert.equal(await page.locator('#journey-nav a').count(),4);
  const hrefs=await page.locator('#journey-nav a').evaluateAll(es=>es.map(e=>decodeURIComponent(e.getAttribute('href'))));
  assert(!hrefs.some(h=>/notes\/|world\/|DECISIONS|提出テンプレート/.test(h)));
  assert.equal(await page.getByRole('link',{name:'キャラクターを共有する',exact:true}).count(),0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.goto(base+'#guide');
  await page.waitForFunction(()=>document.querySelector('.film-archive-disclosure').open);
  assert.equal(await page.locator('.film-archive-links a').count(),4);
  const close=page.locator('.film-archive-disclosure summary');
  await close.click();assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),false);
  await close.focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),true);
  await page.locator('.film-archive-links a').filter({hasText:'ルオスエンを歩く'}).scrollIntoViewIfNeeded();await paint(page);
  const archiveY=await page.evaluate(()=>scrollY);
  await page.locator('.film-archive-links a').filter({hasText:'ルオスエンを歩く'}).click();await ready(page,CITY);
  await page.locator('#reader-bottom [data-return-to-story]').click();await atY(page,archiveY);
  assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),true);
  for (const path of [WORLD,CITY,NEXT,PREP]) {
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
  console.log(JSON.stringify({width,journey:'PASS',scenes:9,cityPanels:6,history:true,archiveReturn:true}));
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
    for(const width of (process.env.RUOSUEN_WIDTHS || '1440,390').split(',').map(Number)) {
      const c=await context({viewport:{width,height:900}});const p=await c.newPage();p.setDefaultTimeout(12000);
      await checkJourney(p,width);await c.close();
    }
    const c=await context({viewport:{width:390,height:844},reducedMotion:'reduce'});const p=await c.newPage();
    await p.goto(base,{waitUntil:'networkidle'});assert.equal(await p.locator('.is-scroll-story').count(),0);
    assert.equal(await p.locator('html.scroll-effects').count(),0);
    await p.locator('#next').scrollIntoViewIfNeeded();await paint(p);
    await clickVisible(p,p.locator('.header-menu summary'));
    await clickWorld(p);await ready(p,WORLD);
    await p.locator('#reader-bottom [data-return-to-story]').click();assert(await p.locator('#next').isVisible());
    // Existing public URLs continue to resolve after consolidation.
    for(const [old,path] of [['docs/03_魔石と魔術.md',WORLD],['docs/08_街角の風景.md',CITY],['docs/06_種族と信仰.md',PREP],['players/characters/README.md',PREP],[OLD_SHARE,PREP]]) {
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
