# -*- coding: utf-8 -*-
"""从经过来源核验、授权的类别照片训练原型；样本不足时安全拒绝。"""
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

# 旧类素材含泛篮、异地织物等，不能代表这些新类别。
# 先把每一类经来源核实、授权并在 raw/<key>/ 中准备至少 3 张真实样本，
# 再由审核者填写索引；默认留空会安全拒绝训练，不覆盖现有 images/model。
# Supply genuine, permission-cleared positive images for five categories and diverse
# out-of-scope negative images for `other`; synthetic images are never accepted.
# 已逐张目检：仅保留内容与类别相符、且许可可再分发的示意图片。
# 注意：这些是工艺示意照片（非东莞本地实物），模型只对应打印卡上的参考图。
KEEP = {
    "houjie_yuexiu": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
    "houjie_shuangshou_hongquan": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
    "aotai_aoyu_brick": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49],
    "guancao": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45],
    "qingxi_qilin_zhazuo": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
    "other": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
}
TRAINABLE_CLASSES = relic.CLASS_ORDER
MIN_REVIEWED_IMAGES_PER_CLASS = 3


def imread(path):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite(path, img):
    ext = os.path.splitext(path)[1] or ".jpg"
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return bool(ok)


# Synthetic fabric generation was intentionally removed: it is not valid class evidence.
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
    # 先完整验证所有来源图片，再写 staging 目录；缺数据时绝不清空现有训练图。
    selected = {}
    missing = []
    for cls in TRAINABLE_CLASSES:
        indices = KEEP.get(cls, [])
        files = sorted(glob.glob(os.path.join(RAW, cls, "*.*")))
        if len(indices) < MIN_REVIEWED_IMAGES_PER_CLASS:
            missing.append("%s: 需至少 %d 张经审核真实图像（other 为类外负样本），KEEP 中只有 %d" %
                           (cls, MIN_REVIEWED_IMAGES_PER_CLASS, len(indices)))
            continue
        if any(i < 0 or i >= len(files) for i in indices):
            missing.append("%s: KEEP 索引超出素材范围" % cls)
            continue
        selected[cls] = [files[i] for i in indices]
    if missing:
        raise RuntimeError("训练被安全拦截；请先补齐来源核验、授权与真实样本：\n- " + "\n- ".join(missing))

    staged_items = []
    staging = IMG + ".candidate"
    backup = IMG + ".previous"
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    try:
        for cls in TRAINABLE_CLASSES:
            folder = os.path.join(staging, cls)
            os.makedirs(folder)
            for n, src in enumerate(selected[cls]):
                img = imread(src)
                if img is None or img.size == 0:
                    raise RuntimeError("无法解码训练素材: " + src)
                dst = os.path.join(folder, "%02d.jpg" % n)
                if not imwrite(dst, img) or not os.path.isfile(dst):
                    raise RuntimeError("无法写入候选训练图: " + dst)
                staged_items.append((cls, dst, "photo"))
        if os.path.isdir(backup):
            raise RuntimeError("上一次训练备份存在，需人工检查: " + backup)
        if os.path.isdir(IMG):
            os.replace(IMG, backup)
        try:
            os.replace(staging, IMG)
        except Exception:
            if os.path.isdir(backup):
                os.replace(backup, IMG)
            raise
        if os.path.isdir(backup):
            shutil.rmtree(backup)
        return [(cls, path.replace(staging, IMG), kind)
                for cls, path, kind in staged_items]
    except Exception:
        if os.path.isdir(staging):
            shutil.rmtree(staging)
        raise


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
    # Match relic.py exactly: threshold OR margin, with a shared absolute floor.
    if best == "other" or not (best_s >= th or margin >= mar) or best_s < 0.55:
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
    th, mar = 0.80, 0.03  # same default thresholds as relic.py (values are saved to model.npz)
    if not by_image:
        raise RuntimeError("无可用训练图像；未触碰现有模型")
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

    # 写到同目录临时文件，训练异常时保留原模型；设备识别开关仍需独立验收后人工开启。
    candidate = MODEL + ".candidate.npz"
    np.savez(
        candidate,
        schema_version=np.int32(2),
        prototypes=P,
        labels=L,
        names=np.array(relic.CLASS_ORDER),
        threshold=np.float32(th),
        margin=np.float32(mar),
    )
    os.replace(candidate, MODEL)
    print("saved candidate model", MODEL, "prototypes", len(L), "LOO", "%d/%d" % (correct, total),
          "bytes", os.path.getsize(MODEL))
    print("NOTE: RELIC_RECOGNITION_ENABLED remains False until an independent test set passes.")


if __name__ == "__main__":
    main()