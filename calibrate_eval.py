# -*- coding: utf-8 -*-
"""改进点 1：长度分桶校准（length-adaptive calibration）。

做法：
1. 把 64 / 128 / 256 三组结果合并；
2. 每个长度桶里，取前 50 条人类文本当“参考集”，算分数的均值和标准差；
3. 其余样本的分数做 z 标准化：z = (score - mu) / sd；
4. 比较“原始分数”和“校准后 z 分数”的 AUROC。

用法：
    python calibrate_eval.py
"""

import csv
import os
import sys

import numpy as np

from lastde_repro import auroc

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = [(64, "r_len64.csv"), (128, "r_len128.csv"), (256, "r_len256.csv")]


def load(tag, name):
    path = os.path.join(HERE, "results", name)
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            yield dict(tag=tag, y=int(r["label"]), score=float(r["lastde"]))


def main():
    rows = []
    for tag, name in FILES:
        rows.extend(load(tag, name))

    test = []
    for tag, _ in FILES:
        sub = [r for r in rows if r["tag"] == tag]
        humans = [r for r in sub if r["y"] == 0]
        ais = [r for r in sub if r["y"] == 1]
        ref, rest_humans = humans[:50], humans[50:]
        mu = np.mean([r["score"] for r in ref])
        sd = np.std([r["score"] for r in ref]) + 1e-9
        for r in rest_humans + ais:
            r2 = dict(r)
            r2["z"] = (r["score"] - mu) / sd
            test.append(r2)

    y = [r["y"] for r in test]
    print("bucket   n_test   raw_AUROC   z_AUROC")
    for tag, _ in FILES:
        sub = [r for r in test if r["tag"] == tag]
        print("%6d   %6d   %.4f      %.4f" % (
            tag, len(sub),
            auroc([r["score"] for r in sub], [r["y"] for r in sub]),
            auroc([r["z"] for r in sub], [r["y"] for r in sub])))
    print("%6s   %6d   %.4f      %.4f" % (
        "pooled", len(test),
        auroc([r["score"] for r in test], y),
        auroc([r["z"] for r in test], y)))
    print("\n说明：桶内 AUROC 不变（z 只是线性变换）；")
    print("提升来自混合长度时去掉了“长度造成的分数偏移”。")


if __name__ == "__main__":
    main()
