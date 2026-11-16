// Shared native-scroll motion for the intro, illustrated pages and reading pages.
// Transform/opacity only: reading positions and browser history keep their geometry.
function initScrollEffects() {
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const home = document.getElementById('home-view');
  const root = document.documentElement;
  let targets = [];
  let pending = 0;
  const clamp = value => Math.max(0,Math.min(1,value));
  const ease = value => value*value*(3-2*value);
  function render() {
    pending = 0;
    if (preference.matches) return;
    const height = innerHeight;
    // Read all geometry before writing animation styles.
    const measured = targets.map(element => ({element,bounds:element.getBoundingClientRect(),artHeight:element.querySelector('.story-art img')?.clientHeight}));
    for (const {element,bounds,artHeight} of measured) {
      const entry = ease(clamp((height-bounds.top)/(height*.3)));
      const passage = clamp((height-bounds.top)/(height+bounds.height));
      element.style.setProperty('--reveal-opacity',String(.3+.7*entry));
      element.style.setProperty('--reveal-y',`${(1-entry)*26}px`);
      element.style.setProperty('--art-shift-y',`${(passage-.5)*Math.min(22,(artHeight || bounds.height)*.036)}px`);
      if (element.id === 'opening') {
        const departure=clamp(-bounds.top/Math.max(1,bounds.height));
        element.style.setProperty('--intro-pan',`${departure*36}px`);
        element.style.setProperty('--intro-copy-y',`${-departure*24}px`);
        element.style.setProperty('--intro-copy-opacity',String(1-departure*.65));
      }
    }
  }
  function schedule() {
    if (!pending && !preference.matches) pending=requestAnimationFrame(render);
  }
  function refresh() {
    root.classList.toggle('scroll-effects',!preference.matches);
    targets = !home.classList.contains('hidden')
      ? [...document.querySelectorAll('#opening,.film-archive')]
      : [...document.querySelectorAll('#reader-view .article-hero,.story-panel,.reading-section,#reader-bottom')];
    targets.forEach(element=>element.setAttribute('data-scroll-reveal',''));
    if (preference.matches) return;
    schedule();
  }
  window.RuosuenScroll={refresh};
  addEventListener('scroll',schedule,{passive:true});
  addEventListener('resize',schedule,{passive:true});
  preference.addEventListener('change',refresh);
  document.fonts?.ready.then(refresh);
  refresh();
}
if (typeof window !== 'undefined') initScrollEffects();
