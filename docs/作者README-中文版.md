# 作者 README 中文版（附解读）

> 原文：`D:\Lastde_Detector\README.md`
> 译者注：带 💡 的段落是我加的，不是作者原文。表格数字保持原样。

---

## 项目简介

本项目提供论文中两个主要方法 **Lastde** 和 **Lastde++** 的核心代码。

论文链接：https://openreview.net/forum?id=vo4AHjowKi

我们沿用 [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt/tree/main) 的标准评测流程来评估每一种检测方法。

项目里有一张框架图：`resources/Lastde_framework.png`。

> 💡 **解读**：这句话的意思是，作者的实验设置（数据怎么切、AUROC 怎么算、对比哪些基线）都照搬 Fast-DetectGPT，方便横向比较。你们写报告时可以直接说“评测协议沿用 Fast-DetectGPT”。

---

## 环境

- Python 3.8
- PyTorch 2.0.0
- 其他依赖：

```python
pip install -r requirements.txt
```

（注：我们的实验在两块 RTX 3090 显卡上进行，每块 24GB 显存。）

> 💡 **解读**：
> - `requirements.txt` 里锁的是 `torch==2.0.0+cu118`、`numpy==1.24.4`、`transformers==4.44.1`，都是 2023—2024 年的版本，对应 Python 3.8。
> - **不要在你的电脑上直接照抄**：Python 3.8 已停止维护；`cu118` 不支持 RTX 50 系显卡（你这台是 5060 Ti，需要 cu128+）。
> - 我们用的是 Python 3.11 + 新版 torch，只复现方法，不追求环境一致。
> - 两块 24GB 显卡是为了跑 13B 模型（fp16 下约 26GB，要拆到两张卡上）。

---

## 源模型与代理模型

`pretrain_models` 目录用来存放开源模型，包括作为**代理模型**的模型，以及用来**生成文本**的源模型。

这里以 `gpt-j-6b` 和 `Llama-3-8B` 为例，权重可以从下面的地址下载：

- [gpt-j-6b](https://huggingface.co/EleutherAI/gpt-j-6b/tree/main)
- [Llama-3-8B](https://huggingface.co/meta-llama/Meta-Llama-3-8B/tree/main)

> 💡 **解读**：
> - **源模型（source model）**：真正写出这段 AI 文本的模型。
> - **代理模型（proxy model）**：检测时用来算概率的模型。黑盒场景下你拿不到源模型，只能拿一个开源模型“代打”，默认用 GPT-J-6B。
> - GPT-J-6B 权重约 12GB，Llama-3-8B 约 16GB。**你们不需要下载**——我们的脚本用 GPT-2（约 500MB）当代理。
> - 官方代码里模型路径写死成 `/pretrain_models/xxx`（Linux 绝对路径），在 Windows 上要改。

---

## 数据集

主数据集分两部分：

- `human_original_data` 目录：原始人类文本，json 格式，例如 XSum 数据集就是 **xsum.json**。
- `human_llm_data_for_experiment` 目录：实验用的完整数据，例如 **xsum_llama3_8b.raw_data.json**。

这份数据本来要通过运行下面的脚本得到：

```python
python py_scripts/data_generations/data_generation_opensource.py
```

（注意：**我们已经把数据放在这里了**，不需要再运行。）

每一条完整数据包含两部分：`original`（人类写的文本）和 `sampled`（大模型生成的文本），两部分内容一一对应。`sampled` 的生成方式是：把对应 `original` 文本的**前 30 个 token** 作为提示词输入源模型（本例中是 Llama-3-8B）让它续写，并且所有条目都被截断到相同长度。

- `perturbation_data_detectgpt_npr` 和 `regeneration_data_dnagpt` 目录：分别存放 DetectGPT/DetectNPR 和 DNA-GPT 实验的完整数据。
- 其余目录对应论文中的“鲁棒性”实验部分。

> 💡 **解读（这段最重要）**：
> - 打开 `datasets/human_llm_data_for_experiment/xsum_gpt2_xl.raw_data.json`，你会看到两个列表：`original` 150 条、`sampled` 150 条。
> - 文件名规则：`数据集_源模型.raw_data.json`。例如 `xsum_llama3_8b` = XSum 数据 + LLaMA-3-8B 写的；`reddit_gpt4o` = Reddit 数据 + GPT-4o 写的。
> - 这正好方便做**跨模型实验**：同一批人类文本，换不同模型生成的 AI 文本，看检测器掉多少。
> - “截断到相同长度”很关键：如果人类文本长、AI 文本短，检测器可能靠长度作弊，所以作者统一了长度。
> - 我们的复现脚本就是直接读这些文件，不需要自己生成。

---

## 检测（怎么跑）

在 `shell_scripts` 目录里运行 **detection_white_box.sh** 或 **detection_black_box.sh**，分别触发白盒和黑盒检测。

```shell
cd shell_scripts

# 白盒设置
./detection_white_box.sh

# 黑盒设置
./detection_black_box.sh
```

检测方法包括：

- Likelihood、LogRank、Entropy、DetectLRR、**Lastde（我们的）**。结果保存在 `experiment_results/statistic_detection_results`。
- DetectGPT。结果保存在 `experiment_results/detectgpt_detection_results`。
- DetectNPR。结果保存在 `experiment_results/npr_detection_results`。
- DNA-GPT。结果保存在 `experiment_results/dna_gpt_detection_results`。
- Fast-DetectGPT。结果保存在 `experiment_results/fast_detectgpt_detection_results`。
- **Lastde++（我们的）**。结果保存在 `experiment_results/lastde_doubleplus_detection_results`。

上述检测方法的代码都封装在 `py_scripts/baselines` 里。

其他实验脚本也都在 `shell_scripts` 目录。

> 💡 **解读**：
> - **白盒**：用“写出这段 AI 文本的那个模型”来打分，等于开卷考试，分数高。
> - **黑盒**：只能拿一个开源模型（GPT-J）当代理，更接近真实场景，分数会低一些。
> - `.sh` 是 Linux 脚本，Windows 上要用 **Git Bash** 或 **WSL** 跑；也可以在命令行里照着 `.sh` 的内容一条条执行 `python xxx.py`。
> - 这些脚本会加载 GPT-J/LLaMA，**你们的电脑跑不动**，所以官方流程只能“看懂”，不能“跑通”。

---

## 基线方法

我们提供了以下基线实现：

- **基于采样的方法（sample-based）**：Likelihood、LogRank、Entropy、DetectLRR、**Lastde（我们的）**、Binoculars
- **基于分布的方法（distribution-based）**：DetectGPT、DetectNPR、DNA-GPT、Fast-DetectGPT、**Lastde++（我们的）**
- **即插即用版本（Plug and Play）**：Likelihood_tocsin、LogRank_tocsin、DetectLRR_tocsin、Lastde_tocsin、Fast-DetectGPT_tocsin、Lastde++_tocsin
- **有监督方法（supervised）**：RoBERTa_Base、RoBERTa_Large、ReMoDetect

感谢 [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt/tree/main)、[TOCSIN](https://github.com/Shixuan-Ma/TOCSIN)、[ReMoDetect](https://github.com/hyunseoklee-ai/ReMoDetect)、[Binoculars](https://github.com/ahans30/Binoculars) 等开源项目和模型的作者。

> 💡 **解读**：
> - **sample-based**：只算一次统计量就出分，快。Lastde 属于这一类。
> - **distribution-based**：要生成很多“对照样本”，再比较分布，慢但通常更准。Lastde++ 属于这一类（用 100 个采样样本）。
> - **TOCSIN** 是另一种“即插即用”的改进框架，作者把自己的方法也接了进去，说明兼容性好。
> - **supervised**：需要训练分类器（RoBERTa），和“免训练”是两条路线，作者拿来当对照。

---

## 主要结果（AUROC）

### 白盒（White-box）

- **数据集**：XSum、SQuAD、WritingPrompts
- **采样模型 || 打分模型**：对应的源模型 || 对应的源模型
- **Lastde / Lastde++ 的超参数**：
  - Lastde：s = 3，ε = 10×n，τ′ = 5，聚合函数 = Std
  - Lastde++：s = 4，ε = 8×n，τ′ = 10，聚合函数 = Std

| 方法 | GPT-2 | Neo-2.7 | OPT-2.7 | GPT-J | Llama-13 | Llama2-13 | Llama3-8 | OPT-13 | BLOOM-7.1 | Falcon-7 | Gemma-7 | Phi2-2.7 | 平均 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Likelihood | 91.65 | 89.40 | 88.08 | 84.95 | 63.65 | 65.36 | 98.35 | 84.45 | 88.00 | 76.78 | 70.14 | 89.67 | 82.54 |
| LogRank | 94.31 | 92.87 | 90.99 | 88.68 | 68.87 | 70.27 | 99.04 | 87.74 | 92.42 | 81.32 | 74.81 | 92.13 | 86.12 |
| Entropy | 52.15 | 51.72 | 50.46 | 54.31 | 64.18 | 61.05 | 23.30 | 54.30 | 62.67 | 59.33 | 66.47 | 44.09 | 53.67 |
| DetectLRR | 96.67 | 96.07 | 93.13 | 92.24 | 81.40 | 80.89 | 98.94 | 91.03 | 96.35 | 87.45 | 81.36 | 94.10 | 90.80 |
| **Lastde** | **98.41** | **98.64** | **98.15** | **97.24** | **88.98** | **88.40** | **99.71** | **96.47** | **99.35** | **95.49** | **91.85** | **96.99** | **95.89** |
| DetectGPT | 93.43 | 90.40 | 90.36 | 83.82 | 63.78 | 65.39 | 70.13 | 85.05 | 89.28 | 77.98 | 68.96 | 89.55 | 80.68 |
| DetectNPR | 95.77 | 94.77 | 93.24 | 88.86 | 68.60 | 69.83 | 95.55 | 89.78 | 94.95 | 83.06 | 74.74 | 93.06 | 86.85 |
| DNA-GPT | 89.92 | 86.80 | 86.79 | 82.21 | 66.28 | 64.46 | 98.07 | 82.51 | 86.74 | 74.04 | 63.63 | 88.00 | 80.45 |
| Fast-DetectGPT | 99.57 | 99.49 | 98.78 | 98.95 | 93.45 | 93.34 | **99.91** | 98.07 | 99.53 | 97.74 | 96.90 | 98.10 | 97.82 |
| **Lastde++** | **99.76** | **99.87** | **99.46** | **99.52** | **96.58** | **96.67** | 99.82 | **98.77** | **99.84** | **98.76** | **98.40** | **98.76** | **98.85** |

### 黑盒（Black-box）

- **数据集**：XSum、WritingPrompts、Reddit
- **采样模型 || 打分模型**：
  - **基于采样的方法**：无 || GPT-J-6B
  - **基于分布的方法**：GPT-J-6B || GPT-J-6B
- **Lastde / Lastde++ 的超参数**：
  - Lastde：s = 3，ε = 10×n，τ′ = 5，聚合函数 = Std
  - Lastde++：s = 4，ε = 8×n，τ′ = 10，聚合函数 = Std

| 方法 | GPT-2 | Neo-2.7 | OPT-2.7 | Llama-13 | Llama2-13 | Llama3-8 | OPT-13 | BLOOM-7.1 | Falcon-7 | Gemma-7 | Phi2-2.7 | GPT-4-Turbo | 平均 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Likelihood | 65.88 | 67.09 | 67.40 | 65.75 | 68.61 | 99.60 | 68.80 | 61.80 | 67.42 | 69.90 | 73.93 | 79.69 | 71.32 |
| LogRank | 70.38 | 71.17 | 72.35 | 70.28 | 72.67 | **99.69** | 73.01 | 67.51 | 71.66 | 72.17 | 77.99 | 79.24 | 74.84 |
| Entropy | 61.48 | 58.65 | 54.55 | 49.14 | 45.18 | 14.43 | 53.09 | 60.84 | 50.55 | 48.01 | 46.58 | 35.09 | 48.13 |
| DetectLRR | 79.30 | 79.19 | 81.25 | 78.51 | 78.94 | 97.35 | 80.27 | 79.57 | 79.87 | 73.47 | 83.79 | 73.85 | 80.45 |
| **Lastde** | **89.17** | **90.24** | **89.70** | **80.71** | **79.90** | 99.67 | **90.01** | **88.94** | **84.36** | **79.61** | **88.32** | **81.33** | **86.38** |
| DetectGPT | 67.56 | 69.28 | 72.03 | 66.12 | 67.96 | 82.90 | 73.89 | 61.83 | 68.69 | 66.55 | 72.76 | 81.73 | 70.94 |
| DetectNPR | 68.07 | 68.41 | 73.06 | 67.83 | 70.60 | 96.75 | 75.13 | 63.00 | 70.42 | 65.72 | 74.08 | 79.94 | 72.75 |
| DNA-GPT | 64.15 | 62.63 | 63.64 | 60.77 | 66.71 | 99.47 | 65.75 | 62.01 | 65.08 | 62.59 | 72.02 | 70.75 | 67.97 |
| Fast-DetectGPT | 89.82 | 88.75 | 86.52 | 77.58 | 77.62 | 99.43 | 86.16 | 84.55 | 81.42 | 81.49 | 86.67 | 88.18 | 85.68 |
| **Lastde++** | **94.93** | **95.28** | **94.13** | **85.00** | **85.80** | 99.03 | **93.37** | **92.22** | **89.49** | **87.58** | **92.67** | **88.21** | **91.47** |

### GPT-4-Turbo || GPT-4o || Claude-3-Haiku（黑盒）

- **采样模型 || 打分模型**：
  - **基于采样的方法**：无 || GPT-J-6B
  - **基于分布的方法**：GPT-J-6B || GPT-J-6B
- **Lastde / Lastde++ 的超参数**：
  - Lastde：s = 3，ε = 1×n，τ′ = 15
  - Lastde++：s = 4，ε = 8×n，τ′ = 10

| 源模型 → | GPT-4-Turbo |  |  |  | GPT-4o |  |  |  | Claude-3-haiku |  |  |  |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 数据集 | XSum | WritingPrompts | Reddit | 平均 | XSum | WritingPrompts | Reddit | 平均 | XSum | WritingPrompts | Reddit | 平均 |
| Likelihood | 60.44 | 81.48 | 97.15 | 79.69 | **75.42** | 84.90 | 97.74 | **86.02** | 96.84 | 98.38 | 99.92 | 98.38 |
| LogRank | 61.52 | 79.03 | **97.16** | 79.24 | 73.85 | 82.32 | 97.74 | 84.64 | 97.09 | 98.71 | 99.96 | 98.59 |
| Entropy | 61.24 | 35.56 | 08.48 | 35.09 | 47.50 | 31.60 | 09.74 | 29.61 | 38.90 | 17.69 | 06.56 | 21.05 |
| DetectLRR | 61.71 | 66.75 | 93.10 | 73.85 | 62.87 | 69.06 | 93.75 | 75.23 | 95.78 | 97.96 | 99.56 | 97.77 |
| **Lastde(Std)** | **64.16** | **83.09** | 96.74 | **81.33** | 73.87 | **86.20** | **97.74** | 85.94 | **97.44** | **99.40** | 99.92 | **98.92** |
| Fast-DetectGPT | 80.79 | **89.88** | 93.87 | 88.18 | 86.87 | 93.77 | 97.93 | 92.86 | 99.93 | 99.99 | 99.96 | 99.96 |
| Lastde++(2-Norm) | 76.91 | 87.39 | 93.61 | 85.97 | 85.74 | 92.96 | 97.52 | 92.07 | 99.95 | 99.99 | 99.96 | 99.97 |
| Lastde++(Range) | 82.67 | 86.37 | 91.72 | 86.92 | 85.96 | 91.34 | 96.57 | 91.29 | 99.84 | 99.99 | 99.96 | 99.93 |
| Lastde++(Std) | **83.12** | 88.50 | 93.00 | 88.21 | 86.47 | 93.41 | 96.98 | 92.29 | 99.92 | 99.96 | 99.89 | 99.92 |
| **Lastde++(ExpRange)** | 82.40 | 89.02 | 93.70 | 88.37 | **87.42** | 93.60 | 97.77 | 92.93 | 99.96 | **100** | **99.97** | **99.98** |
| **Lastde++(ExpStd)** | 81.55 | 89.81 | **93.99** | **88.45** | 87.24 | **94.24** | **97.94** | **93.14** | **99.97** | 99.99 | 99.95 | 99.97 |

> 💡 **解读**：
> - 白盒里 Lastde 平均 **95.89**，黑盒里 Lastde 平均 **86.38**，Lastde++ 黑盒 **91.47**。这就是论文摘要里说的数字。
> - 白盒分数普遍高，是因为“出题人就是阅卷人”；黑盒要低 10 个点左右，更真实。
> - GPT-2 那一列（89.17）可以拿来和你们的复现对照——你们用 GPT-2 当代理、GPT-2 当源模型，属于“同模型”场景，理论上应该比较高。
> - **注意一个不一致**：README 写 Lastde++ 的 τ′ = 10，但论文正文写的是 τ′ = 15。做严格复现时以论文为准，或两者都试一下。
> - 作者自己也说（见下面 Notes）更推荐 `ExpStd` 聚合，但主表用的是 `Std`，说明这个选择有讲究。

---

## 注意事项

- 目前我们建议把聚合函数（Agg）设置为 **ExpStd**。

> 💡 **解读**：`Agg` 是把 5 个尺度的 DE 值合成一个数的函数。可选 Std、2-Norm、Range、ExpStd、ExpRange。作者最后推荐 ExpStd，但为了和主表一致，你们复现时用 Std 更稳妥。

---

## 引用

如果觉得这项工作有用，可以用下面的 BibTeX 引用：

```markdown
@articles{
  xu2025trainingfree,
  title={Training-free {LLM}-generated Text Detection by Mining Token Probability Sequences},
  author={Yihuai Xu and Yongwei Wang and Yifei Bi and Huangsen Cao and Zhouhan Lin and Yu Zhao and Fei Wu},
  booktitle={The Thirteenth International Conference on Learning Representations},
  year={2025},
}
```

> 💡 **解读**：作者这里写的是 `@articles`（不规范的条目类型），正式引用建议改成 `@inproceedings`，`booktitle` 写 `International Conference on Learning Representations (ICLR)`。你们报告里按下面这条写更稳：
>
> ```bibtex
> @inproceedings{xu2025lastde,
>   title={Training-free {LLM}-generated Text Detection by Mining Token Probability Sequences},
>   author={Xu, Yihuai and Wang, Yongwei and Bi, Yifei and Cao, Huangsen and Lin, Zhouhan and Zhao, Yu and Wu, Fei},
>   booktitle={International Conference on Learning Representations (ICLR)},
>   year={2025}
> }
> ```

---

## 附：这份 README 没写、但你会踩的坑

1. **模型路径是写死的**：`lastde_doubleplus.py` 里 `model_path = "/pretrain_models/" + model_fullname`，Windows 上会找不到。要改成 `D:\Lastde_Detector\pretrain_models\...`。
2. **`device_map="auto"` 需要 `accelerate`**：requirements 里有，但版本老。
3. **`.sh` 脚本不能直接双击**：需要 Git Bash、WSL，或手动把里面的 `python` 命令一条条跑。
4. **数据不用重新生成**：README 明确说已经提供，跑 `data_generation_opensource.py` 反而会覆盖。
5. **表里的数字是“源模型 = 打分模型”的白盒结果**，不要拿它和黑盒数字混着比。
6. **没有 GPU 也能做缩规模复现**：用作者的数据 + GPT-2 + 我们的 `lastde_repro.py`，只验证方法趋势，不追求复现 95.89%。

---

## 给你们的实操结论

| 官方 README 的内容 | 你们能不能用 |
|---|---|
| 数据（150 对 original/sampled） | ✅ 直接用，已下载到 D 盘 |
| `fastMDE.py`（多样性熵实现） | ✅ 已翻译进 `lastde_repro.py`，并核对到 1e-8 误差 |
| `lastde_doubleplus.py` | ⚠️ 能看懂，但依赖 GPT-J/LLaMA 权重，跑不动 |
| `shell_scripts/*.sh` | ❌ Windows 下不建议折腾 |
| 环境（Python 3.8 + cu118 + 2×3090） | ❌ 不要照抄，用我们装好的 Python 3.11 |
| 表格里的 AUROC | 📊 当作“论文报告值”，和你们的缩规模结果并列写 |

一句话：**官方代码用来“看”，`lastde_repro.py` 用来“跑”，作者的数据用来“对”。**
