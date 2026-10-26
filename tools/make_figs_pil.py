# -*- coding: utf-8 -*-
"""用 Pillow 画两张配图（当前环境 matplotlib 保存图片会崩溃）。

输出：
    prob_curves.png          人类 vs AI 的 token 对数概率曲线
    lastde_distribution.png  两类文本的 Lastde 分数分布
"""

import csv
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lastde_repro import load_model, token_logprobs, auroc  # noqa: E402

DATA = r"D:\Lastde_Detector\datasets\human_llm_data_for_experiment\xsum_gpt2_xl.raw_data.json"
NAVY = (31, 56, 100)
ORANGE = (197, 90, 17)
GRAY = (89, 89, 89)
LIGHT = (225, 225, 225)
WHITE = (255, 255, 255)


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = os.path.join(r"C:\Windows\Fonts", name)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def line_chart(lp_h, lp_a, out, n=120):
    W, H = 1800, 820
    left, right, top, bottom = 150, 60, 110, 100
    plot_w = W - left - right
    plot_h = H - top - bottom

    n = min(n, len(lp_h), len(lp_a))
    hs = [float(x) for x in lp_h[:n]]
    as_ = [float(x) for x in lp_a[:n]]
    vmin = min(min(hs), min(as_))
    vmax = max(max(hs), max(as_))
    pad = (vmax - vmin) * 0.08 + 0.05
    vmin -= pad
    vmax += pad

    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # grid + y ticks
    for k in range(6):
        v = vmin + (vmax - vmin) * k / 5
        y = top + plot_h - (v - vmin) / (vmax - vmin) * plot_h
        d.line([(left, y), (left + plot_w, y)], fill=LIGHT, width=1)
        d.text((20, y - 12), "%.1f" % v, font=font(24), fill=GRAY)

    # axes
    d.line([(left, top), (left, top + plot_h)], fill=GRAY, width=2)
    d.line([(left, top + plot_h), (left + plot_w, top + plot_h)], fill=GRAY, width=2)

    # x ticks
    for i in range(0, n, 20):
        x = left + i / max(n - 1, 1) * plot_w
        d.text((x - 12, top + plot_h + 12), str(i), font=font(22), fill=GRAY)

    def to_px(i, v):
        x = left + i / max(n - 1, 1) * plot_w
        y = top + plot_h - (v - vmin) / (vmax - vmin) * plot_h
        return (x, y)

    for series, color in ((hs, NAVY), (as_, ORANGE)):
        pts = [to_px(i, v) for i, v in enumerate(series)]
        d.line(pts, fill=color, width=3, joint="curve")

    # legend
    lx, ly = left + plot_w - 320, top + 10
    d.rectangle([lx - 18, ly - 14, lx + 310, ly + 84], fill=WHITE, outline=LIGHT)
    d.line([(lx, ly + 16), (lx + 50, ly + 16)], fill=NAVY, width=5)
    d.text((lx + 62, ly), "human", font=font(28, True), fill=NAVY)
    d.line([(lx, ly + 56), (lx + 50, ly + 56)], fill=ORANGE, width=5)
    d.text((lx + 62, ly + 40), "AI", font=font(28, True), fill=ORANGE)

    d.text((left, 30), "Token probability sequences (XSum, GPT-2 scoring)",
           font=font(36, True), fill=NAVY)
    d.text((left, top + plot_h + 55), "token position", font=font(24), fill=GRAY)
    d.text((left + plot_w - 210, top + plot_h + 55), "log probability", font=font(24), fill=GRAY)

    img.save(out)
    print("saved", out)


def distribution_chart(out):
    path = os.path.join(HERE, "lastde_results.csv")
    if not os.path.exists(path):
        print("no csv, skip distribution")
        return
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    labels = [int(r["label"]) for r in rows]
    scores = np.array([float(r["lastde"]) for r in rows])
    auc = auroc(list(scores), labels)

    W, H = 1500, 820
    left, right, top, bottom = 130, 60, 110, 110
    plot_w = W - left - right
    plot_h = H - top - bottom

    lo, hi = float(scores.min()), float(scores.max())
    nb = 25
    edges = [lo + (hi - lo) * k / nb for k in range(nb + 1)]
    hc = [0] * nb
    ac = [0] * nb
    for s, l in zip(scores, labels):
        idx = min(nb - 1, max(0, int((s - lo) / max(hi - lo, 1e-9) * nb)))
        (hc if l == 0 else ac)[idx] += 1
    ymax = max(max(hc), max(ac)) * 1.18 + 1

    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    for k in range(6):
        v = ymax * k / 5
        y = top + plot_h - v / ymax * plot_h
        d.line([(left, y), (left + plot_w, y)], fill=LIGHT, width=1)
        d.text((30, y - 12), "%d" % round(v), font=font(22), fill=GRAY)

    d.line([(left, top), (left, top + plot_h)], fill=GRAY, width=2)
    d.line([(left, top + plot_h), (left + plot_w, top + plot_h)], fill=GRAY, width=2)

    bw = plot_w / nb
    for i in range(nb):
        x0 = left + i * bw
        for counts, color, side in ((hc, NAVY, 0), (ac, ORANGE, 1)):
            bh = counts[i] / ymax * plot_h
            w2 = bw / 2 - 1
            xx = x0 + (0 if side == 0 else bw / 2)
            d.rectangle([xx + 0.5, top + plot_h - bh, xx + w2, top + plot_h], fill=color)

    for i in range(0, nb + 1, 5):
        x = left + i * bw
        d.text((x - 18, top + plot_h + 12), "%.0f" % edges[i], font=font(20), fill=GRAY)

    lx, ly = left + plot_w - 330, top + 10
    d.rectangle([lx, ly + 6, lx + 34, ly + 26], fill=NAVY)
    d.text((lx + 46, ly), "human", font=font(26, True), fill=NAVY)
    d.rectangle([lx, ly + 46, lx + 34, ly + 66], fill=ORANGE)
    d.text((lx + 46, ly + 40), "AI", font=font(26, True), fill=ORANGE)

    d.text((left, 30), "Lastde score distribution (AUROC=%.3f)" % auc,
           font=font(34, True), fill=NAVY)
    d.text((left, top + plot_h + 55), "Lastde score", font=font(22), fill=GRAY)
    d.text((left + plot_w - 120, top + plot_h + 55), "count", font=font(22), fill=GRAY)

    img.save(out)
    print("saved", out, "AUROC=%.4f" % auc)


def main():
    distribution_chart(os.path.join(HERE, "lastde_distribution.png"))
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    human, ai = data["original"][0], data["sampled"][0]
    tok, model = load_model("gpt2")
    lp_h = token_logprobs(human, tok, model, 200)
    lp_a = token_logprobs(ai, tok, model, 200)
    print("human mean logp %.3f, AI mean logp %.3f" % (lp_h.mean(), lp_a.mean()))
    line_chart(lp_h, lp_a, os.path.join(HERE, "prob_curves.png"))


if __name__ == "__main__":
    import numpy as np
    main()
