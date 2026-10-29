/* Pure-JavaScript DNG decoder for phone RAW files (runs in a Web Worker; also loadable in Node for tests).

   Handles what iPhones and RAW camera apps produce:
     * Apple ProRAW  - LinearRaw (3 samples/pixel), tiled, lossless-JPEG (compression 7)
     * Bayer RAW DNG - CFA, lossless JPEG or uncompressed (Halide, Lightroom, ProCamera ...)
   Output: linear sRGB floats (interleaved RGB), reduced to at most `maxSide` pixels on the long side,
   plus metadata.  The full-size image is never held in memory: each tile is decoded, converted and
   accumulated straight into the reduced image. */
var DNG = (function () {
  var TYPE_SIZE = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4, 16: 8 };

  /* ---------------------------------------------------------------- TIFF structure */
  function readIFD(dv, le, off, ifds, seen) {
    if (!off || off + 2 > dv.byteLength || seen[off]) return;
    seen[off] = 1;
    var n = dv.getUint16(off, le), tags = {};
    for (var i = 0; i < n; i++) {
      var e = off + 2 + i * 12; if (e + 12 > dv.byteLength) break;
      var tag = dv.getUint16(e, le), type = dv.getUint16(e + 2, le), count = dv.getUint32(e + 4, le), sz = (TYPE_SIZE[type] || 1) * count;
      var vo = sz <= 4 ? e + 8 : dv.getUint32(e + 8, le);
      tags[tag] = { type: type, count: count, off: vo };
    }
    var ifd = { tags: tags, dv: dv, le: le }; ifds.push(ifd);
    var sub = tags[330];
    if (sub) { var offs = vals(ifd, 330); for (var j = 0; j < offs.length; j++) readIFD(dv, le, offs[j], ifds, seen); }
    var next = dv.getUint32(off + 2 + n * 12, le); if (next) readIFD(dv, le, next, ifds, seen);
  }
  function vals(ifd, tag) {
    var t = ifd.tags[tag]; if (!t) return null; var dv = ifd.dv, le = ifd.le, out = new Array(t.count), o = t.off, i;
    for (i = 0; i < t.count; i++) {
      switch (t.type) {
        case 1: case 2: case 7: out[i] = dv.getUint8(o + i); break;
        case 6: out[i] = dv.getInt8(o + i); break;
        case 3: out[i] = dv.getUint16(o + 2 * i, le); break;
        case 8: out[i] = dv.getInt16(o + 2 * i, le); break;
        case 4: case 13: out[i] = dv.getUint32(o + 4 * i, le); break;
        case 9: out[i] = dv.getInt32(o + 4 * i, le); break;
        case 5: out[i] = dv.getUint32(o + 8 * i, le) / (dv.getUint32(o + 8 * i + 4, le) || 1); break;
        case 10: out[i] = dv.getInt32(o + 8 * i, le) / (dv.getInt32(o + 8 * i + 4, le) || 1); break;
        case 11: out[i] = dv.getFloat32(o + 4 * i, le); break;
        case 12: out[i] = dv.getFloat64(o + 8 * i, le); break;
        case 16: out[i] = Number(dv.getBigUint64(o + 8 * i, le)); break;
        default: out[i] = 0;
      }
    }
    return out;
  }
  function one(ifd, tag, d) { var v = vals(ifd, tag); return v && v.length ? v[0] : d; }

  /* ---------------------------------------------------------------- lossless JPEG (ITU T.81 process 14, as used by DNG) */
  function buildHuff(counts, syms) {
    var look = new Int32Array(65536).fill(-1), code = 0, k = 0;
    for (var len = 1; len <= 16; len++) {
      for (var i = 0; i < counts[len - 1]; i++, k++) {
        var lo = code << (16 - len), hi = lo + (1 << (16 - len));
        for (var c = lo; c < hi; c++) look[c] = (len << 8) | syms[k];
        code++;
      }
      code <<= 1;
    }
    return look;
  }
  function ljpeg(u8, start, end) {
    var p = start, sof = null, tabs = {}, ss = 1, pt = 0, scanComps = [], dri = 0;
    if (u8[p] !== 0xff || u8[p + 1] !== 0xd8) throw new Error("not a JPEG stream");
    p += 2;
    while (p + 4 < end) {
      if (u8[p] !== 0xff) { p++; continue; }
      var m = u8[p + 1]; p += 2;
      if (m === 0xff) { p--; continue; }
      if (m === 0xd8 || m === 0x01 || (m >= 0xd0 && m <= 0xd7)) continue;
      var len = (u8[p] << 8) | u8[p + 1];
      if (m === 0xc3) {
        sof = { prec: u8[p + 2], Y: (u8[p + 3] << 8) | u8[p + 4], X: (u8[p + 5] << 8) | u8[p + 6], nf: u8[p + 7], comps: [] };
        for (var i = 0; i < sof.nf; i++) sof.comps.push({ id: u8[p + 8 + i * 3], hv: u8[p + 9 + i * 3] });
      } else if (m === 0xc0 || m === 0xc1 || m === 0xc2) throw new Error("lossy JPEG DNG is not supported");
      else if (m === 0xc4) {
        var q = p + 2;
        while (q < p + len) {
          var tcth = u8[q++], counts = u8.subarray(q, q + 16), total = 0; q += 16;
          for (var c = 0; c < 16; c++) total += counts[c];
          tabs[tcth & 15] = buildHuff(counts, u8.subarray(q, q + total)); q += total;
        }
      } else if (m === 0xdd) dri = (u8[p + 2] << 8) | u8[p + 3];
      else if (m === 0xda) {
        var ns = u8[p + 2]; scanComps = [];
        for (var s = 0; s < ns; s++) scanComps.push({ id: u8[p + 3 + s * 2], table: u8[p + 4 + s * 2] >> 4 });
        ss = u8[p + 3 + ns * 2]; pt = u8[p + 5 + ns * 2] & 15; p += len; break;
      }
      p += len;
    }
    if (!sof) throw new Error("no SOF3 in stream");
    if (dri) throw new Error("restart intervals are not supported");
    var X = sof.X, Y = sof.Y, nf = sof.nf, prec = sof.prec, out = new Uint16Array(X * Y * nf);
    var look = []; for (var ci = 0; ci < nf; ci++) look.push(tabs[scanComps[ci] ? scanComps[ci].table : 0]);
    // bit reader (handles 0xFF00 byte stuffing)
    var pos = p, acc = 0, bits = 0, stop = end;
    function fill() {
      while (bits <= 24) {
        var b = 0;
        if (pos < stop) { b = u8[pos++]; if (b === 0xff) { var n2 = u8[pos]; if (n2 === 0) pos++; else { pos--; stop = pos; b = 0; } } }
        acc = (acc << 8) | b; bits += 8;
      }
    }
    var rowStride = X * nf, init = 1 << (prec - pt - 1), mask = (1 << prec) - 1;
    for (var y = 0; y < Y; y++) {
      for (var x = 0; x < X; x++) {
        for (var c2 = 0; c2 < nf; c2++) {
          fill();
          var e = look[c2][(acc >>> (bits - 16)) & 0xffff];
          if (e < 0) throw new Error("bad Huffman code");
          bits -= e >> 8; var sym = e & 255, diff = 0;
          if (sym === 16) diff = 32768;
          else if (sym) {
            if (bits < sym) fill();
            var v = (acc >>> (bits - sym)) & ((1 << sym) - 1); bits -= sym;
            diff = v < (1 << (sym - 1)) ? v - (1 << sym) + 1 : v;
          }
          var idx = (y * X + x) * nf + c2, pred;
          if (y === 0) pred = x === 0 ? init : out[idx - nf];
          else if (x === 0) pred = out[idx - rowStride];
          else {
            var Ra = out[idx - nf], Rb = out[idx - rowStride], Rc = out[idx - rowStride - nf];
            switch (ss) {
              case 1: pred = Ra; break; case 2: pred = Rb; break; case 3: pred = Rc; break;
              case 4: pred = Ra + Rb - Rc; break; case 5: pred = Ra + ((Rb - Rc) >> 1); break;
              case 6: pred = Rb + ((Ra - Rc) >> 1); break; case 7: pred = (Ra + Rb) >> 1; break; default: pred = 0;
            }
          }
          out[idx] = (pred + diff) & mask;
        }
      }
    }
    if (pt) for (var i2 = 0; i2 < out.length; i2++) out[i2] <<= pt;
    return { X: X, Y: Y, nf: nf, prec: prec, data: out };
  }

  /* ---------------------------------------------------------------- uncompressed samples (MSB-first packed) */
  function unpack(u8, off, n, bps, le) {
    var out = new Uint16Array(n), i;
    if (bps === 16) { for (i = 0; i < n; i++) out[i] = le ? u8[off + 2 * i] | (u8[off + 2 * i + 1] << 8) : (u8[off + 2 * i] << 8) | u8[off + 2 * i + 1]; return out; }
    if (bps === 8) { for (i = 0; i < n; i++) out[i] = u8[off + i]; return out; }
    var acc = 0, bits = 0, p = off;
    for (i = 0; i < n; i++) { while (bits < bps) { acc = ((acc << 8) | u8[p++]) >>> 0; bits += 8; } out[i] = (acc >>> (bits - bps)) & ((1 << bps) - 1); bits -= bps; }
    return out;
  }

  /* ---------------------------------------------------------------- colour */
  var XYZ50_TO_SRGB = [3.1338561, -1.6168667, -0.4906146, -0.9787684, 1.9161415, 0.033454, 0.0719453, -0.2289914, 1.4052427];
  function mul3(A, B) { var o = new Array(9); for (var i = 0; i < 3; i++) for (var j = 0; j < 3; j++) o[i * 3 + j] = A[i * 3] * B[j] + A[i * 3 + 1] * B[3 + j] + A[i * 3 + 2] * B[6 + j]; return o; }
  function inv3(m) {
    var a = m[0], b = m[1], c = m[2], d = m[3], e = m[4], f = m[5], g = m[6], h = m[7], i = m[8], det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
    return [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det, (f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det, (d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det];
  }
  function mulv(m, v) { return [m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2], m[6] * v[0] + m[7] * v[1] + m[8] * v[2]]; }
  function cctFromXYZ(X, Y, Z) { var s = X + Y + Z, x = X / s, y = Y / s, n = (x - 0.332) / (0.1858 - y); return 449 * n * n * n + 3525 * n * n + 6823.3 * n + 5520.33; }
  /** camera RGB -> linear sRGB 3x3 (includes white balance from AsShotNeutral) */
  function colorMatrix(ifd0, rawIfd, neutral) {
    function g(tag) { return vals(rawIfd, tag) || vals(ifd0, tag); }
    var fm1 = g(50964), fm2 = g(50965), cm1 = g(50721), cm2 = g(50722), ill1 = (g(50778) || [17])[0], ill2 = (g(50779) || [21])[0];
    var n = neutral || [1, 1, 1], wb = [1 / n[0], 1 / n[1], 1 / n[2]], toXYZ = null;
    function weight() {   // interpolate the two calibrations by colour temperature of the as-shot white
      if (!(cm2 && fm1 && fm2)) return 0;
      var xyz = mulv(inv3(cm2), n), cct = cctFromXYZ(xyz[0], xyz[1], xyz[2]), t1 = ill1 === 17 ? 2856 : 6504, t2 = ill2 === 21 ? 6504 : 2856;
      var w = (1 / cct - 1 / t2) / (1 / t1 - 1 / t2); return Math.max(0, Math.min(1, isFinite(w) ? w : 0));
    }
    if (fm1 || fm2) {
      var f1 = fm1 || fm2, f2 = fm2 || fm1, w1 = weight(), fm = new Array(9);
      for (var i = 0; i < 9; i++) fm[i] = w1 * f1[i] + (1 - w1) * f2[i];
      toXYZ = mul3(fm, [wb[0], 0, 0, 0, wb[1], 0, 0, 0, wb[2]]);
    } else if (cm1 || cm2) {   // no ForwardMatrix: invert ColorMatrix and adapt the as-shot white to D50
      var cm = cm2 || cm1, camToXYZ = inv3(cm), w = mulv(camToXYZ, n), D50 = [0.96422, 1, 0.82521];
      var BR = [0.8951, 0.2664, -0.1614, -0.7502, 1.7135, 0.0367, 0.0389, -0.0685, 1.0296], BRi = inv3(BR), cs = mulv(BR, w), cd = mulv(BR, D50);
      toXYZ = mul3(mul3(BRi, mul3([cd[0] / cs[0], 0, 0, 0, cd[1] / cs[1], 0, 0, 0, cd[2] / cs[2]], BR)), camToXYZ);
    }
    return toXYZ ? mul3(XYZ50_TO_SRGB, toXYZ) : [1, 0, 0, 0, 1, 0, 0, 0, 1];
  }

  /* ---------------------------------------------------------------- main */
  function decode(buf, maxSide, onProgress) {
    var u8 = new Uint8Array(buf), dv = new DataView(buf), le = u8[0] === 0x49;
    if (!((u8[0] === 0x49 && u8[1] === 0x49) || (u8[0] === 0x4d && u8[1] === 0x4d))) throw new Error("not a TIFF/DNG file");
    var magic = dv.getUint16(2, le); if (magic !== 42) throw new Error("unsupported TIFF variant");
    var ifds = []; readIFD(dv, le, dv.getUint32(4, le), ifds, {});
    var ifd0 = ifds[0], raw = null, best = 0;
    ifds.forEach(function (f) {
      var ph = one(f, 262, 0), w = one(f, 256, 0), h = one(f, 257, 0);
      if ((ph === 32803 || ph === 34892) && w * h > best) { best = w * h; raw = f; }
    });
    if (!raw) throw new Error("no RAW image found in this DNG");
    var W = one(raw, 256), H = one(raw, 257), bps = (vals(raw, 258) || [16])[0], spp = one(raw, 277, 1), comp = one(raw, 259, 1), ph = one(raw, 262);
    if (comp !== 1 && comp !== 7) throw new Error("this DNG uses compression " + comp + " (supported: none, lossless JPEG)");
    var linear = ph === 34892, cfa = vals(raw, 33422) || [0, 1, 1, 2], cfaDim = vals(raw, 33421) || [2, 2];
    if (!linear && (cfaDim[0] !== 2 || cfaDim[1] !== 2)) throw new Error("unsupported CFA layout");
    var black = vals(raw, 50714) || vals(ifd0, 50714) || [0], white = one(raw, 50717, null) || one(ifd0, 50717, (1 << bps) - 1), bdim = vals(raw, 50713) || [1, 1];
    var neutral = vals(ifd0, 50728) || vals(raw, 50728);
    var M = colorMatrix(ifd0, raw, neutral);
    var orient = one(ifd0, 274, 1);
    var crop = { x: 0, y: 0, w: W, h: H }, co = vals(raw, 50719) || vals(ifd0, 50719), cs = vals(raw, 50720) || vals(ifd0, 50720);
    if (co && cs) { crop = { x: co[0] | 0, y: co[1] | 0, w: Math.min(cs[0], W - co[0]) | 0, h: Math.min(cs[1], H - co[1]) | 0 }; if (!linear) { crop.x &= ~1; crop.y &= ~1; } }

    // output grid (before orientation): scale so the long side <= maxSide
    var unit = linear ? 1 : 2;                       // Bayer is binned 2x2 into one RGB pixel
    var baseW = Math.floor(crop.w / unit), baseH = Math.floor(crop.h / unit), sc = Math.max(1, Math.max(baseW, baseH) / maxSide);
    var oW = Math.max(1, Math.floor(baseW / sc)), oH = Math.max(1, Math.floor(baseH / sc));
    var sum = new Float32Array(oW * oH * 3), cnt = new Float32Array(oW * oH);

    // data units
    var tiled = !!raw.tags[324], offs = vals(raw, tiled ? 324 : 273), sizes = vals(raw, tiled ? 325 : 279);
    var tw = tiled ? one(raw, 322) : W, th = tiled ? one(raw, 323) : one(raw, 278, H), perRow = Math.ceil(W / tw);
    var scale = function (v, ch) { var b = black[ch % black.length]; return Math.max(0, (v - b) / Math.max(1, white - b)); };

    for (var t = 0; t < offs.length; t++) {
      if (onProgress && (t & 3) === 0) onProgress(t / offs.length);
      var tx = tiled ? (t % perRow) * tw : 0, ty = tiled ? Math.floor(t / perRow) * th : t * th, tH = tiled ? th : Math.min(th, H - ty), tW = tiled ? tw : W;
      var data;
      if (comp === 7) {
        var d = ljpeg(u8, offs[t], offs[t] + sizes[t]);
        if (linear) { if (d.nf !== spp) throw new Error("component count mismatch"); data = d.data; tW = d.X; tH = d.Y; }
        else { data = d.data; tW = d.X * d.nf; tH = d.Y; }                       // interleaved Bayer pairs become pixels in a row
      } else data = unpack(u8, offs[t], tW * tH * spp, bps, le);
      if (linear) {
        for (var y = 0; y < tH; y++) {
          var gy = ty + y - crop.y; if (gy < 0 || gy >= crop.h) continue; var oy = Math.min(oH - 1, Math.floor(gy / sc));
          for (var x = 0; x < tW; x++) {
            var gx = tx + x - crop.x; if (gx < 0 || gx >= crop.w) continue; var ox = Math.min(oW - 1, Math.floor(gx / sc)), s = (y * tW + x) * spp, o = oy * oW + ox;
            sum[o * 3] += scale(data[s], 0); sum[o * 3 + 1] += scale(data[s + 1], 1); sum[o * 3 + 2] += scale(data[s + 2], 2); cnt[o]++;
          }
        }
      } else {
        for (var y2 = 0; y2 + 1 < tH; y2 += 2) {
          var gy2 = ty + y2 - crop.y; if (gy2 < 0 || gy2 + 1 >= crop.h) continue; var oy2 = Math.min(oH - 1, Math.floor(gy2 / 2 / sc));
          for (var x2 = 0; x2 + 1 < tW; x2 += 2) {
            var gx2 = tx + x2 - crop.x; if (gx2 < 0 || gx2 + 1 >= crop.w) continue; var ox2 = Math.min(oW - 1, Math.floor(gx2 / 2 / sc)), o2 = oy2 * oW + ox2;
            var r = 0, g = 0, b = 0, ng = 0;
            for (var k = 0; k < 4; k++) {
              var v = data[(y2 + (k >> 1)) * tW + x2 + (k & 1)], col = cfa[k], bl = black.length >= 4 ? black[k] : black[0], val = Math.max(0, (v - bl) / Math.max(1, white - bl));
              if (col === 0) r = val; else if (col === 2) b = val; else { g += val; ng++; }
            }
            sum[o2 * 3] += r; sum[o2 * 3 + 1] += g / Math.max(1, ng); sum[o2 * 3 + 2] += b; cnt[o2]++;
          }
        }
      }
    }
    // average, camera RGB -> linear sRGB
    var rgb = new Float32Array(oW * oH * 3);
    for (var i = 0; i < oW * oH; i++) {
      var c = cnt[i] || 1, r0 = sum[i * 3] / c, g0 = sum[i * 3 + 1] / c, b0 = sum[i * 3 + 2] / c;
      rgb[i * 3] = Math.max(0, M[0] * r0 + M[1] * g0 + M[2] * b0); rgb[i * 3 + 1] = Math.max(0, M[3] * r0 + M[4] * g0 + M[5] * b0); rgb[i * 3 + 2] = Math.max(0, M[6] * r0 + M[7] * g0 + M[8] * b0);
    }
    // EXIF orientation
    var w = oW, h = oH, res = rgb;
    if (orient !== 1) {
      var swap = orient >= 5, nw = swap ? h : w, nh = swap ? w : h, o3 = new Float32Array(rgb.length);
      for (var yy = 0; yy < h; yy++) for (var xx = 0; xx < w; xx++) {
        var dx, dy;
        switch (orient) {
          case 2: dx = w - 1 - xx; dy = yy; break; case 3: dx = w - 1 - xx; dy = h - 1 - yy; break; case 4: dx = xx; dy = h - 1 - yy; break;
          case 5: dx = yy; dy = xx; break; case 6: dx = h - 1 - yy; dy = xx; break; case 7: dx = h - 1 - yy; dy = w - 1 - xx; break; case 8: dx = yy; dy = w - 1 - xx; break; default: dx = xx; dy = yy;
        }
        var si = (yy * w + xx) * 3, di = (dy * nw + dx) * 3; o3[di] = rgb[si]; o3[di + 1] = rgb[si + 1]; o3[di + 2] = rgb[si + 2];
      }
      res = o3; w = nw; h = nh;
    }
    return { w: w, h: h, rgb: res, meta: { source: [W, H], kind: linear ? "ProRAW / linear DNG" : "Bayer DNG", bits: bps, orientation: orient, compressed: comp === 7, tiles: offs.length } };
  }
  return { decode: decode, _ljpeg: ljpeg, _ifds: function (b) { var dv = new DataView(b), le = new Uint8Array(b)[0] === 0x49, l = []; readIFD(dv, le, dv.getUint32(4, le), l, {}); return l; }, _vals: vals };
})();
if (typeof self !== "undefined" && typeof window === "undefined") {
  self.onmessage = function (e) {
    var m = e.data;
    try { var r = DNG.decode(m.buffer, m.maxSide, function (f) { self.postMessage({ type: "progress", f: f }); }); self.postMessage({ type: "done", id: m.id, w: r.w, h: r.h, rgb: r.rgb, meta: r.meta }, [r.rgb.buffer]); }
    catch (err) { self.postMessage({ type: "error", id: m.id, message: String(err && err.message || err) }); }
  };
}
