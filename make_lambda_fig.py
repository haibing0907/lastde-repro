# -*- coding: utf-8 -*-
"""画 lambda 扫描曲线：验证集 AUROC 随 lambda 变化。"""

import csv
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lastde_repro import auroc

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "results", "lastde_results.csv")
OUT = os.path.join(HERE, "figures", "lambda_curve.png")


def main():
    rows = list(csv.DictReader(open(DATA, encoding="utf-8-sig")))
    H = [r for r in rows if int(r["label"]) == 0]
    A = [r for r in rows if int(r["label"]) == 1]
    ref, val = H[:50], H[50:100] + A[:75]
    mu_ll = np.mean([float(r["mean_ll"]) for r in ref])
    sd_ll = np.std([float(r["mean_ll"]) for r in ref])
    mu_m = np.mean([float(r["aggmde"]) for r in ref])
    sd_m = np.std([float(r["aggmde"]) for r in ref])
    yv = [int(r["label"]) for r in val]

    lams = np.arange(-1.5, 1.51, 0.1)
    aucs = []
    for lam in lams:
        s = [((float(r["mean_ll"]) - mu_ll) / sd_ll) + lam * ((float(r["aggmde"]) - mu_m) / sd_m)
             for r in val]
        aucs.append(auroc(s, yv))
    aucs = np.array(aucs)

    W, Hh = 900, 470
    img = Image.new("RGB", (W, Hh), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)

    L, R, T, B = 90, 860, 40, 380
    lo, hi = 0.5, 1.0

    def px(x):
        return L + (x - lams[0]) / (lams[-1] - lams[0]) * (R - L)

    def py(y):
        return B - (y - lo) / (hi - lo) * (B - T)

    for g in np.arange(0.5, 1.01, 0.1):
        d.line([(L, py(g)), (R, py(g))], fill=(225, 225, 225))
        d.text((L - 45, py(g) - 9), "%.1f" % g, font=small, fill=(90, 90, 90))
    for g in np.arange(-1.5, 1.6, 0.5):
        d.line([(px(g), T), (px(g), B)], fill=(240, 240, 240))
        d.text((px(g) - 14, B + 8), "%.1f" % g, font=small, fill=(90, 90, 90))

    d.line([(L, T), (L, B)], fill=(60, 60, 60), width=2)
    d.line([(L, B), (R, B)], fill=(60, 60, 60), width=2)
    d.text((R - 70, B + 32), "λ", font=font, fill=(60, 60, 60))
    d.text((L - 55, T - 32), "验证集 AUROC", font=small, fill=(60, 60, 60))

    pts = [(px(x), py(y)) for x, y in zip(lams, aucs)]
    d.line(pts, fill=(46, 117, 182), width=3)
    for p in pts:
        d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=(46, 117, 182))

    i = int(np.argmax(aucs))
    bx, by = px(lams[i]), py(aucs[i])
    d.line([(bx, by), (bx, B)], fill=(197, 90, 17), width=2)
    d.ellipse([bx - 7, by - 7, bx + 7, by + 7], fill=(197, 90, 17))
    d.text((bx + 10, by - 34), "λ=0.6  AUROC=0.934", font=font, fill=(197, 90, 17))

    img.save(OUT)
    print("saved", OUT, "best", lams[i], aucs[i])


if __name__ == "__main__":
    main()
