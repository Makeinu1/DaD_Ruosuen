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

// Scene coordinates stay stable for links and history. A shorter pace only
// changes the native scroll distance needed to move through that scene.
export function createTimeline(paces) {
  if (!paces.length || paces.some(pace => !Number.isFinite(pace) || pace <= 0)) {
    throw new RangeError('Scene paces must be positive finite numbers');
  }
  const starts = [0];
  for (let i = 1; i < paces.length; i++) starts.push(starts[i - 1] + paces[i - 1]);
  const travel = starts.at(-1) + paces.at(-1) * 0.65;
  return {
    travel,
    positionAt(distance) {
      const value = clamp(Number.isFinite(distance) ? distance : 0, 0, travel);
      let index = 0;
      while (index < paces.length - 1 && value >= starts[index + 1]) index++;
      return index + (value - starts[index]) / paces[index];
    },
    distanceAt(position) {
      const value = sceneAt(position, paces.length).value;
      const index = Math.floor(value);
      return starts[index] + (value - index) * paces[index];
    }
  };
}

function initStory() {
  const sequence = document.querySelector('.film-sequence');
  if (!sequence) return;
  const stage = sequence.querySelector('.film-stage');
  const home = document.getElementById('home-view');
  const frames = [...sequence.querySelectorAll('[data-film-scene]')];
  const timeline = createTimeline(frames.map(frame => {
    const pace = Number(frame.dataset.filmPace);
    return pace > 0 && Number.isFinite(pace) ? pace : 1;
  }));
  const steps = [...sequence.querySelectorAll('[data-scene-step]')];
  const previousLink = document.getElementById('film-prev');
  const nextLink = document.getElementById('film-next');
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
  let end = 0;
  let headerHeight = 0;
  let flowFrames = [];
  let selection = 0;
  const readyImages = new WeakSet();
  const imageRequests = new WeakMap();

  function prepare(index) {
    const frame = frames[index];
    if (!frame) return Promise.resolve();
    if (!imageRequests.has(frame)) {
      const images = [...frame.querySelectorAll('img')];
      images.forEach(image => { image.loading = 'eager'; });
      const pending = Promise.all(images.map(image => image.decode().catch(() => {}))).then(() => {
        readyImages.add(frame);
        requestRender();
      });
      imageRequests.set(frame, pending);
    }
    return imageRequests.get(frame);
  }

  function updateControls(index) {
    const watching = !home.classList.contains('hidden') && index < frames.length - 1 && window.scrollY < end;
    document.body.classList.toggle('is-watching-film', watching);
    steps.forEach((step, i) => step.classList.toggle('is-current', i === index));
    if (previousLink) {
      previousLink.hidden = index === 0;
      previousLink.href = '#' + frames[Math.max(0, index - 1)].id;
      previousLink.setAttribute('aria-label', '前の場面：' + frames[Math.max(0, index - 1)].dataset.filmScene);
    }
    if (nextLink) {
      nextLink.hidden = index === frames.length - 1;
      nextLink.href = '#' + frames[Math.min(frames.length - 1, index + 1)].id;
      nextLink.setAttribute('aria-label', '次の場面：' + frames[Math.min(frames.length - 1, index + 1)].dataset.filmScene);
    }
  }

  function flowIndex() {
    const midpoint = window.scrollY + (window.innerHeight + headerHeight) / 2;
    const found = flowFrames.findIndex(bounds => bounds.top <= midpoint && bounds.bottom > midpoint);
    return found >= 0 ? found : window.scrollY >= end ? frames.length - 1 : 0;
  }

  function reset() {
    sequence.classList.remove('is-scroll-story');
    sequence.removeAttribute('data-active-scene');
    frames.forEach(frame => {
      frame.inert = false;
      frame.classList.remove('is-scene-visible');
      frame.removeAttribute('style');
    });
    enabled = false;
    lastValue = NaN;
  }

  function render() {
    scheduled = 0;
    if (home.classList.contains('hidden')) {
      document.body.classList.remove('is-watching-film');
      return;
    }
    if (!enabled) { updateControls(flowIndex()); return; }
    const state = sceneAt(timeline.positionAt((window.scrollY - start) / step), frames.length);
    if (state.value === lastValue) return;
    prepare(state.from);
    prepare(state.to);
    // Keep the previous painted scene until the incoming image can actually
    // be painted. A fast scene jump must not expose an empty black frame.
    if (!readyImages.has(frames[state.from]) || (state.mix > 0 && !readyImages.has(frames[state.to]))) return;
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
    updateControls(active);
    label.textContent = frames[active].dataset.filmScene;
    progress.style.transform = `scaleX(${timeline.distanceAt(state.value) / timeline.travel})`;
    sequence.dataset.activeScene = frames[active].id;
  }

  function requestRender() {
    if (!scheduled) scheduled = requestAnimationFrame(render);
  }

  function refresh() {
    if (home.classList.contains('hidden')) return;
    const wasEnabled = enabled;
    const previous = frames[active];
    headerHeight = header.getBoundingClientRect().height;
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
      flowFrames = frames.map(frame => {
        const bounds = frame.getBoundingClientRect();
        return {top: bounds.top + window.scrollY, bottom: bounds.bottom + window.scrollY, height: bounds.height};
      });
      end = sequence.getBoundingClientRect().bottom + window.scrollY;
      updateControls(flowIndex());
      return;
    }

    sequence.classList.add('is-scroll-story');
    const height = stage.getBoundingClientRect().height;
    const captions = frames.map(frame => frame.querySelector('[data-film-caption]'));
    const fits = captions.every(caption => caption.getBoundingClientRect().height <= height - 120);
    if (!fits) {
      reset();
      if (wasEnabled) previous.scrollIntoView({behavior:'instant', block:'start'});
      flowFrames = frames.map(frame => {
        const bounds = frame.getBoundingClientRect();
        return {top: bounds.top + window.scrollY, bottom: bounds.bottom + window.scrollY, height: bounds.height};
      });
      end = sequence.getBoundingClientRect().bottom + window.scrollY;
      updateControls(flowIndex());
      return;
    }
    start = sequence.getBoundingClientRect().top + window.scrollY;
    step = Math.max(480, height * 0.95);
    travel = timeline.travel * step;
    sequence.style.setProperty('--film-travel', `${travel}px`);
    end = start + travel + height;
    enabled = true;
    lastValue = NaN;
    if (wasInside) window.scrollTo({top: start + oldPosition * step, behavior:'instant'});
    else if (!wasEnabled && staticIndex >= 0) window.scrollTo({top: start + timeline.distanceAt(staticIndex) * step, behavior:'instant'});
    // The stacked frames share a viewport, so request their images before a
    // fast scroll can reach them. Raster colors remain entirely untouched.
    frames.forEach(frame => frame.querySelectorAll('img').forEach(img => { img.loading = 'eager'; }));
    prepare(sceneAt(timeline.positionAt((window.scrollY - start) / step), frames.length).active);
    render();
  }

  async function goTo(id) {
    if (!enabled) return false;
    const index = frames.findIndex(frame => frame.id === id);
    if (index < 0) return false;
    const token = ++selection;
    await prepare(index);
    if (token !== selection || home.classList.contains('hidden')) return true;
    if (!enabled) return false;
    // A scene link selects a scene directly instead of rapidly scrubbing
    // through every intervening scene. Ordinary scrolling remains native.
    window.scrollTo({top: start + timeline.distanceAt(index) * step, behavior:'instant'});
    lastValue = NaN;
    render();
    frames[index].focus({preventScroll:true});
    return true;
  }

  function capture() {
    if (home.classList.contains('hidden')) return null;
    if (enabled) {
      if (window.scrollY > start + travel) return null;
      return {kind:'scroll', position:timeline.positionAt((window.scrollY - start) / step)};
    }
    if (window.scrollY >= end) return null;
    const index = flowIndex();
    const bounds = flowFrames[index];
    return bounds ? {kind:'flow', scene:frames[index].id, fraction:(window.scrollY + headerHeight - bounds.top) / bounds.height} : null;
  }

  async function restore(snapshot) {
    if (!snapshot) return false;
    const token = ++selection;
    const index = snapshot.kind === 'scroll' ? sceneAt(snapshot.position, frames.length).active : frames.findIndex(frame => frame.id === snapshot.scene);
    if (index < 0) return false;
    const position = snapshot.kind === 'scroll' ? snapshot.position : index + clamp(snapshot.fraction, 0, 0.55);
    const state = sceneAt(position, frames.length);
    if (enabled) {
      await Promise.all([prepare(state.from), prepare(state.to)]);
      if (token !== selection || home.classList.contains('hidden')) return true;
    }
    if (enabled) {
      window.scrollTo({top:start + timeline.distanceAt(state.value) * step, behavior:'instant'});
      lastValue = NaN;
      render();
      frames[index].focus({preventScroll:true});
    } else {
      const bounds = flowFrames[index];
      const fraction = snapshot.kind === 'flow' ? snapshot.fraction : snapshot.position - Math.floor(snapshot.position);
      window.scrollTo({top:bounds.top + fraction * bounds.height - headerHeight, behavior:'instant'});
      updateControls(index);
      frames[index].focus({preventScroll:true});
    }
    return true;
  }

  window.RuosuenStory = {refresh, goTo, capture, restore, cancelPending:() => { selection++; }};
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
