/* motion-studio engine — the time primitives every composition shares.
 *
 * Copied into each project as lib/engine.js by scaffold.sh (never edit the copy; improve this file
 * and re-copy). Everything here is a pure function of t, so HyperFrames can seek any frame in any order.
 *
 *   MS.springStep(t, zeta, omega)    closed-form damped-spring step response, 0 → 1
 *   MS.springEase(zeta)              the same spring as a GSAP ease, settled by the tween's end
 *   MS.springDur(zeta, omega)       tween duration that makes springEase the physical spring; MS.SPRINGS presets
 *   MS.morph([{t,w,h,r}…])           one box through dot → pill → card (summed springs, lead axis) → fn(t)
 *   MS.lerpKeys([[t,v]…], t)         piecewise-linear keyframes
 *   MS.camera(spec)                  → fn(t) → {s,x,y,r} from CUES.camera (moves / punches / shakes / pulse)
 *   MS.camTransform(c)               → CSS transform string
 *   MS.shaderBg(canvas, opts)        ambient WebGL field; returns draw(t)
 *   MS.grain(canvas, opts)           per-frame hashed film grain; returns draw(t)
 *   MS.drive(tl, dur, fn)            one proxy tween that calls fn(t) every seek
 */
(function () {
  var MS = {};

  MS.springStep = function (t, zeta, omega) {
    if (t <= 0) return 0;
    if (zeta >= 1) return 1 - Math.exp(-omega * t) * (1 + omega * t); // critically damped
    var wd = omega * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * omega * t) * (Math.cos(wd * t) + (zeta * omega / wd) * Math.sin(wd * t));
  };

  MS.springEase = function (zeta) {
    // Stiffness chosen so the step has settled to < 0.1% at p = 1 — otherwise the final
    // `p >= 1 → 1` visibly snaps. Underdamped: bound the envelope incl. its 1/√(1−ζ²) amplitude.
    // Critically damped: e^(−k)(1+k) = 1e-3 → k ≈ 9.23 (was 6.2 → a 1.5% jump on the last frame).
    var k = zeta >= 1 ? 9.23 : Math.log(1000 / Math.sqrt(1 - zeta * zeta)) / zeta;
    return function (p) { return p >= 1 ? 1 : MS.springStep(p, zeta, k); };
  };

  /* The tween duration at which springEase(zeta) IS the physical spring of stiffness omega (rad/s):
   *   tl.to(el, { y: 0, ease: MS.springEase(z), duration: MS.springDur(z, w) })
   * so a spring measured on a reference (ζ, ω) is reproduced exactly, not eyeballed. */
  MS.springDur = function (zeta, omega) {
    var k = zeta >= 1 ? 9.23 : Math.log(1000 / Math.sqrt(1 - zeta * zeta)) / zeta;
    return k / omega;
  };

  /* Measured presets. `ui` = an Apple keynote UI object landing (card, pill, icon): reaches the target
   * in ~0.25 s, overshoots ~5 %, settles by ~0.62 s — fitted on a reference, 2026-10-08
   * (motion-apple/references/preset-keynote-ui.md). `settle` = no overshoot, for type and camera. */
  MS.SPRINGS = { ui: { zeta: 0.68, omega: 17 }, settle: { zeta: 1, omega: 14 } };

  /* A morphing container (Dynamic-Island style): ONE box that becomes a dot, a button, a pill, a card.
   *   var box = MS.morph([{t, w, h, r}, {t, w, h, r, zeta, omega, lead: "w"|"h", stagger}, …]);
   *   box(t) → {w, h, r}   — apply to an SVG <rect> (attr width/height/rx), never to CSS width.
   * Each state is a retarget summed like camera moves, so a change mid-flight keeps its velocity.
   * Defaults to MS.SPRINGS.ui. `lead` moves one axis first and starts the other `stagger` s later:
   * measured on a reference, the pill opens its WIDTH first, then its HEIGHT (preset-keynote-ui §8). */
  MS.morph = function (states) {
    var s0 = states[0];
    var steps = states.slice(1).map(function (s) {
      var z = s.zeta == null ? MS.SPRINGS.ui.zeta : s.zeta, w = s.omega == null ? MS.SPRINGS.ui.omega : s.omega;
      var st = s.stagger || 0;
      return { t: s.t, w: s.w, h: s.h, r: s.r, z: z, o: w,
               dw: s.lead === "h" ? st : 0, dh: s.lead === "w" ? st : 0, dr: st / 2 };
    });
    return function (t) {
      var w = s0.w, h = s0.h, r = s0.r, pw = s0.w, ph = s0.h, pr = s0.r;
      steps.forEach(function (s) {
        w += (s.w - pw) * MS.springStep(t - s.t - s.dw, s.z, s.o);
        h += (s.h - ph) * MS.springStep(t - s.t - s.dh, s.z, s.o);
        r += (s.r - pr) * MS.springStep(t - s.t - s.dr, s.z, s.o);
        pw = s.w; ph = s.h; pr = s.r;
      });
      return { w: w, h: h, r: Math.max(0, Math.min(r, w / 2, h / 2)) };
    };
  };

  MS.lerpKeys = function (keys, t) {
    if (t <= keys[0][0]) return keys[0][1];
    for (var i = 1; i < keys.length; i++) if (t <= keys[i][0]) {
      var a = keys[i - 1], b = keys[i], u = (t - a[0]) / (b[0] - a[0]);
      return a[1] + (b[1] - a[1]) * u;
    }
    return keys[keys.length - 1][1];
  };

  /* Camera as DATA (cues.json → "camera"):
   *   moves:   [{t, s, x, y, w}]   retargets; value = Σ Δ·springStep(t − tᵢ, 0.82, w)
   *   punches: [{t, a}]            scale kicks (12 ms attack, 140 ms decay)
   *   shakes:  [{t, amp}]          decaying 21/17 Hz shake, τ 85 ms
   *   pulse:   {from, to, every, a} beat-synced micro-punch through a groove
   * Marks may be given by name ("drop") and are resolved against CUES.marks. */
  MS.camera = function (spec, marks) {
    spec = spec || {};
    marks = marks || {};
    var at = function (v) { return typeof v === "string" ? marks[v] : v; };
    var moves = (spec.moves || []).map(function (m) { return { t: at(m.t) + (m.dt || 0), s: m.s == null ? 1 : m.s, x: m.x || 0, y: m.y || 0, w: m.w || 18 }; });
    var punches = (spec.punches || []).map(function (p) { return { t: at(p.t) + (p.dt || 0), a: p.a }; });
    var shakes = (spec.shakes || []).map(function (s) { return { t: at(s.t) + (s.dt || 0), amp: s.amp }; });
    if (spec.pulse) {
      var P = spec.pulse, from = at(P.from), to = at(P.to);
      for (var b = from + P.every; b < to - 1e-3; b += P.every) punches.push({ t: b, a: P.a });
    }
    return function (t) {
      var s = 1, x = 0, y = 0, r = 0, ps = 1, px = 0, py = 0;
      moves.forEach(function (m) {
        var k = MS.springStep(t - m.t, 0.82, m.w);
        s += (m.s - ps) * k; x += (m.x - px) * k; y += (m.y - py) * k;
        ps = m.s; px = m.x; py = m.y;
      });
      punches.forEach(function (p) {
        var d = t - p.t;
        if (d > 0) s += p.a * (1 - Math.exp(-d / 0.012)) * Math.exp(-d / 0.14);
      });
      shakes.forEach(function (e, i) {
        var d = t - e.t;
        if (d > 0 && d < 0.6) {
          var env = Math.exp(-d / 0.085) * e.amp;
          x += env * Math.sin(2 * Math.PI * 21 * d + i * 1.7);
          y += env * 0.7 * Math.sin(2 * Math.PI * 17 * d + i * 0.9);
          r += env * 0.028 * Math.sin(2 * Math.PI * 13 * d + i);
        }
      });
      return { s: s, x: x, y: y, r: r };
    };
  };

  MS.camTransform = function (c) {
    return "translate(" + c.x.toFixed(2) + "px," + c.y.toFixed(2) + "px) rotate(" + c.r.toFixed(3) + "deg) scale(" + c.s.toFixed(4) + ")";
  };

  function hexRgb(h) {
    h = h.replace("#", "");
    return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
  }

  /* Ambient field: base colour + a halo (glow colour) around `focus` + domain-warped fbm drift.
   * opts: {base:"#hex", glow:"#hex", spark:"#hex", inten:[[t,v]…], focus:[[t,x,y]…] or [x,y], w, h} */
  MS.shaderBg = function (canvas, opts) {
    var gl = canvas.getContext("webgl", { preserveDrawingBuffer: true, antialias: false });
    if (!gl) return function () {};
    var vs = "attribute vec2 p;varying vec2 uv;void main(){uv=p*.5+.5;gl_Position=vec4(p,0.,1.);}";
    var fs = [
      "precision highp float;varying vec2 uv;uniform float t;uniform float inten;uniform float pulse;uniform vec2 focus;uniform vec2 res;",
      "uniform vec3 base;uniform vec3 glow;uniform vec3 spark;",
      "float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}",
      "float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);",
      " return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}",
      "float fbm(vec2 p){float v=0.,a=.5;mat2 R=mat2(.8,.6,-.6,.8);for(int i=0;i<5;i++){v+=a*n(p);p=R*p*2.03;a*=.5;}return v;}",
      "void main(){vec2 q=uv;q.y=1.-q.y;vec2 a=vec2(q.x,q.y*res.y/res.x);",
      " vec2 w=vec2(fbm(a*1.6+vec2(0.,t*.05)),fbm(a*1.6+vec2(5.2,1.3)-t*.04));",
      " float f=fbm(a*1.2+w*1.8+t*.03);",
      " float halo=exp(-2.6*distance(q,focus))*1.1+exp(-4.5*distance(q,vec2(.85,.95)))*.3;",
      " vec3 col=base+glow*halo*(.55+.9*f)*inten+spark*pow(f,3.)*halo*.22*inten+spark*pulse*.06*halo;",
      " gl_FragColor=vec4(col,1.);}",
    ].join("\n");
    function sh(type, src) { var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }
    var pr = gl.createProgram();
    gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(pr); gl.useProgram(pr);
    var b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    var U = {};
    ["t", "inten", "pulse", "focus", "res", "base", "glow", "spark"].forEach(function (k) { U[k] = gl.getUniformLocation(pr, k); });
    gl.uniform3fv(U.base, hexRgb(opts.base)); gl.uniform3fv(U.glow, hexRgb(opts.glow)); gl.uniform3fv(U.spark, hexRgb(opts.spark || opts.glow));
    gl.uniform2f(U.res, canvas.width, canvas.height);
    var inten = opts.inten || [[0, 1]];
    return function (t, pulse) {
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform1f(U.t, t);
      gl.uniform1f(U.inten, MS.lerpKeys(inten, t));
      gl.uniform1f(U.pulse, pulse || 0);
      var f = opts.focus || [0.5, 0.1];
      if (Array.isArray(f[0])) {
        var fx = MS.lerpKeys(f.map(function (k) { return [k[0], k[1]]; }), t);
        var fy = MS.lerpKeys(f.map(function (k) { return [k[0], k[2]]; }), t);
        gl.uniform2f(U.focus, fx, fy);
      } else gl.uniform2f(U.focus, f[0], f[1]);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
  };

  /* Film grain: xorshift hashed per FRAME (not a looping texture). Draw into a small canvas
   * stretched over the frame with mix-blend overlay at 5–8% opacity. */
  MS.grain = function (canvas, opts) {
    opts = opts || {};
    var fps = opts.fps || 60, ctx = canvas.getContext("2d");
    var img = ctx.createImageData(canvas.width, canvas.height);
    return function (t) {
      var f = Math.floor(t * fps + 1e-6), d = img.data, s = ((f + 1) * 2654435761) >>> 0;
      for (var i = 0; i < d.length; i += 4) {
        s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0;
        var v = s & 255; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255;
      }
      ctx.putImageData(img, 0, 0);
    };
  };

  /* One proxy tween that calls fn(t) on every seek: the frame(t) hook for camera/shader/grain. */
  MS.drive = function (tl, dur, fn) {
    var clock = { t: 0 };
    tl.fromTo(clock, { t: 0 }, { t: dur, duration: dur, ease: "none", onUpdate: function () { fn(clock.t); } }, 0);
  };

  /* Beat helper: MS.beatPulse(t, from, to, spb) → 1 on each beat, decaying (for shader/UI glow). */
  MS.beatPulse = function (t, from, to, spb) {
    if (t < from || t > to) return 0;
    return Math.exp(-((t - from) % spb) / 0.12);
  };

  window.MS = MS;
})();
