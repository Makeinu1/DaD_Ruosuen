const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.RUOSUEN_BASE_URL || 'http://127.0.0.1:8819/';
const city = 'docs/04_自由迷宮都市と組織.md';
const version = JSON.parse(fs.readFileSync(path.join(__dirname,'../assets/reader-release.json'),'utf8')).version;
const route = '#/'+encodeURIComponent(city);
const chapterTitles = {
  "docs/04_自由迷宮都市と組織.md": [
    "街の下へ",
    "この街に生きる人々",
    "まだ、この街のほんの入口だ。"
  ],
  "adventures/次の冒険.md": [
    "冒険者という生き方",
    "例えば、こんな冒険",
    "冒険のある暮らし",
    "君たちの物語"
  ],
  "adventures/最初の冒険.md": [
    "第一話　ある年の瀬、ルオスエンにて",
    "君たちの物語は、この街の年の瀬から始まる。"
  ],
  "players/キャラクター作成ガイド.md": [
    "君の想像する世界",
    "この街で何を求めるのか",
    "仲間と冒険へ",
    "君は、この世界で何者になるだろう。"
  ],
  "docs/01_プレイヤー向け世界観.md": [
    "魔石とは",
    "大転流",
    "大断裂の谷",
    "ルオスエン",
    "君は、何を求めて、この街へ？"
  ]
};
async function check(page, article=city) {
  await page.waitForFunction(p=>{const e=document.querySelector('#article-content');return e?.dataset.source===p && e.getAttribute('aria-busy')==='false';},article);
  const dividers=page.locator('.chapter-divider');
  assert.deepEqual(await dividers.locator('h2').allTextContents(),chapterTitles[article]);
  assert.equal(await dividers.locator('.walk-divider-kicker').count(),chapterTitles[article].length);
  if(article===city) {
    assert.deepEqual(await dividers.locator('h2').evaluateAll(es=>es.map(e=>e.id)),['section-0','walk-people','walk-beyond']);
    assert.equal(await dividers.locator('.walk-divider-copy br').count(),6);
    assert.equal(await page.locator('.story-panel').count(),11);
    const panels=page.locator('.storybook-walk .story-panel');
    assert.deepEqual(await panels.evaluateAll(es=>es.map(e=>e.classList.contains('panel-medium')?'medium':e.classList.contains('panel-small')?'small':e.classList.contains('panel-pair')?'pair':'wide')),
      ['wide','wide','medium','medium','medium','medium','wide','wide','small','medium','medium']);
    assert.equal(await page.locator('.storybook-walk .story-pair').count(),0);
    assert(await panels.evaluateAll(es=>es.every(e=>{
      const r=e.getBoundingClientRect(), img=e.querySelector('img'), a=e.querySelector('.story-art').getBoundingClientRect(), c=e.querySelector('.story-caption').getBoundingClientRect();
      if(r.left<-1||r.right>innerWidth+1||a.left<-1||a.right>innerWidth+1||c.left<-1||c.right>innerWidth+1)return false;
      if(e.classList.contains('panel-small')){
        return getComputedStyle(img).transform==='none' &&
          Math.abs(img.clientHeight/img.clientWidth-941/836)<.02 &&
          (innerWidth>1100?getComputedStyle(e).display==='grid'&&a.right<=c.left+1:getComputedStyle(e).display==='block'&&c.top>=a.bottom-1);
      }
      return c.top>=a.bottom-1;
    })), 'city walk artwork/caption layout');

  }
  if(article.startsWith('docs/01')) {
    assert.equal(await page.locator('.history-chapter').count(),4);
    assert.equal(await page.locator('.story-panel').count(),10);
    assert.deepEqual(await page.locator('.history-chapter').evaluateAll(es=>es.map(e=>e.querySelectorAll('.story-panel').length)),[3,3,2,2]);
  }
  if(article==="adventures/最初の冒険.md") {
    assert(await page.locator('.prologue').evaluate(e=>e.firstElementChild.matches('figure.article-map')));
    assert.equal(await page.locator('#article-content img').count(),1);
  }
  if(article==="adventures/次の冒険.md") assert.equal(await page.locator('.story-panel').count(),1);
  if(article==="players/キャラクター作成ガイド.md") {
    const text = await page.locator('#article-content').innerText();
    for(const term of ['D&D 2024年版','Lv2','追加資料も原則OK','早めにDMへ資料を共有','世界設定をすべて読んでおく必要はありません','誰も知らない地下世界の出身者','この街に新しい組織を作り','別の三人の冒険者と旅をする']) assert(text.includes(term),term);
    assert(!text.includes('空に憧れるファイター'));
    assert.equal(await page.locator('#article-content a[href^="https://"]').count(),2);
  }
  assert.equal(await page.locator('#reader-bottom a').count(),1);
  assert(await dividers.evaluateAll(es=>es.every(e=>{
    const r=e.getBoundingClientRect(), css=getComputedStyle(e), before=getComputedStyle(e,'::before'), after=getComputedStyle(e,'::after');
    return css.display==='flex' && parseFloat(css.borderTopWidth)>0 && parseFloat(css.borderBottomWidth)>0 && before.content!=='none' && after.content!=='none' && r.left>=-1 && r.right<=innerWidth+1;
  })));
}
(async()=>{
  for(const [name,type] of [['chromium',chromium],['webkit',webkit]]){
    const browser=await type.launch({headless:true});
    try{
      for(const width of [320,390,768,1024,1440]){
        const context=await browser.newContext({viewport:{width,height:844},deviceScaleFactor:width<500?3:1});
        await context.route('https://fonts.googleapis.com/**',r=>r.fulfill({contentType:'text/css',body:'/* fallback font */'}));
        const page=await context.newPage();
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        for(const article of Object.keys(chapterTitles)){
          await page.goto(base+'#/'+encodeURIComponent(article),{waitUntil:'domcontentloaded'});
          await check(page,article);
        }
        assert.deepEqual(errors,[]);
        await context.close();
      }
      // Simulate a stale shell on an initial request, then let the replacement
      // navigation load the actual current release while retaining the hash.
      const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:3});
      await context.route('https://fonts.googleapis.com/**',r=>r.fulfill({contentType:'text/css',body:''}));
      let oldShell=0, staleDoc=0;
      await context.route('**/*',async r=>{
        const u=new URL(r.request().url());
        if(r.request().resourceType()==='document' && u.origin===new URL(base).origin && !u.searchParams.has('v')){
          oldShell++;
          const response=await r.fetch();
          await r.fulfill({response,body:(await response.text()).replace('name="ruosuen-release" content="'+version+'"','name="ruosuen-release" content="0000000000000000"')});
        }else if(decodeURIComponent(u.pathname).endsWith(city) && !u.searchParams.has('retry')){
          staleDoc++;
          const response=await r.fetch();
          await r.fulfill({response,body:'# stale content'});
        }else await r.fallback();
      });
      const page=await context.newPage();
      await page.goto(base+route,{waitUntil:'domcontentloaded'});
      await page.waitForURL(u=>u.searchParams.get('v')===version);
      await check(page);
      assert.equal(oldShell,1);assert.equal(staleDoc,1);
      assert.equal(decodeURIComponent(new URL(page.url()).hash.slice(2)),city);
      await context.close();
      console.log(name+': all five articles, chapter doors, stale shell and stale source PASS');
    }finally{await browser.close();}
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
