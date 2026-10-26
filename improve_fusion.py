# -*- coding: utf-8 -*-
"""改进：把固定除法换成加权 z 融合。

原方法：Lastde = 平均 log p / Agg-MDE
改进后：score   = z(平均 log p) + lambda * z(Agg-MDE)

数据切分（防止泄漏）：
    参考集：前 50 条人类      -> 只用来算 z 的均值和标准差
    验证集：50~100 人类 + 75 AI -> 只用来选 lambda
    测试集：100~150 人类 + 75 AI -> 只用来报告结果

用法：
    python improve_fusion.py
"""

import csv
import json
import os
import sys

import numpy as np

from lastde_repro import auroc

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "results", "lastde_results.csv")


def load():
    with open(DATA, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    humans = [r for r in rows if int(r["label"]) == 0]
    ais = [r for r in rows if int(r["label"]) == 1]
    return humans, ais


def main():
    humans, ais = load()
    ref = humans[:50]
    val = humans[50:100] + ais[:75]
    test = humans[100:] + ais[75:]

    mu_ll = np.mean([float(r["mean_ll"]) for r in ref])
    sd_ll = np.std([float(r["mean_ll"]) for r in ref]) + 1e-9
    mu_m = np.mean([float(r["aggmde"]) for r in ref])
    sd_m = np.std([float(r["aggmde"]) for r in ref]) + 1e-9

    def z(r, key, mu, sd):
        return (float(r[key]) - mu) / sd

    def score(r, lam):
        return z(r, "mean_ll", mu_ll, sd_ll) + lam * z(r, "aggmde", mu_m, sd_m)

    y_val = [int(r["label"]) for r in val]
    best_lam, best_auc = 0.0, -1.0
    for lam in np.arange(-1.5, 1.51, 0.1):
        auc = auroc([score(r, lam) for r in val], y_val)
        if auc > best_auc:
            best_lam, best_auc = float(lam), auc

    y_test = [int(r["label"]) for r in test]
    test_base = auroc([float(r["lastde"]) for r in test], y_test)
    test_ll = auroc([float(r["mean_ll"]) for r in test], y_test)
    test_fusion = auroc([score(r, best_lam) for r in test], y_test)
    full_base = auroc([float(r["lastde"]) for r in humans + ais],
                      [int(r["label"]) for r in humans + ais])

    summary = dict(lambda_=round(best_lam, 2), val_auroc=round(best_auc, 4),
                   test_baseline=round(test_base, 4), test_ll=round(test_ll, 4),
                   test_fusion=round(test_fusion, 4), full_baseline=round(full_base, 4),
                   n_ref=len(ref), n_val=len(val), n_test=len(test))
    with open(os.path.join(HERE, "results", "fusion_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("参考集 %d 条 | 验证集 %d 条 | 测试集 %d 条" % (len(ref), len(val), len(test)))
    print("验证集选出的 lambda = %.2f（验证集 AUROC %.4f）" % (best_lam, best_auc))
    print("")
    print("测试集上的对比：")
    print("  原 Lastde（除法）      %.4f" % test_base)
    print("  只用平均 log p         %.4f" % test_ll)
    print("  加权融合（我们的改进） %.4f" % test_fusion)
    print("")
    print("全量 300 条的原始基线：%.4f（参考）" % full_base)
    print("结果写入 results/fusion_summary.json")


if __name__ == "__main__":
    main()
