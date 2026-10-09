// node --test ~/.claude/skills/motion-studio/tests/engine.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("../templates/engine.js", import.meta.url), "utf8");
const ctx = { window: {}, Math };
vm.createContext(ctx);
vm.runInContext(src, ctx);
const MS = ctx.window.MS;

test("spring step starts at 0 and settles at 1", () => {
  assert.equal(MS.springStep(0, 0.74, 20), 0);
  assert.ok(Math.abs(MS.springStep(3, 0.74, 20) - 1) < 1e-4);
  assert.ok(Math.abs(MS.springStep(3, 1.0, 20) - 1) < 1e-4); // critically damped branch
});

test("spring overshoot at zeta 0.74 stays under 4%", () => {
  let peak = 0;
  for (let t = 0; t < 1; t += 0.001) peak = Math.max(peak, MS.springStep(t, 0.74, 20));
  assert.ok(peak > 1 && peak < 1.04, `peak ${peak}`);
});

test("springEase hits exactly 0 and 1 at the ends", () => {
  const e = MS.springEase(0.74);
  assert.equal(e(0), 0);
  assert.equal(e(1), 1);
});

test("springEase has no end-of-tween snap at any damping (incl. critical, zeta 1)", () => {
  for (const zeta of [0.74, 0.86, 1.0, 1.2]) {
    const e = MS.springEase(zeta);
    const gap = Math.abs(1 - e(0.999));
    assert.ok(gap < 0.003, `zeta ${zeta}: jumps ${gap} on the last frame`);
  }
});

test("springDur makes a GSAP springEase tween run the physical spring (zeta, omega)", () => {
  // keynote-ui UI spring, measured on a reference: zeta 0.68, omega 17 rad/s
  const zeta = 0.68, omega = 17, dur = MS.springDur(zeta, omega), e = MS.springEase(zeta);
  assert.ok(dur > 0.55 && dur < 0.7, `dur ${dur}`);
  for (const t of [0.05, 0.12, 0.2, 0.35]) {
    assert.ok(Math.abs(e(t / dur) - MS.springStep(t, zeta, omega)) < 1e-9, `t ${t}`);
  }
});

test("UI spring presets: settle has no overshoot, ui overshoots ~5%", () => {
  const peak = (p) => { let m = 0; for (let t = 0; t < 2; t += 0.0005) m = Math.max(m, MS.springStep(t, p.zeta, p.omega)); return m; };
  assert.ok(peak(MS.SPRINGS.settle) <= 1 + 1e-9);
  const ui = peak(MS.SPRINGS.ui);
  assert.ok(ui > 1.04 && ui < 1.07, `ui peak ${ui}`);
});

test("morph holds the first state, then retargets through every state and settles on the last", () => {
  const m = MS.morph([
    { t: 0, w: 40, h: 40, r: 20 },
    { t: 1, w: 400, h: 40, r: 20 },
    { t: 2, w: 400, h: 300, r: 40 },
  ]);
  const s = m(0.5);
  assert.ok(s.w === 40 && s.h === 40 && s.r === 20, JSON.stringify(s));
  const mid = m(1.9);
  assert.ok(Math.abs(mid.w - 400) < 1 && Math.abs(mid.h - 40) < 1e-9, JSON.stringify(mid)); // width first, height untouched
  const end = m(5);
  assert.ok(Math.abs(end.w - 400) < 1e-3 && Math.abs(end.h - 300) < 1e-3 && Math.abs(end.r - 40) < 1e-3);
  assert.deepEqual(m(1.37), m(1.37)); // pure function of t
});

test("morph overshoots with the ui spring and a lead axis staggers the other", () => {
  const m = MS.morph([{ t: 0, w: 100, h: 100, r: 10 }, { t: 1, w: 300, h: 300, r: 10, lead: "w", stagger: 0.1 }]);
  let peak = 0;
  for (let t = 1; t < 3; t += 0.002) peak = Math.max(peak, m(t).w);
  assert.ok(peak > 305 && peak < 320, `peak ${peak}`);          // ~5 % of the 200 px travel
  assert.ok(m(1.05).w > 110 && m(1.05).h === 100);               // h waits for its stagger
});

test("morph retarget mid-flight keeps velocity (no restart from zero)", () => {
  const m = MS.morph([{ t: 0, w: 0, h: 0, r: 0 }, { t: 1, w: 100, h: 0, r: 0 }, { t: 1.1, w: 200, h: 0, r: 0 }]);
  const v = (t) => (m(t + 1e-4).w - m(t - 1e-4).w) / 2e-4;
  assert.ok(v(1.1) > 50, `velocity at retarget ${v(1.1)}`);
});

test("lerpKeys interpolates and clamps", () => {
  const k = [[0, 0], [2, 10]];
  assert.equal(MS.lerpKeys(k, -1), 0);
  assert.equal(MS.lerpKeys(k, 1), 5);
  assert.equal(MS.lerpKeys(k, 9), 10);
});

test("camera resolves named marks, punches decay, rests at identity", () => {
  const cam = MS.camera({ punches: [{ t: "drop", a: 0.1 }], shakes: [{ t: "drop", amp: 10 }] }, { drop: 2 });
  const before = cam(1.9), hit = cam(2.05), after = cam(4);
  assert.equal(before.s, 1);
  assert.ok(hit.s > 1.03);
  assert.ok(Math.abs(after.s - 1) < 1e-6 && Math.abs(after.x) < 1e-6);
});

test("camera moves retarget and are a pure function of t", () => {
  const cam = MS.camera({ moves: [{ t: 1, s: 1.2, w: 20 }, { t: 3, s: 1, w: 20 }] }, {});
  assert.ok(Math.abs(cam(2.9).s - 1.2) < 1e-3);
  assert.ok(Math.abs(cam(6).s - 1) < 1e-3);
  assert.deepEqual(cam(2.5), cam(2.5));
});

test("pulse expands into per-beat punches inside its window only", () => {
  const cam = MS.camera({ pulse: { from: 0, to: 2, every: 0.5, a: 0.02 } }, {});
  assert.ok(cam(0.53).s > 1.005);
  assert.ok(Math.abs(cam(3.0).s - 1) < 1e-5); // exponential tails never hit exactly 0
});
