"""Convert Google's EfficientNet-Lite0 (ImageNet, Apache-2.0, via MediaPipe) into a compact blob
that the browser build runs in pure JavaScript.

    python scripts/export_vision_model.py effnet_f32.tflite > browser/vision_model.json

Weights are stored as per-output-channel int8 (4.7 MB) and dequantised on load."""
import base64
import io
import json
import sys
import zipfile

import numpy as np
import tflite

CONV, DW, ADD, AVG, RESHAPE, FC, SOFTMAX = 3, 4, 0, 1, 22, 9, 25


def export(path: str) -> dict:
    raw = open(path, "rb").read()
    labels = zipfile.ZipFile(io.BytesIO(raw)).read("labels_without_background.txt").decode().strip().split("\n")
    m = tflite.Model.GetRootAsModel(raw, 0)
    sg = m.Subgraphs(0)
    blob = io.BytesIO()
    weights = {}

    def tensor(i):
        t = sg.Tensors(i)
        return t, [t.Shape(j) for j in range(t.ShapeLength())]

    def put(i, kind):
        """store tensor i; kind 'w' = int8 per-output-channel (channel axis 0 or last for depthwise)"""
        if (i, kind) in weights:
            return weights[(i, kind)]
        t, shape = tensor(i)
        data = np.frombuffer(m.Buffers(t.Buffer()).DataAsNumpy().tobytes(), dtype=np.float32).reshape(shape)
        if kind == "w":
            axis = 3 if shape[0] == 1 and len(shape) == 4 and shape[3] > 1 and shape[1] > 1 and kind == "w" and False else 0
        entry = {"shape": shape, "off": blob.tell()}
        if kind == "b":
            blob.write(data.astype("<f4").tobytes())
            entry["kind"] = "f32"
        else:
            ch_axis = entry["axis"] = 3 if kind == "dw" else 0
            flat = np.moveaxis(data, ch_axis, 0).reshape(shape[ch_axis], -1)
            scale = np.maximum(np.abs(flat).max(axis=1), 1e-12) / 127.0
            q = np.clip(np.round(flat / scale[:, None]), -127, 127).astype(np.int8)
            blob.write(q.tobytes())
            entry["scale_off"] = blob.tell()
            blob.write(scale.astype("<f4").tobytes())
            entry["kind"] = "i8"
        weights[(i, kind)] = entry
        return entry

    codes = {m.OperatorCodes(i).BuiltinCode() or m.OperatorCodes(i).DeprecatedBuiltinCode(): i for i in range(m.OperatorCodesLength())}
    ops, wlist = [], []
    avg_out = None
    for k in range(sg.OperatorsLength()):
        op = sg.Operators(k)
        oc = m.OperatorCodes(op.OpcodeIndex())
        code = max(oc.BuiltinCode(), oc.DeprecatedBuiltinCode())
        ins = [op.Inputs(j) for j in range(op.InputsLength())]
        outs = [op.Outputs(j) for j in range(op.OutputsLength())]
        opts = op.BuiltinOptions()
        d = {"in": ins[0], "out": outs[0]}
        if code in (CONV, DW):
            o = tflite.Conv2DOptions() if code == CONV else tflite.DepthwiseConv2DOptions()
            o.Init(opts.Bytes, opts.Pos)
            assert o.DilationHFactor() == 1 and o.DilationWFactor() == 1
            d.update(t="conv" if code == CONV else "dw", sh=o.StrideH(), sw=o.StrideW(), pad="same" if o.Padding() == 0 else "valid",
                     act=o.FusedActivationFunction())
            d["w"] = put(ins[1], "w" if code == CONV else "dw")
            d["b"] = put(ins[2], "b")
            if code == DW:
                assert o.DepthMultiplier() == 1
        elif code == ADD:
            o = tflite.AddOptions(); o.Init(opts.Bytes, opts.Pos)
            d.update(t="add", in2=ins[1], act=o.FusedActivationFunction())
        elif code == AVG:
            o = tflite.Pool2DOptions(); o.Init(opts.Bytes, opts.Pos)
            d.update(t="avg", fh=o.FilterHeight(), fw=o.FilterWidth(), sh=o.StrideH(), sw=o.StrideW(), pad="same" if o.Padding() == 0 else "valid")
            avg_out = outs[0]
        elif code == RESHAPE:
            d.update(t="reshape")
        elif code == FC:
            d.update(t="fc", w=put(ins[1], "w"), b=put(ins[2], "b"))
        elif code == SOFTMAX:
            d.update(t="softmax")
        else:
            raise SystemExit(f"unsupported op {code}")
        d["shape"] = tensor(outs[0])[1]
        ops.append(d)
    inp = sg.Inputs(0)
    return {"input": {"idx": inp, "shape": tensor(inp)[1], "mean": 127.0, "std": 128.0}, "output": sg.Outputs(0), "embed": avg_out,
            "ops": ops, "labels": labels, "weights": base64.b64encode(blob.getvalue()).decode()}


if __name__ == "__main__":
    json.dump(export(sys.argv[1]), sys.stdout, separators=(",", ":"))
