# -*- coding: utf-8 -*-
"""从 Wikimedia 筛过的照片训练火眼金睛原型，并做留一验证。"""
import glob
import os
import shutil
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(APP, "..", "..", "02_数据", "relics"))
RAW = os.path.join(ROOT, "raw")
IMG = os.path.join(ROOT, "images")
MODEL = os.path.join(ROOT, "model.npz")
sys.path.insert(0, APP)
import relic

KEEP = {
    "xiangyunsha": [0],
    "guancao": [0, 1, 2, 5, 7],
    "qianjiaodeng": [0, 1, 9],
    "other": [0, 1, 2, 6],
}


def imread(path):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite(path, img):
    ext = os.path.splitext(path)[1] or ".jpg"
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)


def make_silk(kind, rng):
    h, w = 320, 320
    yy = np.linspace(0, 1, h)[:, None]
    xx = np.linspace(0, 1, w)[None, :]
    if kind == "black":
        base = np.array([26, 28, 24], np.float32)
        sheen = (18 + 10 * np.sin(yy * 18 + rng.uniform(0, 3)))[..., None]
        img = base + sheen + rng.normal(0, 6, (h, w, 1))
    elif kind == "brown":
        base = np.array([42, 68, 108], np.float32)
        band = (12 * np.sin(xx * 40))[..., None]
        img = base + band + rng.normal(0, 7, (h, w, 1))
    else:
        img = np.zeros((h, w, 3), np.float32)
        img[:] = (70, 90, 140)
        for i in range(8):
            y0 = 10 + i * 38
            img[y0:y0 + 22] = (55, 70, 120)
        img += rng.normal(0, 8, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def augment(img, rng):
    out = [img]
    out.append(cv2.flip(img, 1))
    for alpha in (0.75, 1.2):
        out.append(np.clip(img.astype(np.float32) * alpha, 0, 255).astype(np.uint8))
    h, w = img.shape[:2]
    for keep in (0.62, 0.84):
        dh, dw = int(h * (1 - keep) / 2), int(w * (1 - keep) / 2)
        crop = img[dh:h - max(dh, 1), dw:w - max(dw, 1)]
        if crop.size:
            out.append(crop)
    return out


def prepare_images():
    if os.path.isdir(IMG):
        shutil.rmtree(IMG)
    os.makedirs(IMG)
    items = []
    for cls, idxs in KEEP.items():
        files = sorted(glob.glob(os.path.join(RAW, cls, "*.*")))
        folder = os.path.join(IMG, cls)
        os.makedirs(folder)
        for n, i in enumerate(idxs):
            if i >= len(files):
                continue
            dst = os.path.join(folder, "%02d.jpg" % n)
            img = imread(files[i])
            imwrite(dst, img)
            items.append((cls, dst, "photo"))
    rng = np.random.RandomState(7)
    folder = os.path.join(IMG, "xiangyunsha")
    for n, kind in enumerate(("black", "black", "brown", "field")):
        dst = os.path.join(folder, "syn_%s_%d.jpg" % (kind, n))
        imwrite(dst, make_silk(kind, rng))
        items.append(("xiangyunsha", dst, "synth"))
    return items


def feats_of(path):
    img = imread(path)
    rng = np.random.RandomState(abs(hash(path)) % (2 ** 31))
    vecs = []
    for aug in augment(img, rng):
        vec, ratios = relic.embed(aug)
        vecs.append((vec, ratios))
    return vecs


def score_vec(vec, ratios, prototypes, labels):
    sims = prototypes.dot(vec)
    score = {}
    for i, name in enumerate(relic.CLASS_ORDER):
        sel = sims[labels == i]
        if sel.size == 0:
            score[name] = -1.0
            continue
        score[name] = float(np.sort(sel)[-3:].mean())
    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    best, best_s = ranked[0]
    second = ranked[1][1]
    return best, best_s, best_s - second, ratios


def predict_with(best, best_s, margin, ratios, th, mar):
    if best == "other" or best_s < th or margin < mar:
        return "other"
    if not relic.gate(best, ratios):
        return "other"
    return best


def main():
    items = prepare_images()
    by_image = []
    for cls, path, kind in items:
        vecs = feats_of(path)
        by_image.append({"cls": cls, "path": path, "kind": kind, "vecs": vecs})
        print("img", cls, kind, os.path.basename(path), "augs", len(vecs))

    def pack(rows):
        prototypes, labels = [], []
        for row in rows:
            for vec, _ in row["vecs"]:
                prototypes.append(vec)
                labels.append(relic.CLASS_ORDER.index(row["cls"]))
        return np.stack(prototypes).astype(np.float32), np.array(labels, np.int32)

    # 留一：每张真实照片拿出去，看原图（不看增强）能不能认对
    correct = 0
    total = 0
    th, mar = 0.80, 0.03
    print("--- leave one photo out ---")
    for i, row in enumerate(by_image):
        if row["kind"] != "photo":
            continue
        train = [r for j, r in enumerate(by_image) if j != i]
        P, L = pack(train)
        vec, ratios = row["vecs"][0]
        best, best_s, margin, ratios = score_vec(vec, ratios, P, L)
        pred = predict_with(best, best_s, margin, ratios, th, mar)
        ok = pred == row["cls"]
        correct += int(ok)
        total += 1
        print(("OK " if ok else "MISS"), row["cls"], "->", pred, "s=%.3f m=%.3f" % (best_s, margin), os.path.basename(row["path"]))
    print("LOO %d/%d" % (correct, total))

    P, L = pack(by_image)
    # 用全体模型看每张原图，挑一个不乱报的阈值
    print("--- full model on originals ---")
    for row in by_image:
        vec, ratios = row["vecs"][0]
        best, best_s, margin, ratios = score_vec(vec, ratios, P, L)
        pred = predict_with(best, best_s, margin, ratios, th, mar)
        print(row["cls"], "->", pred, "best", best, "s=%.3f m=%.3f" % (best_s, margin))

    np.savez(
        MODEL,
        prototypes=P,
        labels=L,
        names=np.array(relic.CLASS_ORDER),
        threshold=np.float32(th),
        margin=np.float32(mar),
    )
    print("saved", MODEL, "prototypes", len(L), "bytes", os.path.getsize(MODEL))


if __name__ == "__main__":
    main()