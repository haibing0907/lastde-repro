# -*- coding: utf-8 -*-
"""短文本改进试验：把 DE 的超参数按长度调小（s=2, tau 更少）。"""

import json
import os
import sys

import numpy as np

from lastde_repro import load_model, token_logprobs, aggmde, auroc

DATA = r"D:\Lastde_Detector\datasets\human_llm_data_for_experiment\xsum_gpt2_xl.raw_data.json"


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    items = [(t, 0) for t in d["original"]] + [(t, 1) for t in d["sampled"]]

    tok, model = load_model("gpt2")
    cache = []
    for i, (text, y) in enumerate(items):
        lp = token_logprobs(text, tok, model, 64)
        if lp.size >= 10:
            cache.append((lp, y))
        if (i + 1) % 100 == 0:
            print("done", i + 1)

    y = [c[1] for c in cache]
    for s, tau in [(3, 5), (3, 3), (2, 5), (2, 4), (2, 3)]:
        scores = []
        for lp, _ in cache:
            a = aggmde(lp, s=s, tau_max=tau)
            scores.append(float(lp.mean()) / (a + 1e-6))
        print("s=%d tau=%d  AUROC %.4f" % (s, tau, auroc(scores, y)))


if __name__ == "__main__":
    main()
