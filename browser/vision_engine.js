/* Tiny CNN inference engine (runs in a Web Worker; also loadable in Node for tests).
   Executes the graph exported by scripts/export_vision_model.py: conv, depthwise conv, add,
   global average pool, fully connected, softmax. NHWC float32, TFLite SAME/VALID padding rules. */
var VISION = (function () {
  var M = null, T = null;
  function b64ToBytes(b64) { var bin = atob(b64), u = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }
  function prod(a) { var p = 1; for (var i = 0; i < a.length; i++) p *= a[i]; return p; }
  function load(model) {
    var bytes = b64ToBytes(model.weights), buf = bytes.buffer;
    function f32(off, n) { return new Float32Array(buf.slice(off, off + 4 * n)); }
    model.ops.forEach(function (op) {
      if (op.b) op.bias = f32(op.b.off, prod(op.b.shape));
      if (op.w) {
        var e = op.w, n = prod(e.shape), q = new Int8Array(buf, e.off, n), sc = f32(e.scale_off, e.shape[e.axis]), w = new Float32Array(n);
        if (op.t === "dw") {                       // stored [C][kh*kw] -> want [kh*kw][C]
          var C = e.shape[3], K = e.shape[1] * e.shape[2];
          for (var c = 0; c < C; c++) for (var k = 0; k < K; k++) w[k * C + c] = q[c * K + k] * sc[c];
        } else { var per = n / e.shape[0]; for (var o = 0; o < e.shape[0]; o++) for (var j = 0; j < per; j++) w[o * per + j] = q[o * per + j] * sc[o]; }
        op.wf = w;
      }
    });
    model.weights = null; M = model;
  }
  function act(v, a) { return a === 1 ? (v < 0 ? 0 : v) : a === 3 ? (v < 0 ? 0 : v > 6 ? 6 : v) : v; }
  function dims(shape, op, kh, kw) {
    var H = shape[1], W = shape[2], oh, ow, pt = 0, pl = 0;
    if (op.pad === "same") { oh = Math.ceil(H / op.sh); ow = Math.ceil(W / op.sw); pt = Math.max(0, ((oh - 1) * op.sh + kh - H)) >> 1; pl = Math.max(0, ((ow - 1) * op.sw + kw - W)) >> 1; }
    else { oh = Math.floor((H - kh) / op.sh) + 1; ow = Math.floor((W - kw) / op.sw) + 1; }
    return { H: H, W: W, oh: oh, ow: ow, pt: pt, pl: pl };
  }
  function conv(op, x, inShape) {
    var O = op.w.shape[0], kh = op.w.shape[1], kw = op.w.shape[2], I = op.w.shape[3], d = dims(inShape, op, kh, kw), out = new Float32Array(d.oh * d.ow * O), w = op.wf, b = op.bias;
    for (var oy = 0; oy < d.oh; oy++) for (var ox = 0; ox < d.ow; ox++) {
      var ob = (oy * d.ow + ox) * O;
      for (var o = 0; o < O; o++) {
        var acc = b[o];
        for (var ky = 0; ky < kh; ky++) {
          var iy = oy * op.sh - d.pt + ky; if (iy < 0 || iy >= d.H) continue;
          for (var kx = 0; kx < kw; kx++) {
            var ix = ox * op.sw - d.pl + kx; if (ix < 0 || ix >= d.W) continue;
            var ib = (iy * d.W + ix) * I, wb = ((o * kh + ky) * kw + kx) * I;
            for (var i = 0; i < I; i++) acc += x[ib + i] * w[wb + i];
          }
        }
        out[ob + o] = act(acc, op.act);
      }
    }
    return out;
  }
  function dw(op, x, inShape) {
    var kh = op.w.shape[1], kw = op.w.shape[2], C = op.w.shape[3], d = dims(inShape, op, kh, kw), out = new Float32Array(d.oh * d.ow * C), w = op.wf, b = op.bias;
    for (var oy = 0; oy < d.oh; oy++) for (var ox = 0; ox < d.ow; ox++) {
      var ob = (oy * d.ow + ox) * C, c;
      for (c = 0; c < C; c++) out[ob + c] = b[c];
      for (var ky = 0; ky < kh; ky++) {
        var iy = oy * op.sh - d.pt + ky; if (iy < 0 || iy >= d.H) continue;
        for (var kx = 0; kx < kw; kx++) {
          var ix = ox * op.sw - d.pl + kx; if (ix < 0 || ix >= d.W) continue;
          var ib = (iy * d.W + ix) * C, wb = (ky * kw + kx) * C;
          for (c = 0; c < C; c++) out[ob + c] += x[ib + c] * w[wb + c];
        }
      }
      for (c = 0; c < C; c++) out[ob + c] = act(out[ob + c], op.act);
    }
    return out;
  }
  /** pixels: Float32Array(224*224*3) already normalised ((v-127)/128) */
  function run(pixels) {
    var t = {}; t[M.input.idx] = pixels;
    var shapes = {}; shapes[M.input.idx] = M.input.shape;
    for (var k = 0; k < M.ops.length; k++) {
      var op = M.ops[k], x = t[op.in], s = shapes[op.in], out;
      if (op.t === "conv") out = conv(op, x, s);
      else if (op.t === "dw") out = dw(op, x, s);
      else if (op.t === "add") { var y = t[op.in2]; out = new Float32Array(x.length); for (var i = 0; i < x.length; i++) out[i] = act(x[i] + y[i], op.act); }
      else if (op.t === "avg") { var H = s[1], W = s[2], C = s[3]; out = new Float32Array(C); for (var p = 0; p < H * W; p++) for (var c = 0; c < C; c++) out[c] += x[p * C + c]; for (var c2 = 0; c2 < C; c2++) out[c2] /= H * W; }
      else if (op.t === "reshape") out = x;
      else if (op.t === "fc") { var O = op.w.shape[0], I = op.w.shape[1]; out = new Float32Array(O); for (var o = 0; o < O; o++) { var acc = op.bias[o]; for (var j = 0; j < I; j++) acc += x[j] * op.wf[o * I + j]; out[o] = acc; } }
      else if (op.t === "softmax") { var mx = -1e30, sum = 0; out = new Float32Array(x.length); for (var q = 0; q < x.length; q++) mx = Math.max(mx, x[q]); for (var q2 = 0; q2 < x.length; q2++) { out[q2] = Math.exp(x[q2] - mx); sum += out[q2]; } for (var q3 = 0; q3 < x.length; q3++) out[q3] /= sum; }
      t[op.out] = out; shapes[op.out] = op.shape;
    }
    return { probs: t[M.output], embed: t[M.embed] };
  }
  return { load: load, run: run };
})();
if (typeof self !== "undefined" && typeof window === "undefined") {   // inside a Worker
  self.onmessage = function (e) {
    var m = e.data;
    try {
      if (m.type === "init") { VISION.load(m.model); self.postMessage({ type: "ready" }); }
      else if (m.type === "run") { var r = VISION.run(m.pixels); self.postMessage({ type: "result", id: m.id, probs: r.probs, embed: r.embed }, [r.probs.buffer, r.embed.buffer]); }
    } catch (err) { self.postMessage({ type: "error", id: m.id, message: String(err) }); }
  };
}
