"""Write test DNGs shaped like what iPhones produce: Apple-ProRAW-style tiled lossless-JPEG LinearRaw and
Bayer DNG, so the JavaScript decoder can be checked bit-for-bit (the compression is lossless) and against LibRaw."""
from __future__ import annotations

import struct

import numpy as np

XYZ50_TO_SRGB = np.array([[3.1338561, -1.6168667, -0.4906146], [-0.9787684, 1.9161415, 0.0334540], [0.0719453, -0.2289914, 1.4052427]])
SRGB_TO_XYZ50 = np.linalg.inv(XYZ50_TO_SRGB)


def ljpeg_encode(arr: np.ndarray, prec: int) -> bytes:
    """arr: (H, W, nf) uint16.  Predictor 1, one Huffman table (17 categories, 5 bits each)."""
    H, W, nf = arr.shape
    out = bytearray(b"\xff\xd8")
    out += b"\xff\xc3" + struct.pack(">HBHHB", 8 + 3 * nf, prec, H, W, nf)
    for c in range(nf):
        out += bytes([c + 1, 0x11, 0])
    out += b"\xff\xc4" + struct.pack(">H", 2 + 1 + 16 + 17) + b"\x00" + bytes([0] * 4 + [17] + [0] * 11) + bytes(range(17))
    out += b"\xff\xda" + struct.pack(">HB", 6 + 2 * nf, nf) + b"".join(bytes([c + 1, 0x00]) for c in range(nf)) + bytes([1, 0, 0])
    acc, nbits, body = 0, 0, bytearray()

    def put(val, n):
        nonlocal acc, nbits
        acc = (acc << n) | (val & ((1 << n) - 1)); nbits += n
        while nbits >= 8:
            b = (acc >> (nbits - 8)) & 0xFF; body.append(b)
            if b == 0xFF:
                body.append(0)
            nbits -= 8
        acc &= (1 << nbits) - 1

    init = 1 << (prec - 1)
    a = arr.astype(np.int64)
    for y in range(H):
        for x in range(W):
            for c in range(nf):
                cur = int(a[y, x, c])
                pred = init if (y == 0 and x == 0) else int(a[y, x - 1, c]) if y == 0 else int(a[y - 1, x, c]) if x == 0 else int(a[y, x - 1, c])
                d = (cur - pred) & 0xFFFF
                if d > 32767:
                    d -= 65536
                s = 16 if d == -32768 else abs(d).bit_length()
                put(s, 5)                                     # symbol s has code value s at length 5
                if s and s < 16:
                    put(d if d > 0 else d + (1 << s) - 1, s)
    if nbits:
        put((1 << (8 - nbits)) - 1, 8 - nbits)
    return bytes(out) + bytes(body) + b"\xff\xd9"


class Ifd:
    def __init__(self):
        self.e = []

    def add(self, tag, typ, vals):
        self.e.append((tag, typ, vals if isinstance(vals, (list, tuple)) else [vals]))


def write_dng(path, raw: np.ndarray, *, linear: bool, bits=12, tile=(64, 64), orientation=1, neutral=(0.5, 1.0, 0.6),
              fm=None, black=0, white=None, cfa=(0, 1, 1, 2), crop=None, compress=True):
    """raw: linear -> (H, W, 3) uint16; bayer -> (H, W) uint16."""
    H, W = raw.shape[:2]
    white = white or (1 << bits) - 1
    th, tw = tile
    tiles = []
    for ty in range(0, H, th):
        for tx in range(0, W, tw):
            t = np.zeros((th, tw) + raw.shape[2:], np.uint16)
            blk = raw[ty:ty + th, tx:tx + tw]
            t[:blk.shape[0], :blk.shape[1]] = blk
            if compress:
                tt = t if linear else t.reshape(th, tw // 2, 2)       # Bayer: interleaved pairs, 2 components
                tiles.append(ljpeg_encode(tt, bits))
            else:
                tiles.append(t.astype("<u2").tobytes())
    sizes = [len(t) for t in tiles]

    def ifd_bytes(ifd, base, extra):                                   # returns IFD blob; `extra` collects out-of-line data
        ents = sorted(ifd.e, key=lambda x: x[0])
        blob = struct.pack("<H", len(ents))
        for tag, typ, vals in ents:
            fmt = {1: "B", 3: "H", 4: "I", 5: "II", 9: "i", 10: "ii", 7: "B", 2: "B", 12: "d"}[typ]
            size = {1: 1, 3: 2, 4: 4, 5: 8, 9: 4, 10: 8, 7: 1, 2: 1, 12: 8}[typ]
            flat = []
            for v in vals:
                if typ in (5, 10):
                    from fractions import Fraction
                    f = Fraction(v).limit_denominator(1_000_000); flat += [f.numerator, f.denominator]
                else:
                    flat.append(v)
            data = struct.pack("<" + str(len(flat)) + fmt[0], *flat) if typ not in (5, 10) else struct.pack("<" + "I" * len(flat) if typ == 5 else "<" + "i" * len(flat), *flat)
            if len(data) <= 4:
                blob += struct.pack("<HHI", tag, typ, len(vals)) + data.ljust(4, b"\0")
            else:
                off = base + len(extra)
                extra += data + (b"\0" if len(data) % 2 else b"")
                blob += struct.pack("<HHII", tag, typ, len(vals), off)
        return blob + struct.pack("<I", 0)

    # layout: header | IFD0 | extra0 | raw IFD | extra1 | tile data
    thumb = Ifd()
    thumb.add(254, 4, 1); thumb.add(256, 4, 8); thumb.add(257, 4, 8); thumb.add(258, 3, [8, 8, 8]); thumb.add(259, 3, 1); thumb.add(262, 3, 2)
    thumb.add(273, 4, 0); thumb.add(274, 3, orientation); thumb.add(277, 3, 3); thumb.add(278, 3, 8); thumb.add(279, 4, 192)
    thumb.add(50706, 1, [1, 4, 0, 0]); thumb.add(50728, 5, list(neutral))
    cm = np.linalg.inv(XYZ50_TO_SRGB @ (fm if fm is not None else np.eye(3))) if False else None
    fmm = fm if fm is not None else SRGB_TO_XYZ50
    thumb.add(50964, 10, list(fmm.flatten())); thumb.add(50965, 10, list(fmm.flatten()))
    thumb.add(50721, 10, list(np.linalg.inv(fmm).flatten())); thumb.add(50722, 10, list(np.linalg.inv(fmm).flatten()))
    thumb.add(50778, 3, 17); thumb.add(50779, 3, 21); thumb.add(50730, 10, [0.5])
    thumb.add(330, 4, 0)
    rawi = Ifd()
    rawi.add(254, 4, 0); rawi.add(256, 4, W); rawi.add(257, 4, H)
    rawi.add(258, 3, [16, 16, 16] if linear else [16]); rawi.add(259, 3, 7 if compress else 1)
    rawi.add(262, 3, 34892 if linear else 32803); rawi.add(277, 3, 3 if linear else 1)
    rawi.add(322, 4, tw); rawi.add(323, 4, th); rawi.add(324, 4, [0] * len(tiles)); rawi.add(325, 4, sizes)
    rawi.add(50714, 3, [black] * (3 if linear else 4)); rawi.add(50717, 3, white)
    if not linear:
        rawi.add(33421, 3, [2, 2]); rawi.add(33422, 1, list(cfa)); rawi.add(50713, 3, [2, 2])
    if crop:
        rawi.add(50719, 4, [crop[0], crop[1]]); rawi.add(50720, 4, [crop[2], crop[3]])
    # two-pass sizing (offsets depend on lengths)
    def build():
        ex0, ex1 = bytearray(), bytearray()
        i0_off = 8
        # dummy pass for lengths
        b0 = ifd_bytes(thumb, 0, bytearray()); e0 = bytearray(); ifd_bytes(thumb, 0, e0)
        raw_ifd_off = i0_off + len(b0) + len(e0) + 192
        thumb_data_off = i0_off + len(b0) + len(e0)
        return i0_off, raw_ifd_off, thumb_data_off
    i0_off, raw_off, thumb_off = build()
    for t in thumb.e:
        pass
    thumb.e = [(t, ty, [thumb_off] if t == 273 else [raw_off] if t == 330 else v) for t, ty, v in thumb.e]
    ex0 = bytearray(); b0 = ifd_bytes(thumb, i0_off + 2 + 12 * len(thumb.e) + 4, ex0)
    assert i0_off + len(b0) + len(ex0) == thumb_off, (i0_off + len(b0) + len(ex0), thumb_off)
    ex1 = bytearray(); b1_probe = ifd_bytes(rawi, raw_off + 2 + 12 * len(rawi.e) + 4, ex1)
    tile_off = raw_off + len(b1_probe) + len(ex1)
    offs, o = [], tile_off
    for s in sizes:
        offs.append(o); o += s + (s % 2)
    rawi.e = [(t, ty, offs if t == 324 else v) for t, ty, v in rawi.e]
    ex1 = bytearray(); b1 = ifd_bytes(rawi, raw_off + 2 + 12 * len(rawi.e) + 4, ex1)
    out = bytearray(b"II*\0" + struct.pack("<I", i0_off)) + b0 + ex0 + bytes(192) + b1 + ex1
    assert len(out) == tile_off, (len(out), tile_off)
    for t in tiles:
        out += t + (b"\0" if len(t) % 2 else b"")
    open(path, "wb").write(bytes(out))
    return path
