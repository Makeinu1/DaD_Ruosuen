/* Run with Playwright available and a local static server on port 8819.
 * RUOSUEN_BASE_URL can target the published Pages site for the same checks.
 */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const base = process.env.RUOSUEN_BASE_URL || 'http://127.0.0.1:8819/';
const depthsPath = 'docs/02_迷宮と探索.md';
const errors = [];

function watchErrors(page) {
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error' && !message.location().url?.endsWith('/favicon.ico')) {
      errors.push(message.text());
    }
  });
}

async function paint(page) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function openMovie(page) {
  await page.goto(base, {waitUntil:'networkidle'});
  await page.waitForFunction(() => window.RuosuenStory && document.querySelector('.is-scroll-story'));
  await page.evaluate(() => document.fonts.ready);
  await paint(page);
}

async function seekByScrolling(page, sceneId, fraction=0.27) {
  // Geometry is the only connection to the controller: this deliberately
  // scrolls the document without using goTo(), setting a hash, or its state.
  await page.evaluate(({sceneId, fraction}) => {
    const sequence = document.querySelector('.film-sequence');
    const frames = [...sequence.querySelectorAll('[data-film-scene]')];
    const index = frames.findIndex(frame => frame.id === sceneId);
    if (index < 0) throw new Error('Unknown scene: '+sceneId);
    const paces = frames.map(frame => Number(frame.dataset.filmPace) || 1);
    const prefix = paces.slice(0,index).reduce((sum,pace) => sum+pace,0);
    const total = paces.slice(0,-1).reduce((sum,pace) => sum+pace,0)+0.65;
    const step = parseFloat(sequence.style.getPropertyValue('--film-travel')) / total;
    const start = sequence.getBoundingClientRect().top + scrollY;
    const local = index === frames.length-1 ? Math.min(fraction,0.65) : fraction*paces[index];
    scrollTo({top:start + (prefix+local)*step, behavior:'instant'});
  }, {sceneId,fraction});
  await paint(page);
}

async function waitForScene(page, sceneId) {
  await page.waitForFunction(sceneId =>
    document.querySelector('.film-sequence').dataset.activeScene === sceneId,
  sceneId, {timeout:7000});
}

async function waitForMoviePosition(page, scene, expectedY) {
  await page.waitForFunction(({scene, expectedY}) => {
    const home = document.getElementById('home-view');
    return !home.classList.contains('hidden') &&
      document.querySelector('.film-sequence').dataset.activeScene === scene &&
      Math.abs(scrollY - expectedY) <= 2;
  }, {scene, expectedY}, {timeout:7000});
}

async function articleReady(page, expectedPath) {
  await page.waitForFunction(expectedPath => {
    const reader = document.getElementById('reader-view');
    const content = document.getElementById('article-content');
    const currentPath = decodeURIComponent(location.hash.replace(/^#\/?/,''));
    return !reader.classList.contains('hidden') && currentPath === expectedPath &&
      content.getAttribute('aria-busy') === 'false' &&
      !content.querySelector('.loading') && content.textContent.trim().length > 80;
  }, expectedPath, {timeout:10000});
  assert.ok(!(await page.locator('#article-content').innerText()).includes('資料を読み込めませんでした'));
  await page.locator('#article-content img').evaluateAll(images =>
    Promise.all(images.map(image => image.decode().catch(() => undefined))));
}

async function readPartway(page, preferredY=420) {
  const y = await page.evaluate(preferredY => {
    const available = document.documentElement.scrollHeight - innerHeight;
    const destination = Math.min(preferredY, Math.max(0, available - 40));
    scrollTo({top:destination, behavior:'instant'});
    return scrollY;
  }, preferredY);
  assert.ok(y > 100, 'Article must actually be scrolled for a meaningful history check');
  await paint(page);
  return y;
}

async function waitForReadingPosition(page, expectedY) {
  await page.waitForFunction(expectedY => Math.abs(scrollY - expectedY) <= 2,
    expectedY, {timeout:7000});
}

async function checkHookScenes(page,width) {
  await openMovie(page);
  const scenes = page.locator('.film-sequence [data-film-scene]');
  const ids = await scenes.evaluateAll(elements => elements.map(element => element.id));
  assert.equal(ids.length,12);
  const hooks = [
    ['manastone','魔石が、暮らしを灯す。','使えば減る、魔法の燃料。地下の魔石が、街の灯りになる。'],
    ['territory','領域主の縄張りへ。','そこに生きるものを、君たちはまだ知らない。'],
    ['explorers','発見を、この街へ。','商館で仕事を。市場で商いを。酒場では、帰還の祝いを。'],
    ['map','地図が、宝になる。','君たちの足跡が、次の誰かの道になる。']
  ];
  const shortIds = ['domains',...hooks.map(([id]) => id)];
  assert.deepEqual(ids.slice(ids.indexOf('domains'),ids.indexOf('domains')+5),shortIds);
  assert.equal(await page.locator('#domains h2').count(),1);
  assert.equal((await page.locator('#domains h2').textContent()).replace(/\s+/g,''),
    'その先で、何を見つけるだろう。');
  for (const [id,heading,description] of hooks) {
    const frame = page.locator('#'+id);
    assert.equal(await frame.locator('h2').count(),1);
    assert.equal((await frame.locator('h2').textContent()).replace(/\s+/g,''),heading);
    assert.equal(await frame.locator('p').count(),1);
    assert.equal((await frame.locator('p').textContent()).replace(/\s+/g,''),description);
    const occurrences = await page.locator('.film-stage').evaluate((stage,{heading,description}) => {
      const equals = (element,text) => element.textContent.replace(/\s+/g,'') === text;
      return {
        heading:[...stage.querySelectorAll('h1,h2')].filter(element => equals(element,heading)).length,
        description:[...stage.querySelectorAll('p')].filter(element => equals(element,description)).length
      };
    },{heading,description});
    assert.deepEqual(occurrences,{heading:1,description:1});
  }
  const hookCopy = await page.locator(shortIds.map(id => '#'+id).join(',')).allTextContents();
  assert.ok(!hookCopy.join('').includes('百万年'));
  assert.ok(!hookCopy.join('').includes('五大国'));

  // A half-length hook must use half the scroll distance, rather than only
  // showing a shorter block of text inside an unchanged reading interval.
  const positions = {};
  for (const id of ['opening','overture',...shortIds,'next']) {
    assert.equal(await page.evaluate(id => window.RuosuenStory.goTo(id),id),true);
    await waitForScene(page,id);
    positions[id] = await page.evaluate(() => scrollY);
  }
  const normalDistance = positions.overture-positions.opening;
  assert.ok(normalDistance >= 480);
  for (let index=0; index<shortIds.length; index++) {
    const id = shortIds[index];
    const nextId = shortIds[index+1] || 'next';
    const ratio = id === 'domains' ? 0.35 : 0.5;
    assert.ok(Math.abs((positions[nextId]-positions[id])-normalDistance*ratio) <= 2,
      id+' should occupy '+ratio+' of a normal scene scroll distance');

    await seekByScrolling(page,id,0.2);
    await waitForScene(page,id);
    assert.ok(await page.locator('#'+id+' h2').isVisible());
    const sceneIndex = ids.indexOf(id);
    assert.equal(await page.locator('#film-prev').getAttribute('href'),'#'+ids[sceneIndex-1]);
    assert.equal(await page.locator('#film-next').getAttribute('href'),'#'+ids[sceneIndex+1]);
    await page.locator('#film-next').click();
    await waitForScene(page,ids[sceneIndex+1]);
    await page.locator('#film-prev').click();
    await waitForScene(page,id);
  }
  for (const [id] of hooks) {
    await page.goto(base+'#'+id);
    await waitForScene(page,id);
    assert.ok(await page.locator('#'+id+' h2').isVisible());
  }
  for (const [scene,path] of [
    ['manastone','docs/03_魔石と魔術.md'],
    ['explorers','docs/04_自由迷宮都市と組織.md']
  ]) {
    await page.goto(base+'#'+scene);
    await waitForScene(page,scene);
    const departureY = await page.evaluate(() => scrollY);
    await page.locator('#'+scene+' a[href^="#/"]').click();
    await articleReady(page,path);
    await page.locator('#reader-bottom [data-return-to-story]').click();
    await waitForMoviePosition(page,scene,departureY);
  }
  console.log(JSON.stringify({check:'individual hooks and weighted scroll',width,scenes:12,
    normalDistance,shortScenes:shortIds,deepLinks:hooks.map(([id]) => id)}));
}

async function checkReadingHistory(page, width) {
  // The first visit has no scene hash. This catches restoring the opening
  // instead of the actual movie position reached by ordinary scrolling.
  await openMovie(page);
  assert.equal(await page.evaluate(() => location.hash), '');
  const headerCreation = page.locator('.site-header a').filter({hasText:/冒険者になる|キャラクターをつくる/});
  for (const link of await headerCreation.all()) assert.equal(await link.isVisible(), false);

  await seekByScrolling(page, 'depths');
  await page.waitForFunction(() => document.querySelector('.film-sequence').dataset.activeScene === 'depths');
  const movieY = await page.evaluate(() => scrollY);
  await page.locator('#depths a').filter({hasText:/迷宮/}).click();
  await articleReady(page, depthsPath);
  const readingY = await readPartway(page);

  await page.goBack();
  await waitForMoviePosition(page, 'depths', movieY);
  await page.goForward();
  await articleReady(page, depthsPath);
  await waitForReadingPosition(page, readingY);

  assert.ok(!(await page.locator('#reader-bottom').innerText()).includes('次に読む：'));
  const related = page.locator('#reader-bottom .reader-related a[href^="#/"]').first();
  assert.ok(await related.count(), 'A world article should offer an intentional related article');
  const relatedPath = decodeURIComponent((await related.getAttribute('href')).replace(/^#\/?/,''));
  assert.notEqual(relatedPath, depthsPath);
  await related.scrollIntoViewIfNeeded();
  await paint(page);
  const previousReadingY = await page.evaluate(() => scrollY);
  await related.click();
  await articleReady(page, relatedPath);
  const relatedReadingY = await readPartway(page, 340);

  await page.goBack();
  await articleReady(page, depthsPath);
  await waitForReadingPosition(page, previousReadingY);
  await page.goForward();
  await articleReady(page, relatedPath);
  await waitForReadingPosition(page, relatedReadingY);

  // Returning after more than one article must retain the originating movie
  // position, rather than merely going back to the previous article.
  const resume = page.locator('#reader-bottom [data-return-to-story]').filter({hasText:'物語の続きへ'});
  await resume.click();
  await waitForMoviePosition(page, 'depths', movieY);
  console.log(JSON.stringify({check:'movie and article history', width, movieY, readingY, relatedPath}));
}

async function checkMobileContents(page) {
  await openMovie(page);
  await seekByScrolling(page, 'depths');
  await page.locator('#depths a').filter({hasText:/迷宮/}).click();
  await articleReady(page, depthsPath);
  const contents = page.locator('details.reader-toc');
  assert.equal(await contents.evaluate(element => element.open), false);
  await contents.getByText('資料の目次', {exact:true}).click();
  assert.equal(await contents.evaluate(element => element.open), true);
  const links = contents.locator('#mobile-categories a');
  assert.equal(await links.count(), 13);
  const groups = await contents.locator('#mobile-categories').evaluate(element =>
    [...element.children].filter(child => child.tagName !== 'A' && child.querySelector('a')).length);
  assert.ok(groups >= 2, 'Contents should present labeled groups, not a flat tab row');
  const positions = await links.evaluateAll(elements => elements.map(element => element.getBoundingClientRect().top));
  assert.ok(positions.every((position, index) => index === 0 || position > positions[index-1]),
    'Mobile contents should have vertically arranged links');
  await contents.getByText('資料の目次', {exact:true}).click();
  assert.equal(await contents.evaluate(element => element.open), false);
  console.log(JSON.stringify({check:'mobile grouped contents', groups, articles:13}));
}

async function waitForHomePosition(page, expectedY) {
  try {
    await page.waitForFunction(expectedY =>
      !document.getElementById('home-view').classList.contains('hidden') && Math.abs(scrollY - expectedY) <= 2,
    expectedY, {timeout:7000});
  } catch (error) {
    const actual = await page.evaluate(() => ({hash:location.hash,y:scrollY,
      height:document.documentElement.scrollHeight,bodyClass:document.body.className,
      homeVisible:!document.getElementById('home-view').classList.contains('hidden'),
      archiveOpen:document.querySelector('.film-archive-disclosure').open}));
    console.error('Home restoration mismatch:', JSON.stringify({expectedY,...actual}));
    error.message += '\nHome restoration: '+JSON.stringify({expectedY,...actual});
    throw error;
  }
}

async function checkArchiveOrigin(page,width) {
  await openMovie(page);
  await page.goto(base+'#map');
  await waitForScene(page,'map');
  await page.goto(base+'#guide');
  const archive = page.locator('.film-archive-disclosure');
  await page.waitForFunction(() => document.querySelector('.film-archive-disclosure').open &&
    !document.body.classList.contains('is-watching-film'));
  const articleLink = archive.locator('a').filter({hasText:'迷宮と探索'});
  await articleLink.scrollIntoViewIfNeeded();
  await paint(page);
  const openY = await page.evaluate(() => scrollY);
  await articleLink.click();
  await articleReady(page,depthsPath);
  await page.locator('#reader-bottom [data-return-to-story]').filter({hasText:'元の場所へ戻る'}).click();
  await waitForHomePosition(page,openY);
  assert.equal(await archive.evaluate(element => element.open),true);

  // The same #guide entry can also have its disclosure intentionally closed.
  // Following a header link must not make returning reopen the disclosure.
  await archive.locator('summary').click();
  const creationLink = page.locator('.site-header').getByRole('link',{name:'キャラクターをつくる',exact:true});
  await paint(page);
  const box = await creationLink.boundingBox();
  assert.ok(box && await creationLink.isVisible());
  const closedY = await page.evaluate(() => scrollY);
  // The sticky header is already visible. Clicking its actual coordinates
  // avoids Playwright re-centering its scroll container before the click.
  await page.mouse.click(box.x + box.width/2, box.y + box.height/2);
  await articleReady(page,'players/キャラクター作成ガイド.md');
  await page.locator('#reader-bottom [data-return-to-story]').filter({hasText:'元の場所へ戻る'}).click();
  await waitForHomePosition(page,closedY);
  assert.equal(await archive.evaluate(element => element.open),false);
  console.log(JSON.stringify({check:'post-movie origin and disclosure state',width,openY,closedY}));
}

async function checkDirectArticle(browser) {
  const page = await browser.newPage({viewport:{width:390,height:844}});
  watchErrors(page);
  await page.goto(base+'#/'+encodeURIComponent(depthsPath),{waitUntil:'networkidle'});
  await articleReady(page,depthsPath);
  await page.locator('#reader-bottom [data-return-to-story]').filter({hasText:'物語を見る'}).click();
  await waitForMoviePosition(page,'opening',0);
  await page.close();
  console.log(JSON.stringify({check:'direct article has an explicit movie entrance'}));
}

async function checkReducedMotionReturn(browser) {
  const page = await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  watchErrors(page);
  await page.goto(base,{waitUntil:'networkidle'});
  await page.waitForFunction(() => window.RuosuenStory);
  assert.equal(await page.locator('.is-scroll-story').count(),0);
  await page.evaluate(() => {
    const depths = document.getElementById('depths');
    scrollTo({top:depths.getBoundingClientRect().top+scrollY+140,behavior:'instant'});
  });
  const articleLink = page.locator('#depths a').filter({hasText:/迷宮/});
  await articleLink.scrollIntoViewIfNeeded();
  await paint(page);
  const sourceY = await page.evaluate(() => scrollY);
  await articleLink.click();
  await articleReady(page,depthsPath);
  await page.locator('#reader-bottom [data-return-to-story]').click();
  await waitForHomePosition(page,sourceY);
  assert.equal(await page.locator('.is-scroll-story').count(),0);
  await page.close();
  console.log(JSON.stringify({check:'reduced-motion normal-flow return',sourceY}));
}

(async () => {
  const proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
  const executablePath = process.env.RUOSUEN_CHROMIUM ||
    (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
  const browser = await chromium.launch({
    headless:true,
    ...(executablePath ? {executablePath} : {}),
    args:['--no-sandbox','--disable-dev-shm-usage'],
    ...(proxy ? {proxy:{server:proxy,bypass:'127.0.0.1,localhost'}} : {})
  });
  try {
    for (const [width,height] of [[1440,900],[390,844]]) {
      const page = await browser.newPage({viewport:{width,height}});
      page.setDefaultTimeout(10000);
      watchErrors(page);
      await openMovie(page);
      await page.getByRole('link', {name:'物語を始める',exact:true}).click();
      await page.waitForFunction(() => document.querySelector('.film-sequence').dataset.activeScene === 'overture');
      await checkReadingHistory(page,width);
      await checkHookScenes(page,width);

      await page.goto(base+'#next');
      await page.waitForFunction(() => document.querySelector('.film-sequence').dataset.activeScene === 'next');
      const invitation = page.locator('#next').getByRole('link', {name:'キャラクターをつくる',exact:true});
      assert.ok(await invitation.isVisible());
      await invitation.click();
      await articleReady(page,'players/キャラクター作成ガイド.md');
      if (width === 390) await checkMobileContents(page);
      await checkArchiveOrigin(page,width);
      assert.equal(await page.locator('a[href="#/DECISIONS.md"]').count(),0,
        'Editor decisions must not be offered as a player route');
      await page.goto(base+'#/'+encodeURIComponent('docs/05_歴史と伝承.md'));
      await articleReady(page,'docs/05_歴史と伝承.md');
      assert.ok(!(await page.locator('#reader-bottom').innerText()).includes('次に読む：'));
      await page.close();
    }
    await checkDirectArticle(browser);
    await checkReducedMotionReturn(browser);
    assert.deepEqual(errors,[],'Unexpected browser errors');
    console.log(JSON.stringify({result:'PASS',viewports:[1440,390],bareUrlReturn:true,
      historyForward:true,articleHistory:true,relatedArticleReturn:true,groupedContents:true,
      archiveOrigin:true,archiveOpenState:true,directArticle:true,reducedMotionReturn:true,
      individualHooks:true,weightedScroll:true,hookDeepLinks:true,creationInvitation:true,errors}));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode=1; });
