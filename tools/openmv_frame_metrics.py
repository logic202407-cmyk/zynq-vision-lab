"""Host-side scoring for OpenMV stage-2 frames (orientation + focus).

Works on the camera's own JPEG frames, not on IDE screenshots, so the numbers
describe the sensor path rather than the IDE renderer.

Modes
-----
pair          compare two frames: is ``b`` the 180 degree rotation of ``a``?
group         per-frame focus scores for a sweep directory
selftest      blur a frame on purpose and show the focus metric responding

Metrics
-------
laplacian_var : variance of the 4-neighbour Laplacian of the luma plane
tenengrad     : mean squared Sobel gradient magnitude
mse/mae       : pixel difference, used for the orientation comparison

The orientation comparison is the load-bearing one: if
``mse(b, rot180(a))`` sits at the run-to-run noise floor while ``mse(a, b)`` is
one to two orders of magnitude larger, then the flip flags really do produce an
exact 180 degree rotation and the correction is safe to adopt.  A rotated
cross-hair proves nothing on its own because a centred cross is rotationally
invariant -- a real scene or a bearing target is required.

Usage
-----
python openmv_frame_metrics.py pair --a A_0.jpg --b B_0.jpg --json out.json
python openmv_frame_metrics.py group --dir ./frames --roi 96,56,128,128
python openmv_frame_metrics.py selftest --image A_0.jpg
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

DEFAULT_ROI = (96, 56, 128, 128)


def load_rgb(path, roi=None):
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    if roi is not None:
        x, y, w, h = roi
        arr = arr[y:y + h, x:x + w]
    return arr


def luma_of(rgb):
    return 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]


def laplacian_var(luma):
    from numpy.lib.stride_tricks import sliding_window_view

    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    lap = (sliding_window_view(luma, (3, 3)) * k).sum(axis=(-1, -2))
    return float(lap.var())


def tenengrad(luma):
    gx = np.zeros_like(luma)
    gy = np.zeros_like(luma)
    gx[:, 1:-1] = luma[:, 2:] - luma[:, :-2]
    gy[1:-1, :] = luma[2:, :] - luma[:-2, :]
    return float(np.mean(gx * gx + gy * gy))


def frame_metrics(path, roi):
    rgb = load_rgb(path, roi)
    luma = luma_of(rgb)
    saturated = float(np.mean(np.all(rgb >= 250, axis=2))) * 100.0
    return {
        "file": os.path.basename(path),
        "roi": list(roi),
        "laplacian_var": round(laplacian_var(luma), 3),
        "tenengrad": round(tenengrad(luma), 3),
        "luma_mean": round(float(luma.mean()), 3),
        "luma_stdev": round(float(luma.std()), 3),
        "luma_min": round(float(luma.min()), 1),
        "luma_max": round(float(luma.max()), 1),
        "saturated_pct": round(saturated, 3),
    }


def compare(a_path, b_path, roi):
    ra, rb = load_rgb(a_path, roi), load_rgb(b_path, roi)
    if ra.shape != rb.shape:
        return {"error": "shape mismatch %s vs %s" % (ra.shape, rb.shape)}
    same = ra - rb
    rot = ra - rb[::-1, ::-1, :]
    return {
        "a": os.path.basename(a_path),
        "b": os.path.basename(b_path),
        "mse_as_is": round(float(np.mean(same ** 2)), 3),
        "mse_b_vs_rot180_a": round(float(np.mean(rot ** 2)), 3),
        "mae_as_is": round(float(np.mean(np.abs(same))), 3),
        "mae_b_vs_rot180_a": round(float(np.mean(np.abs(rot))), 3),
    }


def selftest(image_path, roi):
    from PIL import ImageFilter

    out = {}
    for radius in (0.0, 1.0, 2.0, 3.0):
        im = Image.open(image_path).convert("RGB")
        if radius:
            im = im.filter(ImageFilter.GaussianBlur(radius))
        arr = np.asarray(im, dtype=np.float64)
        x, y, w, h = roi
        luma = luma_of(arr[y:y + h, x:x + w])
        out["blur_%.1f" % radius] = {
            "laplacian_var": round(laplacian_var(luma), 3),
            "tenengrad": round(tenengrad(luma), 3),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pair", "group", "selftest"])
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--dir")
    ap.add_argument("--image")
    ap.add_argument("--roi", default="%d,%d,%d,%d" % DEFAULT_ROI)
    ap.add_argument("--json")
    args = ap.parse_args()
    roi = tuple(int(v) for v in args.roi.split(","))

    if args.mode == "pair":
        out = {"pair": compare(args.a, args.b, roi),
               "metrics_a": frame_metrics(args.a, roi),
               "metrics_b": frame_metrics(args.b, roi)}
    elif args.mode == "group":
        files = sorted(glob.glob(os.path.join(args.dir, "*.jpg")))
        out = {"frames": [frame_metrics(f, roi) for f in files]}
    else:
        out = {"selftest": selftest(args.image, roi)}

    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())