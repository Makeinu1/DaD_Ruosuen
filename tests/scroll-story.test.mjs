import test from 'node:test';
import assert from 'node:assert/strict';
import {sceneAt, createTimeline} from '../assets/scroll-story.mjs';

test('the first scene is readable before the opening transition', () => {
  for (const position of [-100, 0, 0.2, 0.58]) {
    const state = sceneAt(position, 8);
    assert.equal(state.active, 0);
    assert.equal(state.mix, 0);
  }
});

test('a dissolve has exactly two adjacent scenes and ends on the next scene', () => {
  const middle = sceneAt(2.79, 8);
  assert.equal(middle.from, 2);
  assert.equal(middle.to, 3);
  assert.ok(Math.abs(middle.mix - 0.5) < 1e-10);
  const before = sceneAt(2.999999, 8);
  const after = sceneAt(3, 8);
  assert.ok(before.mix > 0.99999);
  assert.equal(before.active, after.active);
  assert.equal(after.mix, 0);
});

test('reverse scrolling produces the same scene state without accumulated timing', () => {
  const positions = Array.from({length:80}, (_, i) => i / 10);
  const forward = positions.map(position => sceneAt(position, 8));
  const backward = [...positions].reverse().map(position => sceneAt(position, 8)).reverse();
  assert.deepEqual(backward, forward);
});

test('the final reading interval and values outside the story stay on the final scene', () => {
  for (const position of [7, 7.4, 7.65, 999]) {
    const state = sceneAt(position, 8);
    assert.equal(state.from, 7);
    assert.equal(state.to, 7);
    assert.equal(state.active, 7);
    assert.equal(state.mix, 0);
  }
  assert.equal(sceneAt(999, 8).progress, 1);
});

test('a single scene and restored invalid positions have safe bounds', () => {
  assert.equal(sceneAt(0.5, 1).active, 0);
  assert.equal(sceneAt(NaN, 8).value, 0);
  assert.throws(() => sceneAt(0, 0), RangeError);
});

test('short hook scenes use half the distance without changing earlier scenes', () => {
  const timeline = createTimeline([1, 1, 1, 1, 1, 1, 0.35, 0.5, 0.5, 0.5, 0.5, 1]);
  assert.equal(timeline.distanceAt(5.27), 5.27);
  assert.ok(Math.abs(timeline.distanceAt(8) - timeline.distanceAt(7) - 0.5) < 1e-10);
  assert.ok(Math.abs(timeline.distanceAt(7) - timeline.distanceAt(6) - 0.35) < 1e-10);
  assert.ok(Math.abs(timeline.travel - 9) < 1e-10);
  assert.equal(timeline.positionAt(-10), 0);
  assert.ok(Math.abs(timeline.positionAt(100) - 11.65) < 1e-10);
});

test('weighted progression and saved scene positions round-trip in both directions', () => {
  const timeline = createTimeline([1, 0.35, 0.5, 0.5, 1]);
  for (const position of [0, 0.79, 1, 1.27, 1.79, 2, 2.79, 3.2, 4, 4.65]) {
    assert.ok(Math.abs(timeline.positionAt(timeline.distanceAt(position)) - position) < 1e-10);
  }
  const boundary = timeline.distanceAt(2);
  assert.equal(sceneAt(timeline.positionAt(boundary), 5).active, 2);
  assert.ok(sceneAt(timeline.positionAt(boundary - 0.001), 5).mix > 0.99);
  assert.equal(timeline.distanceAt(NaN), 0);
  assert.throws(() => createTimeline([]), RangeError);
  assert.throws(() => createTimeline([1, 0]), RangeError);
  assert.throws(() => createTimeline([Infinity]), RangeError);
});
