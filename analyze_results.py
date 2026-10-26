# -*- coding: utf-8 -*-
"""读 lastde_results.csv，输出三个 AUROC（消融实验用）。

用法：
    python analyze_results.py lastde_results.csv
"""

import csv
import sys

from lastde_repro import auroc

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "lastde_results.csv"
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    labels = [int(r["label"]) for r in rows]
    lastde = [float(r["lastde"]) for r in rows]
    mean_ll = [float(r["mean_ll"]) for r in rows]
    aggmde = [float(r["aggmde"]) for r in rows]

    print("样本数：%d（人类 %d / AI %d）"
          % (len(rows), labels.count(0), labels.count(1)))
    print("")
    print("Lastde（LL / Agg-MDE） : %.4f" % auroc(lastde, labels))
    print("只用 LL（Likelihood）   : %.4f" % auroc(mean_ll, labels))
    print("只用 Agg-MDE           : %.4f" % auroc([-x for x in aggmde], labels))
    print("")
    print("说明：Agg-MDE 越小越像 AI，所以这里取了负号，让它和另外两个同方向。")


if __name__ == "__main__":
    main()
