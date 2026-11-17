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
const FIRST='adventures/最初の冒険.md';
const PREP='players/キャラクター作成ガイド.md';
const OLD_SHARE='players/キャラクター提出テンプレート.md';
const scenes=['opening','vista','trail','cargo','depths','explorers','territory','tavern','next'];
const worldArtwork=Array.from({length:10},(_,index)=>'reuna-turn-'+String(index+1).padStart(2,'0')+'.webp');
const historyChapters=['魔石とは','大転流','大断裂の谷','ルオスエン'];
const historyPhases=['rise','fall','renewal','city'];
const institutions=['モグラの寝床','モグラ商館','王立地図院','竜骨亭','伽藍の塔','摩天楼','星路教会'];
const errors=[];
const url=path=>base+'#/'+encodeURIComponent(path);
async function clickVisible(page,link) {
  const box=await link.boundingBox();
  assert(box&&box.y>=0&&box.y+box.height<=900);
  await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
}
async function returnToStory(page) {
  const menu=page.locator('.header-menu summary');
  if(await menu.isVisible()) await menu.click();
  await page.locator('.top-nav [data-return-to-story]:visible').click();
}
async function clickWorld(page) {
  const links=await page.getByRole('link',{name:'世界を知る',exact:true}).all();
  for (const link of links) {
    const box=await link.boundingBox();
    if (box&&box.y>=0&&box.y+box.height<=900) return clickVisible(page,link);
  }
  throw new Error('No accessible world-history navigation in viewport');
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
  await Promise.all(scenes.slice(index,index+2).map(scene=>page.locator('#'+scene+' img').evaluate(i=>{i.loading='eager';return i.decode();})));
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
async function checkWorldPanels(page) {
  const panels=page.locator('#article-content .story-panel');
  assert.equal(await panels.count(),10);
  const artwork=await panels.locator('img').evaluateAll(images=>
    images.map(image=>new URL(image.src).pathname.split('/').pop()));
  assert.deepEqual(artwork,worldArtwork);
  assert.equal(new Set(artwork).size,10,'Every history scene needs its own painting');
  const chapters=page.locator('#article-content .history-chapter');
  assert.deepEqual(await chapters.evaluateAll(elements=>elements.map(element=>element.dataset.historyPhase)),historyPhases);
  assert.deepEqual(await chapters.locator(':scope > h2').allTextContents(),historyChapters);
  assert.deepEqual(await chapters.evaluateAll(elements=>elements.map(element=>element.querySelectorAll('.story-panel').length)),[3,3,2,2]);
  assert.equal(await page.locator('#story-chapters').count(),0);
  assert(await chapters.evaluateAll(es=>es.every(e=>getComputedStyle(e).backgroundColor==='rgba(0, 0, 0, 0)'&&getComputedStyle(e).backgroundImage==='none')));
  assert.equal(await panels.nth(3).locator('h3').innerText(),'地上の富が、細っていく');
  assert.equal(await panels.nth(6).locator('h3').innerText(),'その谷の底に、世界が開いた');
  assert.equal(await panels.nth(3).evaluate(element=>element.closest('.history-chapter').dataset.historyPhase),'fall');
  assert.equal(await panels.nth(6).evaluate(element=>element.closest('.history-chapter').dataset.historyPhase),'renewal');
  for (const panel of await panels.all()) {
    const image=panel.locator('img');
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(image=>image.decode());
    await paint(page);
    const actual=await panel.evaluate(panel=>{
      const image=panel.querySelector('img');
      const art=panel.querySelector('.story-art');
      const caption=panel.querySelector('.story-caption');
      const filters=[];
      for(let element=image;element;element=element.parentElement) {
        filters.push(getComputedStyle(element).filter);
        if(element.id==='article-content')break;
      }
      return {naturalWidth:image.naturalWidth,naturalHeight:image.naturalHeight,
        width:image.getAttribute('width'),height:image.getAttribute('height'),
        alt:image.alt,filters,captionPosition:getComputedStyle(caption).position,
        followsArtwork:art.nextElementSibling===caption,
        artBottom:art.getBoundingClientRect().bottom,captionTop:caption.getBoundingClientRect().top,
        paragraphCount:caption.querySelectorAll('p').length,headingCount:caption.querySelectorAll('h3').length};
    });
    assert(actual.naturalWidth>0&&actual.naturalHeight>0,'The actual history painting must load');
    assert.equal(Number(actual.width),1672);
    assert.equal(Number(actual.height),941);
    // srcset makes naturalWidth density-corrected, not the encoded width.
    assert(Math.abs(actual.naturalWidth/actual.naturalHeight-1672/941)<.02);
    assert(actual.alt.trim().length>10,'Each painting needs a meaningful description');
    assert(actual.filters.every(filter=>filter==='none'),'World artwork must keep its original colors');
    assert.equal(actual.captionPosition,'relative');
    assert(actual.followsArtwork&&actual.captionTop>=actual.artBottom-1,
      'World explanations must flow below the full painting');
    assert.equal(actual.headingCount,1,'Each scene has one heading within its chapter');
    assert.equal(actual.paragraphCount,2,'World scenes must preserve explanatory paragraphs');
  }
  const causalTerms=[['その力を蓄えた結晶鉱物'],
    ['保管していた魔石','マナを失いやすく','石に蓄えられた力','地表の天然魔石鉱床は枯渇'],
    ['従来のものをはるかに上回る高純度の魔石'],['いまも育ち続けるこの街']];
  for(let index=0;index<causalTerms.length;index++) {
    const text=await chapters.nth(index).innerText();
    for(const term of causalTerms[index])assert(text.includes(term),'History chapter '+historyChapters[index]+' needs '+term);
  }
  const worldText=await page.locator('#article-content').innerText();
  for(const term of ['レウナ','マナ','魔石','大転流','約三十年','大断裂','地下','ルオスエン'])assert(worldText.includes(term));
  assert.equal((worldText.match(/君は、何を求めて、この街へ？/g)||[]).length,1);
  const question=page.locator('#article-content p').filter({hasText:'君は、何を求めて、この街へ？'});
  assert.equal(await question.innerText(),'君は、何を求めて、この街へ？');
  assert(await question.evaluate(element=>{
    const finalScene=[...document.querySelectorAll('#article-content .story-panel')].at(-1);
    return Boolean(finalScene.compareDocumentPosition(element)&Node.DOCUMENT_POSITION_FOLLOWING);
  }),
    'The world story should end by inviting the reader to imagine their character');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));


}
async function checkJourney(page,width) {
  await page.goto(base,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.RuosuenStory&&document.querySelector('.is-scroll-story'));
  assert.deepEqual(await page.locator('[data-film-scene]').evaluateAll(es=>es.map(e=>e.id)),scenes);
  assert.deepEqual(await page.locator('.film-sequence [data-film-scene]').evaluateAll(es=>es.map(e=>e.id)),scenes);
  const artwork=await page.locator('[data-film-scene] img').evaluateAll(es=>es.map(e=>e.getAttribute('src')));
  assert(await page.locator('[data-film-scene] img').evaluateAll(es=>es.every(e=>e.srcset.includes('800w')&&e.srcset.includes('1200w')&&e.sizes==='(max-width: 480px) 400px, 100vw')));
  assert.equal(new Set(artwork).size,9,'Every film scene needs distinct artwork');
  assert.equal(await page.locator('.film-story-hint,.film-scene-steps').count(),0);
  assert.equal(await page.locator('.film-story-progress').count(),1);
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
  await returnToStory(page);
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
  await checkWorldPanels(page);
  const readingY=await readAt(page);
  assert(readingY>100);
  await page.goBack();await restored(page,'next',movieY);
  await page.goForward();await ready(page,WORLD);await atY(page,readingY);
  await page.locator('#reader-bottom .reader-onward-link').scrollIntoViewIfNeeded();await paint(page);
  const departWorldY=await page.evaluate(()=>scrollY);
  await page.locator('#reader-bottom .reader-onward-link').click();await ready(page,CITY);
  assert.equal(await page.locator('.story-panel').count(),11);
  assert.equal(await page.locator('#story-chapters,.walk-organizations').count(),0);
  assert.deepEqual(await page.locator('#article-content .story-panel h2').allTextContents(),[...institutions,'クェンサ ― 我らの青']);
  const divider=page.locator('.walk-chapter-divider');
  assert.equal(await divider.count(),1);
  assert.equal(await divider.locator('h2').innerText(),'この街に生きる人々');
  assert.equal(await divider.locator('img').count(),0);
  assert.equal(await divider.locator('.walk-divider-copy br').count(),2);
  assert(await divider.evaluate(e=>e.previousElementSibling.querySelector('h3').textContent==='見つけて、持ち帰る' && e.nextElementSibling.querySelector('h2').textContent==='モグラの寝床'));
  const quentha=page.locator('.story-panel').filter({has:page.locator('h2',{hasText:'クェンサ ― 我らの青'})});
  assert.equal(await quentha.count(),1);
  assert.equal(await quentha.locator('img').count(),1);
  assert.equal(await quentha.locator('img').evaluate(img=>new URL(img.src).pathname.split('/').pop()),'ruosuen-walk-quentha-20261117.webp');
  assert((await quentha.innerText()).includes('大断裂で森ごと地下へ沈んだエルフたち'));
  assert((await page.locator('#article-content').innerText()).includes('クェンサもまた、ルオスエンに生きる人々だ。'));
  for(const [index,caption] of (await page.locator('.storybook .story-caption').all()).entries()) {
    assert.equal(await caption.locator('p').count(),index<3?2:3,'Labyrinth scenes have two paragraphs; all city scenes have three');
    assert.equal(await caption.locator('.story-hook').count(),0,'Place names remain in explanatory prose');
  }
  assert((await page.locator('#article-content').innerText()).includes('ほんの入口'));

  for (const image of await page.locator('.story-panel img').all()) {
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(i=>i.decode());
    assert(await image.evaluate(i=>i.naturalWidth>0));
  }
  const tower=page.locator('.story-panel').filter({has:page.locator('h2',{hasText:'伽藍の塔'})});
  await tower.scrollIntoViewIfNeeded();
  assert(await tower.isVisible());
  await paint(page);
  const cityY=await page.evaluate(()=>scrollY);
  assert(cityY>1000);
  await page.goBack();await ready(page,WORLD);await atY(page,departWorldY);
  await page.goForward();await ready(page,CITY);await atY(page,cityY);
  await returnToStory(page);await restored(page,'next',movieY);
  // First-time reader journey: city → possible adventures → first adventure → character, then optional history.
  for(const [path,following] of [[WORLD,CITY],[CITY,NEXT],[NEXT,FIRST],[FIRST,PREP],[PREP,WORLD]]) {
    await page.goto(url(path));await ready(page,path);
    const onward=page.locator('#reader-bottom .reader-onward-link');
    assert.equal(await page.locator('#reader-bottom a').count(),1);
    await onward.scrollIntoViewIfNeeded();await paint(page);
    await clickVisible(page,onward);await ready(page,following);
  }
  await page.goto(url(NEXT));await ready(page,NEXT);
  assert(!(await page.locator('#article-content').innerText()).includes('ある年の瀬、ルオスエンにて'));
  assert.equal(await page.locator('#reader-bottom .reader-onward-link').count(),1);
  await page.goto(url(FIRST));await ready(page,FIRST);
  const firstArt=page.locator('#article-content img');
  assert.equal(await firstArt.count(),1);
  await firstArt.evaluate(img=>img.decode());
  assert(await firstArt.evaluate(img=>img.naturalWidth>0 && img.getAttribute('width')==='1672' &&
    img.getAttribute('height')==='941' && img.srcset.includes('800w') && img.srcset.includes('1200w')));
  const prologue=await page.locator('#article-content').innerText();
  assert(prologue.includes('ある年の瀬、ルオスエンにて')&&prologue.includes('一年かけて貯めた金で買った乗船券')&&prologue.includes('君たちの物語は、この街の年の瀬から始まる。'));
  assert.equal(await page.locator('#reader-bottom .reader-onward-link').count(),1);
  await page.goto(url(PREP));await ready(page,PREP);
  const prep=await page.locator('#article-content').innerText();
  for(const term of ['地下の世界からやって来た','ゲーム上の作成条件','キャラクターを作成する'])assert(prep.includes(term));
  assert(!prep.includes('死者の蘇生'));
  assert(prep.includes('大きな夢を抱いている者。\n故郷を離れ、新しい暮らしを求める者。\nまだ誰も知らない世界からやって来た者。'));
  assert(prep.includes('大切な人はいるだろうか。\n忘れられない出来事はあるだろうか。'));
  // Only the header provides global navigation. The mobile menu does not
  // repeat the always-visible character creation action.
  assert.equal(await page.locator('#journey-nav,.reader-breadcrumbs,.reader-toc,#sidebar').count(),0);
  const menuSummary=page.locator('.header-menu summary');
  const mobile=await menuSummary.isVisible();
  if(mobile) await menuSummary.click();
  const navLinks=page.locator('.top-nav a[href^="#/"]:not([data-return-to-story]):visible');
  const hrefs=await navLinks.evaluateAll(es=>es.map(e=>decodeURIComponent(e.getAttribute('href'))).sort());
  assert.deepEqual(hrefs,[CITY,NEXT,FIRST,PREP,WORLD].map(p=>'#/'+p).sort());
  assert.equal(await page.locator('.top-nav a[aria-current="page"]:visible').count(),1);
  if(mobile) await menuSummary.click();
  assert.equal(await page.locator('#reader-bottom a').count(),1);
  assert.equal(await page.getByRole('link',{name:'キャラクターを共有する',exact:true}).count(),0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.goto(base+'#guide');
  await page.waitForFunction(()=>document.querySelector('.film-archive-disclosure').open);
  assert.equal(await page.locator('.film-archive-links a').count(),5);
  assert.equal(await page.locator('h2.film-title .film-phrase').count(), 32);
  assert.equal(await page.locator('.header-desktop-link').filter({hasText:'この街で冒険する'}).count(),1);
  const close=page.locator('.film-archive-disclosure summary');
  await close.click();assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),false);
  await close.focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),true);
  await page.locator('.film-archive-links a').filter({hasText:'ルオスエンを歩く'}).scrollIntoViewIfNeeded();await paint(page);
  const archiveY=await page.evaluate(()=>scrollY);
  await page.locator('.film-archive-links a').filter({hasText:'ルオスエンを歩く'}).click();await ready(page,CITY);
  await returnToStory(page);await atY(page,archiveY);
  assert.equal(await page.locator('.film-archive-disclosure').evaluate(e=>e.open),true);
  for (const path of [WORLD,CITY,NEXT,FIRST,PREP]) {
    await page.goto(url(path));await ready(page,path);
    await page.waitForFunction(()=>window.RuosuenScroll&&document.documentElement.classList.contains('scroll-effects'));
    const illustrated=[WORLD,CITY,NEXT].includes(path);
    // FIRST has a single section beginning above the fold, so its reveal
    // is already complete on desktop. The below-fold onward nav is the
    // meaningful scroll target on that page.
    const target=page.locator(illustrated?'.story-panel':path===FIRST?'#reader-bottom':'.reading-section').last();
    await paint(page);
    const property=illustrated?'--art-shift-y':'--reveal-opacity';
    const before=await target.evaluate((e,p)=>e.style.getPropertyValue(p),property);
    await target.evaluate(e=>scrollTo({top:e.getBoundingClientRect().top+scrollY-120,behavior:'instant'}));await paint(page);
    const after=await target.evaluate((e,p)=>e.style.getPropertyValue(p),property);
    assert.notEqual(before,after,'Native scroll must animate '+path);
  }
  console.log(JSON.stringify({width,journey:'PASS',scenes:9,worldPanels:10,historyChapters:4,chapterNavigationRemoved:true,cityPanels:11,history:true,archiveReturn:true}));
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
    await returnToStory(p);assert(await p.locator('#next').isVisible());
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
