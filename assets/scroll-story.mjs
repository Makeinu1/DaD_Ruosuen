const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const smoothstep = (start, end, value) => {
  const t = clamp((value - start) / (end - start), 0, 1);
  return t * t * (3 - 2 * t);
};

// A full reading interval precedes each dissolve. Moving backwards samples
// exactly the same state; no timer, wheel interception, or animation queue.
export function sceneAt(position, count) {
  if (!Number.isInteger(count) || count < 1) throw new RangeError('A story needs at least one scene');
  const travel = count - 1 + 0.65;
  const value = clamp(Number.isFinite(position) ? position : 0, 0, travel);
  const from = Math.min(Math.floor(value), count - 1);
  const to = Math.min(from + 1, count - 1);
  const mix = from === to ? 0 : smoothstep(0.58, 1, value - from);
  return {from, to, mix, active: mix >= 0.5 ? to : from, value, progress: value / travel};
}

function initStory() {
  const sequence = document.querySelector('.film-sequence');
  if (!sequence) return;
  const stage = sequence.querySelector('.film-stage');
  const home = document.getElementById('home-view');
  const frames = [...sequence.querySelectorAll('[data-film-scene]')];
  const links = [...sequence.querySelectorAll('.film-scene-nav a')];
  const label = sequence.querySelector('.film-current-scene');
  const progress = sequence.querySelector('.film-story-progress span');
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  const header = document.querySelector('.site-header');
  let enabled = false;
  let start = 0;
  let step = 1;
  let travel = 0;
  let active = 0;
  let scheduled = 0;
  let lastValue = NaN;

  function reset() {
    sequence.classList.remove('is-scroll-story');
    sequence.removeAttribute('data-active-scene');
    frames.forEach(frame => {
      frame.inert = false;
      frame.classList.remove('is-scene-visible');
      frame.removeAttribute('style');
    });
    links.forEach(link => link.removeAttribute('aria-current'));
    enabled = false;
    lastValue = NaN;
  }

  function render() {
    scheduled = 0;
    if (!enabled || home.classList.contains('hidden')) return;
    const state = sceneAt((window.scrollY - start) / step, frames.length);
    if (state.value === lastValue) return;
    lastValue = state.value;
    active = state.active;
    frames.forEach((frame, index) => {
      const outgoing = index === state.from;
      const incoming = index === state.to && state.to !== state.from;
      const opacity = outgoing ? 1 - state.mix : incoming ? state.mix : 0;
      const caption = outgoing ? 1 - smoothstep(0.08, 0.48, state.mix)
        : incoming ? smoothstep(0.52, 0.92, state.mix) : 0;
      const local = clamp((state.value - index + 0.3) / 1.3, 0, 1);
      const zoom = frame.id === 'depths' ? 1.02 + local * 0.12 : 1.12 - local * 0.12;
      frame.style.opacity = String(opacity);
      frame.style.visibility = opacity > 0.001 ? 'visible' : 'hidden';
      frame.style.zIndex = incoming ? '2' : '1';
      frame.style.setProperty('--scene-caption', caption.toFixed(4));
      frame.style.setProperty('--scene-caption-y', `${(1 - caption) * 16}px`);
      frame.style.setProperty('--scene-zoom', zoom.toFixed(4));
      frame.style.setProperty('--scene-pan', `${(local - 0.5) * (frame.id === 'cargo' ? -30 : 16)}px`);
      frame.inert = index !== active || caption < 0.2;
      frame.classList.toggle('is-scene-visible', opacity > 0.001);
    });
    links.forEach((link, index) => {
      if (index === active) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
    });
    label.textContent = frames[active].dataset.filmScene;
    progress.style.transform = `scaleX(${state.progress})`;
    sequence.dataset.activeScene = frames[active].id;
  }

  function requestRender() {
    if (!scheduled && enabled) scheduled = requestAnimationFrame(render);
  }

  function refresh() {
    if (home.classList.contains('hidden')) return;
    const wasEnabled = enabled;
    const previous = frames[active];
    const headerHeight = header.getBoundingClientRect().height;
    const oldPosition = enabled ? (window.scrollY - start) / step : null;
    const wasInside = enabled && oldPosition >= 0 && window.scrollY <= start + travel;
    // Keep the same place when changing between normal flow and the pinned
    // sequence (rotation, text zoom, or a changed reduced-motion preference).
    const midpoint = (window.innerHeight + headerHeight) / 2;
    const staticIndex = wasEnabled ? -1 : frames.findIndex(frame => {
      const bounds = frame.getBoundingClientRect();
      return bounds.top <= midpoint && bounds.bottom > midpoint;
    });
    sequence.style.setProperty('--film-header-height', `${headerHeight}px`);
    if (media.matches || window.innerHeight - headerHeight < 540 ||
        !CSS.supports('position', 'sticky') || !('inert' in HTMLElement.prototype)) {
      reset();
      if (wasEnabled) previous.scrollIntoView({behavior:'instant', block:'start'});
      return;
    }

    sequence.classList.add('is-scroll-story');
    const height = stage.getBoundingClientRect().height;
    const captions = frames.map(frame => frame.querySelector('[data-film-caption]'));
    const fits = captions.every(caption => caption.getBoundingClientRect().height <= height - 120);
    if (!fits) {
      reset();
      if (wasEnabled) previous.scrollIntoView({behavior:'instant', block:'start'});
      return;
    }
    start = sequence.getBoundingClientRect().top + window.scrollY;
    step = Math.max(480, height * 0.95);
    travel = (frames.length - 1 + 0.65) * step;
    sequence.style.setProperty('--film-travel', `${travel}px`);
    enabled = true;
    lastValue = NaN;
    if (wasInside) window.scrollTo({top: start + oldPosition * step, behavior:'instant'});
    else if (!wasEnabled && staticIndex >= 0) window.scrollTo({top: start + staticIndex * step, behavior:'instant'});
    // The stacked frames share a viewport, so request their images before a
    // fast scroll can reach them. Raster colors remain entirely untouched.
    frames.forEach(frame => frame.querySelectorAll('img').forEach(img => { img.loading = 'eager'; }));
    render();
  }

  function goTo(id) {
    if (!enabled) return false;
    const index = frames.findIndex(frame => frame.id === id);
    if (index < 0) return false;
    // A scene link selects a scene directly instead of rapidly scrubbing
    // through every intervening scene. Ordinary scrolling remains native.
    window.scrollTo({top: start + index * step, behavior:'instant'});
    lastValue = NaN;
    render();
    frames[index].focus({preventScroll:true});
    return true;
  }

  window.RuosuenStory = {refresh, goTo};
  window.addEventListener('scroll', requestRender, {passive:true});
  window.addEventListener('resize', refresh, {passive:true});
  media.addEventListener('change', refresh);
  document.fonts?.ready.then(refresh);
  window.addEventListener('pageshow', refresh);
  refresh();
  // Classic reader code and this module can finish loading in either order.
  // Reapply the requested URL after the enhanced layout has been measured.
  window.dispatchEvent(new Event('ruosuen:story-ready'));
}

if (typeof window !== 'undefined') initStory();
