import test from 'node:test';
import assert from 'node:assert/strict';
import {sceneAt} from '../assets/scroll-story.mjs';

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
