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

CONV, DW, ADD, AVG, RESHAPE, FC, SOFTMAX, CONCAT, RESIZE = 3, 4, 0, 1, 22, 9, 25, 2, 23
MAXPOOL, PAD, PRELU, LOGISTIC, DEQUANTIZE = 17, 34, 54, 14, 6


def export(path: str, mean: float = 127.0, std: float = 128.0) -> dict:
    raw = open(path, "rb").read()
    try:
        labels = zipfile.ZipFile(io.BytesIO(raw)).read("labels_without_background.txt").decode().strip().split("\n")
    except Exception:   # noqa: BLE001 - segmentation models carry no label file
        labels = []
    m = tflite.Model.GetRootAsModel(raw, 0)
    sg = m.Subgraphs(0)
    blob = io.BytesIO()
    weights = {}

    def tensor(i):
        t = sg.Tensors(i)
        return t, [t.Shape(j) for j in range(t.ShapeLength())]

    deq = {}    # float16 constants that reach the graph through DEQUANTIZE ops
    for k in range(sg.OperatorsLength()):
        o_ = sg.Operators(k); c_ = m.OperatorCodes(o_.OpcodeIndex())
        if max(c_.BuiltinCode(), c_.DeprecatedBuiltinCode()) == DEQUANTIZE:
            deq[o_.Outputs(0)] = o_.Inputs(0)

    def const(i):
        src = deq.get(i, i)
        t, shape = tensor(src)
        raw_ = m.Buffers(t.Buffer()).DataAsNumpy().tobytes()
        dt = np.float16 if t.Type() == 1 else np.int32 if t.Type() == 2 else np.float32
        return np.frombuffer(raw_, dtype=dt).astype(np.float32 if dt != np.int32 else np.int32).reshape(shape), shape

    def put(i, kind):
        """store tensor i; kind 'w' = int8 per-output-channel (channel axis 0 or last for depthwise)"""
        if (i, kind) in weights:
            return weights[(i, kind)]
        data, shape = const(i)
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
        if code == DEQUANTIZE:
            continue
        ins = [op.Inputs(j) for j in range(op.InputsLength())]
        outs = [op.Outputs(j) for j in range(op.OutputsLength())]
        opts = op.BuiltinOptions()
        d = {"in": ins[0], "out": outs[0]}
        if code in (CONV, DW):
            o = tflite.Conv2DOptions() if code == CONV else tflite.DepthwiseConv2DOptions()
            o.Init(opts.Bytes, opts.Pos)
            d.update(t="conv" if code == CONV else "dw", sh=o.StrideH(), sw=o.StrideW(), pad="same" if o.Padding() == 0 else "valid",
                     act=o.FusedActivationFunction(), dh=o.DilationHFactor(), dw_=o.DilationWFactor())
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
        elif code == CONCAT:
            o = tflite.ConcatenationOptions(); o.Init(opts.Bytes, opts.Pos)
            d.update(t="concat", ins=ins, axis=o.Axis(), act=o.FusedActivationFunction())
        elif code == RESIZE:
            o = tflite.ResizeBilinearOptions(); o.Init(opts.Bytes, opts.Pos)
            d.update(t="resize", align=bool(o.AlignCorners()), half=bool(o.HalfPixelCenters()))
        elif code == PRELU:
            d.update(t="prelu", alpha=put(ins[1], "b"))
        elif code == MAXPOOL:
            o = tflite.Pool2DOptions(); o.Init(opts.Bytes, opts.Pos)
            d.update(t="maxpool", fh=o.FilterHeight(), fw=o.FilterWidth(), sh=o.StrideH(), sw=o.StrideW(), pad="same" if o.Padding() == 0 else "valid")
        elif code == PAD:
            pads, _ = const(ins[1])
            d.update(t="pad", pads=[[int(a), int(b)] for a, b in pads])
        elif code == LOGISTIC:
            d.update(t="sigmoid")
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
    return {"input": {"idx": inp, "shape": tensor(inp)[1], "mean": mean, "std": std}, "output": sg.Outputs(0), "outputs": [sg.Outputs(i) for i in range(sg.OutputsLength())], "embed": avg_out,
            "ops": ops, "labels": labels, "weights": base64.b64encode(blob.getvalue()).decode()}


if __name__ == "__main__":
    json.dump(export(sys.argv[1], *(float(a) for a in sys.argv[2:4])), sys.stdout, separators=(",", ":"))
