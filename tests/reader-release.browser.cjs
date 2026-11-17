const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.RUOSUEN_BASE_URL || 'http://127.0.0.1:8819/';
const city = 'docs/04_自由迷宮都市と組織.md';
const version = JSON.parse(fs.readFileSync(path.join(__dirname,'../assets/reader-release.json'),'utf8')).version;
const route = '#/'+encodeURIComponent(city);
async function check(page) {
  await page.waitForFunction(p=>{const e=document.querySelector('#article-content');return e?.dataset.source===p && e.getAttribute('aria-busy')==='false';},city);
  const dividers=page.locator('.walk-chapter-divider');
  assert.deepEqual(await dividers.locator('h2').allTextContents(),['街の下へ','この街に生きる人々','まだ、この街のほんの入口だ。']);
  assert.deepEqual(await dividers.locator('h2').evaluateAll(es=>es.map(e=>e.id)),['section-0','walk-people','walk-beyond']);
  assert.equal(await dividers.locator('.walk-divider-copy br').count(),6);
  assert.equal(await page.locator('.story-panel').count(),11);
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
      for(const width of [320,390,1440]){
        const context=await browser.newContext({viewport:{width,height:844},deviceScaleFactor:width<500?3:1});
        await context.route('https://fonts.googleapis.com/**',r=>r.fulfill({contentType:'text/css',body:'/* fallback font */'}));
        const page=await context.newPage();
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto(base+route,{waitUntil:'domcontentloaded'});
        await check(page);
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
      console.log(name+': chapter doors, stale shell and stale source PASS');
    }finally{await browser.close();}
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
