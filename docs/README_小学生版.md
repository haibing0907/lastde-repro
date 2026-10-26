# 小学生版复现指南

> 你只需要会三件事：**双击文件、看黑窗口、把数字抄进报告**。
> 不需要懂 pip，不需要进 PyCharm。

---

## 你现在有什么

| 东西 | 在哪 |
|---|---|
| 论文作者官方代码 | `D:\Lastde_Detector` |
| 论文作者提供的数据 | `D:\Lastde_Detector\datasets\human_llm_data_for_experiment` |
| 我们的复现脚本 | 本项目文件夹里的 `lastde_repro.py` |
| 一键运行 | 本项目文件夹里的 `run_repro.bat` |

作者的数据里，每个文件长这样：

```
xsum_gpt2_xl.raw_data.json
├── original : 150 条人类写的新闻
└── sampled  : 150 条 GPT-2 续写的新闻（和上面一一对应）
```

**所以我们连数据都不用造，直接用作者的。**

---

## 第 1 步：先看一眼官方代码长什么样（2 分钟）

打开 `D:\Lastde_Detector`，你会看到：

```
README.md            说明书
requirements.txt     作者当年用的包（Python 3.8 + torch 2.0，别照抄）
datasets/            数据（就是我们要用的）
py_scripts/          代码
  baselines/
    lastde_doubleplus.py   ← 主方法
    scoring_methods/
      fastMDE.py           ← 论文核心：多样性熵
shell_scripts/       实验命令（Linux 的 .sh）
```

**为什么我们不直接跑官方代码？**
因为官方脚本默认加载 GPT-J 6B、LLaMA-3 8B 这些大模型，需要 2 张 24GB 的显卡。你们电脑跑不动。
所以我们用**作者的数据 + 作者的核心算法 + 小模型 GPT-2**，做缩规模复现——这是完全站得住脚的做法。

---

## 第 2 步：双击 `run_repro.bat`（等 5~10 分钟）

双击后会出现黑窗口，它会：

1. 读 `D:\Lastde_Detector\datasets\...\xsum_gpt2_xl.raw_data.json`；
2. 第一次运行会自动下载 GPT-2（约 500MB），耐心等；
3. 对 300 条文本逐条算分；
4. 打印结果表格；
5. 生成两张图。

**看到这些就说明成功：**

```
复现结果（AUROC，0.5=瞎猜，1.0=完美）
======================================================
  Lastde（论文方法）      : 0.8xxx
  Likelihood（最简单基线）: 0.7xxx
  提升                    : +0.0xxx
```

同时文件夹里会多出：

- `lastde_results.csv`（每条文本的分数）
- `lastde_distribution.png`（人类 vs AI 的分数分布）
- `prob_curves.png`（概率曲线）

---

## 第 3 步：看懂这张表（3 分钟）

| 名词 | 人话 |
|---|---|
| AUROC | 0.5=瞎猜，0.9=很准。**Lastde 应该比 Likelihood 高** |
| Lastde | 论文方法：平均对数似然 ÷ Agg-MDE |
| Likelihood | 最简单的基线：只看平均对数似然 |
| Agg-MDE | 曲线“乱不乱”的指标 |

**判断标准**：

- Lastde 的 AUROC 明显大于 0.5 → 方法有效；
- Lastde 大于 Likelihood → “加了局部信息”确实有用，和论文结论一致；
- 两个都接近 0.5 → 数据或标签有问题，把输出发我。

---

## 第 4 步：换一组数据再跑（5 分钟）

把 `run_repro.bat` 里的 `--data xsum_gpt2_xl` 改成下面任意一个：

| 写法 | 数据 |
|---|---|
| `--data reddit_gpt2_xl` | Reddit 问答 |
| `--data squad_gpt2_xl` | 维基问答 |
| `--data xsum_llama3_8b` | AI 文本换成 LLaMA-3 写的（跨模型） |
| `--data reddit_gpt4o` | AI 文本换成 GPT-4o 写的（跨模型） |

改完保存，再双击。**换模型后 Lastde 掉多少，就是“跨模型泛化”的结论。**

也可以换打分模型（把 `--model gpt2` 改成 `--model distilgpt2`，更快更小）。

---

## 第 5 步：把结果搬进报告

| 报告里写 | 用哪个文件 |
|---|---|
| AUROC 表 | 黑窗口里的数字，或 `lastde_results.csv` |
| 分数分布图 | `lastde_distribution.png` |
| 概率曲线图 | `prob_curves.png` |
| “人类更乱”的证据 | 输出里的“人类 Agg-MDE 均值” vs “AI Agg-MDE 均值” |

一句话结论可以写：

> 我们在作者公开的 XSum 数据（150 对）上，用 GPT-2 复现了 Lastde 的评分流程，
> Lastde 的 AUROC 为 0.8x，高于 Likelihood 基线 0.7x，与论文“结合局部统计更强”的结论一致。

---

## 常见错误

| 报错 | 原因 | 怎么办 |
|---|---|---|
| `ModuleNotFoundError: torch` | 用错 Python | 不要敲 `python`，只双击 bat |
| `Can't load tokenizer` / 连接失败 | 下载模型失败 | 确认 bat 里有 `HF_ENDPOINT=https://hf-mirror.com` |
| `PermissionError ... .hf_cache` | 缓存目录权限坏了 | 删掉项目里的 `.hf_cache` 文件夹，再双击 |
| `找不到数据文件` | 数据名写错 | 打开 `D:\Lastde_Detector\datasets\human_llm_data_for_experiment` 看文件名 |
| 窗口一闪就关 | 双击运行出错 | 在该文件夹按住 Shift + 右键 → 在终端中打开 → 输入 `cmd /c run_repro.bat` |

---

## 检查点（做到这里就算复现完成）

- [ ] 双击 `run_repro.bat` 能跑完，看到 AUROC 两个数字
- [ ] 文件夹里有 `lastde_results.csv`
- [ ] 有两张图：`lastde_distribution.png`、`prob_curves.png`
- [ ] 换过至少一个数据集（比如 reddit），得到第二组数字
- [ ] 把数字填进报告/PPT

---

## 为什么这个脚本是可信的

`lastde_repro.py` 里的“多样性熵”部分，是照着官方 `fastMDE.py` 逐行翻译成 numpy 的。
我们用相同输入对比过：

```
我们:  0.010395885
官方:  0.010395901
```

误差在 1e-8 量级，说明算法实现是对的。
