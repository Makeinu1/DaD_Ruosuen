const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const base='http://127.0.0.1:8819/';
const paths=['docs/04_自由迷宮都市と組織.md','adventures/次の冒険.md','adventures/最初の冒険.md','players/キャラクター作成ガイド.md','docs/01_プレイヤー向け世界観.md'];
async function docsReady(page,path) {
  await page.waitForFunction(p=>document.querySelector('#article-content').dataset.source===p &&
    document.querySelector('#article-content').getAttribute('aria-busy')==='false',path);
}
(async()=>{
for (const [name,type] of [['chromium',chromium],['webkit',webkit]]) {
  const browser=await type.launch({headless:true});
  try {
    for (const width of [320,375,390,430,901,1440]) {
      const context=await browser.newContext({viewport:{width,height:width===320?568:844},deviceScaleFactor:width<=430?3:1});
      await context.route('https://fonts.googleapis.com/**',route=>route.fulfill({contentType:'text/css',body:'/* system font baseline */'}));
      const p=await context.newPage();
      const errors=[];
      p.on('pageerror',e=>errors.push(e.message));
      await p.goto(base,{waitUntil:'domcontentloaded'});
      await p.waitForFunction(()=>window.RuosuenStory);
      await p.evaluate(()=>document.fonts.ready);
      await p.locator('#opening img').evaluate(img=>img.decode());
      const film=await p.evaluate(()=>{
        const titleSpans=[...document.querySelectorAll('h2.film-title .film-phrase')];
        const phraseFailures=titleSpans.filter(e=>{
          const r=e.getBoundingClientRect(),parent=e.parentElement.getBoundingClientRect();
          return getComputedStyle(e).whiteSpace!=='nowrap' || r.width>parent.width+1 || r.left<-1 || r.right>innerWidth+1;
        }).map(e=>e.textContent);
        const header=document.querySelector('.header-inner').getBoundingClientRect();
        const nav=document.querySelector('.top-nav').getBoundingClientRect();
        return {phraseCount:titleSpans.length,phraseFailures,bodyWidth:document.documentElement.scrollWidth,headerOverflow:nav.right>header.right+1,
        initialSrc:document.querySelector('#opening img').currentSrc,allSrcset:[...document.querySelectorAll('img.film-image')].every(i=>i.srcset.includes('800w')&&i.srcset.includes('1200w'))};
      });
      assert.equal(film.phraseCount,32);
      assert.deepEqual(film.phraseFailures,[],JSON.stringify({name,width,film}));
      assert(film.bodyWidth<=width+1 && !film.headerOverflow && film.allSrcset,JSON.stringify({name,width,film}));
      for(const path of paths) {
        await p.goto(base+'#/'+encodeURIComponent(path));
        await docsReady(p,path);
        const nav=await p.locator('#journey-nav').evaluate(e=>{
          const links=[...e.querySelectorAll('a')],a=e.querySelector('[aria-current="page"]'),box=e.getBoundingClientRect(),r=a.getBoundingClientRect();
          return {count:links.length,rows:new Set(links.map(x=>Math.round(x.getBoundingClientRect().top))).size,activeVisible:r.left>=box.left-1&&r.right<=box.right+1,bodyWidth:document.documentElement.scrollWidth,wrap:getComputedStyle(e).flexWrap};
        });
        assert.equal(nav.count,5);
        assert(nav.bodyWidth<=width+1,JSON.stringify({name,width,path,nav}));
        if(width<=430)assert(nav.rows===1&&nav.activeVisible&&nav.wrap==='nowrap',JSON.stringify({name,width,path,nav}));
        const imgs=p.locator('#article-content img');
        if(await imgs.count()) {
          const first=imgs.first();
          await first.evaluate(i=>i.decode());
          assert(await first.evaluate(i=>i.naturalWidth>0&&i.srcset.includes('800w')&&i.srcset.includes('1200w')));
        }
        if(path.startsWith('players/'))assert((await p.locator('#article-content').innerText()).includes('大きな夢を抱いている者。\n故郷を離れ、新しい暮らしを求める者。\nまだ誰も知らない世界からやって来た者。'));
      }
      assert.deepEqual(errors,[]);
      console.log(JSON.stringify({browser:name,width,dpr:width<=430?3:1,initialSrc:film.initialSrc,phraseCount:film.phraseCount,nav:5,result:'PASS'}));
      await context.close();
    }
  } finally {await browser.close();}
}
})().catch(e=>{console.error(e);process.exitCode=1});
