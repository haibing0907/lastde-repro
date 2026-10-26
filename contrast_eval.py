# -*- coding: utf-8 -*-
"""改进点 2 试验：对比式 DE（DE_real - DE_shuffle）。"""

import json
import os
import sys

import numpy as np

from lastde_repro import load_model, token_logprobs, aggmde, auroc

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"D:\Lastde_Detector\datasets\human_llm_data_for_experiment\xsum_gpt2_xl.raw_data.json"


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    items = [(t, 0) for t in d["original"]] + [(t, 1) for t in d["sampled"]]

    tok, model = load_model("gpt2")
    rng = np.random.RandomState(0)

    rows = []
    for i, (text, y) in enumerate(items):
        lp = token_logprobs(text, tok, model, 256)
        if lp.size < 30:
            continue
        real = aggmde(lp)
        base = np.mean([aggmde(rng.permutation(lp)) for _ in range(5)])
        rows.append(dict(y=y, ll=float(lp.mean()), mde=real, contrast=real - base))
        if (i + 1) % 50 == 0:
            print("done", i + 1)

    y = [r["y"] for r in rows]
    ll = [r["ll"] for r in rows]
    mde = [r["mde"] for r in rows]
    con = [r["contrast"] for r in rows]
    eps = 1e-6

    print("n", len(rows))
    print("human mde %.4f  AI mde %.4f" % (np.mean([r["mde"] for r in rows if r["y"] == 0]),
                                           np.mean([r["mde"] for r in rows if r["y"] == 1])))
    print("human contrast %.4f  AI contrast %.4f" % (np.mean([r["contrast"] for r in rows if r["y"] == 0]),
                                                     np.mean([r["contrast"] for r in rows if r["y"] == 1])))
    print("AUROC baseline (ll/mde)      %.4f" % auroc([a / (b + eps) for a, b in zip(ll, mde)], y))
    print("AUROC contrast score (ll/con) %.4f" % auroc([a / (b + eps) if b > 0 else -1e9 for a, b in zip(ll, con)], y))
    print("AUROC contrast alone (-con)  %.4f" % auroc([-c for c in con], y))


if __name__ == "__main__":
    main()
