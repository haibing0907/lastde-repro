# -*- coding: utf-8 -*-
"""Lastde 复现（一步到位版）

用论文作者公开的数据 + GPT-2 + CPU，复现论文的核心指标 AUROC。

它会做三件事：
1. 读论文自带的数据（人类文本 original / AI 文本 sampled）
2. 用 GPT-2 算每段文本的 token 对数概率
3. 算两个分数并比较：
   - Lastde        = 平均对数似然 / Agg-MDE   （论文方法）
   - Likelihood    = 平均对数似然             （最简单的基线）

用法：
    python lastde_repro.py --data xsum_gpt2_xl
    python lastde_repro.py --data reddit_gpt2_xl --model distilgpt2

数据默认从 D:\\Lastde_Detector\\datasets\\human_llm_data_for_experiment 读取。
"""

import argparse
import csv
import json
import os
import sys

import numpy as np

DEFAULT_DATA_DIR = r"D:\Lastde_Detector\datasets\human_llm_data_for_experiment"
FIG_DIR = "figures" if os.path.isdir("figures") else "."


# ---------------------------------------------------------------- AUROC

def auroc(scores, labels):
    """0.5 = 瞎猜，1.0 = 完美。labels: 1 = AI, 0 = 人类。"""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=int)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")

    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    sorted_v = allv[order]

    ranks_sorted = np.empty(len(allv), dtype=np.float64)
    i = 0
    while i < len(sorted_v):
        j = i
        while j + 1 < len(sorted_v) and sorted_v[j + 1] == sorted_v[i]:
            j += 1
        ranks_sorted[i:j + 1] = (i + j) / 2.0 + 1.0
        i = j + 1

    ranks = np.empty(len(allv), dtype=np.float64)
    ranks[order] = ranks_sorted
    sum_pos = ranks[:len(pos)].sum()
    return float((sum_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg)))


# ---------------------------------------------------------------- 模型

_MODEL = {}


def load_model(name):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    if name not in _MODEL:
        print("[模型] 加载 %s（第一次会自动下载）..." % name)
        tok = AutoTokenizer.from_pretrained(name)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(name)
        model.eval()
        _MODEL[name] = (tok, model)
        print("[模型] 完成")
    return _MODEL[name]


def token_logprobs(text, tok, model, max_tokens=256):
    import torch

    ids = tok(text, return_tensors="pt", truncation=True, max_length=max_tokens).input_ids
    if ids.shape[1] < 10:
        return np.zeros(0, dtype=np.float64)

    with torch.no_grad():
        logits = model(ids).logits
    logp = torch.log_softmax(logits[:, :-1, :], dim=-1)
    picked = logp.gather(2, ids[:, 1:].unsqueeze(-1)).squeeze(-1).squeeze(0)
    return picked.numpy().astype(np.float64)


# ---------------------------------------------------------------- Lastde 的 MDE

def _cosine_adjacent(x, s):
    """相邻两个长度为 s 的窗口的余弦相似度。"""
    from numpy.lib.stride_tricks import sliding_window_view

    if len(x) < s + 2:
        return np.zeros(0)
    w = sliding_window_view(np.asarray(x, dtype=np.float64), s)
    a, b = w[:-1], w[1:]
    na = np.linalg.norm(a, axis=1)
    nb = np.linalg.norm(b, axis=1)
    denom = na * nb
    out = np.zeros(len(a))
    ok = denom > 1e-12
    out[ok] = (a[ok] * b[ok]).sum(axis=1) / denom[ok]
    return out


def _de(x, s, bins):
    """一个尺度上的多样性熵（范围 0~1）。"""
    sims = _cosine_adjacent(x, s)
    if sims.size < 5:
        return 0.0
    hist, _ = np.histogram(sims, bins=bins, range=(-1.0, 1.0))
    total = hist.sum()
    if total == 0:
        return 0.0
    p = hist[hist > 0].astype(np.float64) / total
    return float(-(p * np.log(p)).sum() / np.log(bins))


def aggmde(x, s=3, eps_mult=10, tau_max=5):
    """多尺度多样性熵，跨尺度取标准差（论文默认聚合方式）。"""
    n = len(x)
    if n < s + 6:
        return 0.0
    bins = max(10, int(eps_mult * n))
    vals = []
    for tau in range(1, tau_max + 1):
        if n - tau < s + 2:
            continue
        pooled = np.convolve(x, np.ones(tau) / tau, mode="valid")
        vals.append(_de(pooled, s, bins))
    if len(vals) < 2:
        return 0.0
    return float(np.std(vals, ddof=1))


# ---------------------------------------------------------------- 数据

def load_pairs(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data["original"]), list(data["sampled"])


# ---------------------------------------------------------------- 主流程

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="xsum_gpt2_xl", help="数据文件名（不含 .raw_data.json）")
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--model", default="gpt2")
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--out", default="lastde_results.csv")
    ap.add_argument("--curves", action="store_true", help="额外画一张人类/AI 的概率曲线")
    args = ap.parse_args()

    path = os.path.join(args.data_dir, args.data + ".raw_data.json")
    if not os.path.exists(path):
        print("找不到数据文件：%s" % path)
        print("这个文件夹里可用的文件：")
        for name in sorted(os.listdir(args.data_dir))[:20]:
            print("  ", name)
        return

    originals, sampled = load_pairs(path)
    print("数据：%s" % path)
    print("人类文本 %d 条，AI 文本 %d 条" % (len(originals), len(sampled)))

    tok, model = load_model(args.model)

    def score_one(text, label, idx, total):
        lp = token_logprobs(text, tok, model, args.max_tokens)
        if lp.size < 30:
            return None
        mean_ll = float(lp.mean())
        mde = aggmde(lp)
        lastde = mean_ll / (mde + 1e-6)
        return {
            "label": label,
            "mean_ll": mean_ll,
            "aggmde": mde,
            "lastde": lastde,
        }

    rows = []
    items = [(t, 0) for t in originals] + [(t, 1) for t in sampled]
    for i, (text, label) in enumerate(items):
        r = score_one(text, label, i, len(items))
        if r is not None:
            rows.append(r)
        if (i + 1) % 25 == 0:
            print("  已处理 %d/%d" % (i + 1, len(items)))

    labels = np.array([r["label"] for r in rows])
    lastde_scores = [r["lastde"] for r in rows]
    ll_scores = [r["mean_ll"] for r in rows]

    auc_lastde = auroc(lastde_scores, labels)
    auc_ll = auroc(ll_scores, labels)

    print("\n" + "=" * 54)
    print("复现结果（AUROC，0.5=瞎猜，1.0=完美）")
    print("=" * 54)
    print("  Lastde（论文方法）      : %.4f" % auc_lastde)
    print("  Likelihood（最简单基线）: %.4f" % auc_ll)
    print("  提升                    : %+.4f" % (auc_lastde - auc_ll))
    print("\n  样本数：%d（人类 %d / AI %d）"
          % (len(rows), int((labels == 0).sum()), int((labels == 1).sum())))

    human = [r for r in rows if r["label"] == 0]
    ai = [r for r in rows if r["label"] == 1]
    print("  人类 Agg-MDE 均值：%.4f" % np.mean([r["aggmde"] for r in human]))
    print("  AI   Agg-MDE 均值：%.4f" % np.mean([r["aggmde"] for r in ai]))
    print("  人类 平均对数似然：%.3f" % np.mean([r["mean_ll"] for r in human]))
    print("  AI   平均对数似然：%.3f" % np.mean([r["mean_ll"] for r in ai]))

    if auc_lastde < 0.5:
        print("\n  注意：Lastde 的 AUROC 小于 0.5，说明分数方向和预期相反，")
        print("  报告时应写成 1 - AUROC，或检查数据标签。")

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "mean_ll", "aggmde", "lastde"])
        writer.writeheader()
        writer.writerows(rows)
    print("\n逐条结果已保存：%s" % os.path.abspath(args.out))

    # 画图
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.hist([r["lastde"] for r in human], bins=30, alpha=0.6, label="human")
    plt.hist([r["lastde"] for r in ai], bins=30, alpha=0.6, label="AI")
    plt.xlabel("Lastde score")
    plt.ylabel("count")
    plt.title("Lastde score distribution (AUROC=%.3f)" % auc_lastde)
    plt.legend()
    plt.tight_layout()
    dist_path = os.path.join(FIG_DIR, "lastde_distribution.png")
    plt.savefig(dist_path, dpi=150)
    print("分数分布图已保存：%s" % dist_path)

    if args.curves:
        lp_h = token_logprobs(originals[0], tok, model, args.max_tokens)
        lp_a = token_logprobs(sampled[0], tok, model, args.max_tokens)
        plt.figure(figsize=(9, 4))
        plt.plot(lp_h, marker="o", markersize=3, label="human")
        plt.plot(lp_a, marker="s", markersize=3, label="AI")
        plt.xlabel("token position")
        plt.ylabel("log probability")
        plt.title("Token probability sequences")
        plt.legend()
        plt.tight_layout()
        curve_path = os.path.join(FIG_DIR, "prob_curves.png")
        plt.savefig(curve_path, dpi=150)
        print("概率曲线图已保存：%s" % curve_path)


if __name__ == "__main__":
    main()
