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
      await p.waitForLoadState('networkidle');
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
      if(width<=430)assert(film.initialSrc.includes('responsive/'),JSON.stringify({name,width,film}));
      const initialTransfer=await p.evaluate(()=>{
        const entries=performance.getEntriesByType('resource').filter(e=>/\.webp(?:\?|$)/.test(e.name));
        return {images:entries.length,encodedBytes:entries.reduce((n,e)=>n+(e.encodedBodySize||0),0),transferredBytes:entries.reduce((n,e)=>n+(e.transferSize||0),0)};
      });
      for(const path of paths) {
        await p.goto(base+'#/'+encodeURIComponent(path));
        await docsReady(p,path);
        assert.equal(await p.locator('#journey-nav,.reader-breadcrumbs,.reader-toc,#sidebar,#story-chapters,.walk-organizations').count(),0);
        const design=await p.evaluate(()=>{
          const reader=document.querySelector('#reader-view'),hero=document.querySelector('.article-hero');
          const title=hero.querySelector('h1'), r=title.getBoundingClientRect();
          const font=e=>parseFloat(getComputedStyle(e).fontSize);
          const text=[...document.querySelectorAll('#article-content p,#article-content li')].filter(e=>!e.matches('.walk-divider-kicker,.history-era') && e.getClientRects().length);
          return {background:getComputedStyle(reader).backgroundColor,gradient:getComputedStyle(reader).backgroundImage,
            border:getComputedStyle(hero).borderBottomWidth,headingFont:font(title),titleLeft:r.left,
            titleTop:r.top,minimumBody:Math.min(...text.map(font)),
            labelFont:font(hero.querySelector('.article-label')),summaryFont:font(hero.querySelector('.article-summary')),
            captions:document.querySelectorAll('#article-content figure figcaption').length};
        });
        assert(design.background==='rgb(3, 8, 16)'&&design.gradient==='none'&&design.border==='0px'&&design.minimumBody>=16&&design.labelFont>=14&&design.summaryFont>=16&&design.captions===0,JSON.stringify({name,width,path,design}));
        if(path===paths[0]) globalThis.baseline=design;
        else assert(Math.abs(design.headingFont-globalThis.baseline.headingFont)<.1&&Math.abs(design.titleLeft-globalThis.baseline.titleLeft)<1&&Math.abs(design.titleTop-globalThis.baseline.titleTop)<2,JSON.stringify({name,width,path,design,baseline:globalThis.baseline}));
        if(path===paths[2])assert(await p.locator('.prologue').evaluate(e=>e.firstElementChild.matches('figure.article-map')&&e.firstElementChild.nextElementSibling.querySelector('h2').textContent.includes('ある年の瀬')));
        if(path===paths[4])assert(await p.locator('.history-chapter').evaluateAll(es=>es.length===4&&es.every(e=>getComputedStyle(e).backgroundImage==='none'&&getComputedStyle(e).backgroundColor==='rgba(0, 0, 0, 0)')));

        assert.equal(await p.locator('#reader-bottom a').count(),1);
        const menu=p.locator('.header-menu summary');
        const mobile=await menu.isVisible();
        if(mobile) await menu.click();
        const nav=await p.locator('.top-nav').evaluate(e=>{
          const links=[...e.querySelectorAll('a[href^="#/"]:not([data-return-to-story])')].filter(a=>a.getClientRects().length && getComputedStyle(a).visibility!=='hidden' && (!a.closest('details') || a.closest('details').open));
          return {minimumFont:Math.min(...links.map(a=>parseFloat(getComputedStyle(a).fontSize))),count:links.length,active:links.filter(a=>a.getAttribute('aria-current')==='page').length,unique:new Set(links.map(a=>a.getAttribute('href'))).size,bodyWidth:document.documentElement.scrollWidth};
        });
        assert(nav.minimumFont>=14&&nav.count===5&&nav.unique===5&&nav.active===1&&nav.bodyWidth<=width+1,JSON.stringify({name,width,path,nav}));
        if(mobile) await menu.click();
        if(path===paths[0]){
          const dividers=p.locator('.walk-chapter-divider');
          assert.equal(await dividers.count(),3);
          assert.deepEqual(await dividers.locator('h2').allTextContents(),['街の下へ','この街に生きる人々','まだ、この街のほんの入口だ。']);
          for(const chapter of await dividers.all()){
            assert.equal(await chapter.locator('.walk-divider-copy br').count(),2);
            assert(await chapter.evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1;}));
          }
          const divider=dividers.nth(1);
          assert.equal(await divider.locator('h2').innerText(),'この街に生きる人々');
          assert.equal(await divider.locator('.walk-divider-copy br').count(),2);
          const dividerStyle=await divider.evaluate(e=>{
            const style=getComputedStyle(e), r=e.getBoundingClientRect();
            return {width:r.width,viewport:innerWidth,padding:parseFloat(style.paddingTop),
              previous:e.previousElementSibling.matches('.story-panel'),next:e.nextElementSibling.querySelector('h2')?.textContent};
          });
          assert(dividerStyle.width<=dividerStyle.viewport&&dividerStyle.padding>=64&&dividerStyle.previous&&dividerStyle.next==='モグラの寝床',JSON.stringify({name,width,dividerStyle}));
          assert.equal(await p.locator('#article-content .story-panel').count(),11);
          const q=p.locator('.story-panel').filter({has:p.locator('h2',{hasText:'クェンサ'})});
          assert.equal(await q.count(),1);
          assert.equal(await q.locator('img').count(),1);
          assert.equal(await q.locator('.story-caption p').count(),3);
          assert((await q.innerText()).includes('大断裂で森ごと地下へ沈んだエルフたち'));
          assert((await q.innerText()).includes('この街の顔役の一人に数えられている'));

        }
        const imgs=p.locator('#article-content img');
        if(await imgs.count()) {
          const first=imgs.first();
          await first.evaluate(i=>i.decode());
          assert(await first.evaluate(i=>i.naturalWidth>0&&i.srcset.includes('800w')&&(i.closest('.portrait-art')?i.srcset.includes('1024w')&&!i.srcset.includes('1200w')&&i.clientWidth<=700&&Math.abs(i.clientHeight/i.clientWidth-1.5)<.02&&getComputedStyle(i).transform==='none':i.srcset.includes('1200w'))));
        }
        if(path.startsWith('players/'))assert((await p.locator('#article-content').innerText()).includes('世界設定をすべて読んでおく必要はありません'));
      }
      assert.deepEqual(errors,[]);
      console.log(JSON.stringify({browser:name,width,dpr:width<=430?3:1,initialSrc:film.initialSrc,initialTransfer,phraseCount:film.phraseCount,nav:5,result:'PASS'}));
      await context.close();
    }
  } finally {await browser.close();}
}
})().catch(e=>{console.error(e);process.exitCode=1});
