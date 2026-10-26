# Lastde 复现（AI for Software Engineering 期末项目）

复现论文：**Training-free LLM-generated Text Detection by Mining Token Probability Sequences**（ICLR 2025，[arXiv:2410.06072](https://arxiv.org/abs/2410.06072)）。

做法：用作者公开的数据 + 作者的 MDE 算法 + GPT-2 打分，在 CPU 上做缩规模复现。

**一句话结论**：Lastde 的 AUROC 为 **0.8938**，高于 Likelihood 基线的 **0.8535**（+4.03 个百分点），
复现了“全局 + 局部统计”更有效的核心结论；同时发现 Agg-MDE 的方向与论文相反，并做了三组鲁棒性实验定位原因。

---

## 目录结构

```
lastde-repro/
├── lastde_repro.py         主程序：读数据 → 算 TPS/DE → 打分 → 算 AUROC → 画图
├── analyze_results.py      读 CSV，输出消融用的三个 AUROC
├── run_repro.bat           跑单个实验（改 MODEL / DATA 即可切换）
├── run_length.bat          一次跑 64 / 128 / 256 三组长度实验
├── make_final_ppt.py       从 results/ 读数字，生成终版 PPT
├── docs/                   说明文档（见文末索引）
├── figures/                论文插图与我们生成的图
├── results/                实验输出的 CSV 与日志
└── tools/                  辅助脚本（旧版 PPT 生成、画图、环境安装）
```

---

## 每个文件的作用

| 文件 | 作用 | 要不要改 |
|---|---|---|
| `lastde_repro.py` | 主程序，一次实验全流程 | 一般不改，用参数控制 |
| `analyze_results.py` | 消融分析：Lastde / 只用 LL / 只用 MDE | 不改 |
| `run_repro.bat` | 双击跑一个模型；改 `MODEL` 和 `DATA` 切换 | 只改两行 |
| `run_length.bat` | 双击跑 64/128/256 三组长度 | 不改 |
| `make_final_ppt.py` | 重新生成 PPT（自动读 `results/`） | 不改 |
| `tools/` | 旧版生成器、Pillow 画图、环境安装脚本 | 备用，不影响主流程 |

---

## 代码地图（`lastde_repro.py`）

| 函数 | 对应论文 | 作用 |
|---|---|---|
| `load_model(name)` | — | 加载 tokenizer + 模型，缓存 |
| `token_logprobs(text, ...)` | 式(1) | 前向一次，取出每个位置“真实词”的 log 概率 |
| `_cosine_adjacent(x, s)` | 式(5) | 相邻窗口余弦相似度 |
| `_de(x, s, bins)` | 式(8) | 直方图 + 归一化熵 |
| `aggmde(x, ...)` | 式(9) 分母 | 多尺度 DE，取标准差 |
| `auroc(scores, labels)` | 4.2 节 | 秩和公式算 AUROC |
| `load_pairs(path)` | 附录 B.1 | 读作者数据（original / sampled） |
| `main()` | 全流程 | 参数解析、逐条打分、输出 CSV 与图 |

关键一行（论文式 9）：

```python
lastde = mean_ll / (aggmde + 1e-6)
```

---

## 实验结果（XSum，150 对，GPT-2 打分）

### 主结果

| 方法 | AUROC |
|---|---|
| **Lastde** | **0.8938** |
| Likelihood | 0.8535 |
| 只用 Agg-MDE | 0.4096（低于 0.5，方向反了） |

### 代理模型规模

| 代理 | 参数量 | Lastde | 人类 MDE | AI MDE |
|---|---|---|---|---|
| distilgpt2 | 0.82 亿 | 0.8655 | 0.0758 | 0.0780 |
| gpt2 | 1.24 亿 | 0.8938 | 0.0736 | 0.0754 |
| gpt2-medium | 3.55 亿 | 0.9137 | 0.0693 | 0.0737 |

### 文本长度

| max-tokens | Lastde | Likelihood |
|---|---|---|
| 64 | 0.6975 | 0.6894 |
| 128 | 0.8576 | 0.7997 |
| 256 | 0.8938 | 0.8535 |

### 改进实验

| 脚本 | 作用 | 结果 |
|---|---|---|
| `improve_fusion.py` | 加权 z 融合替代固定除法 | 测试集 0.8835 → **0.8955** |
| `calibrate_eval.py` | 长度分桶校准 | 混合长度 0.8206 → 0.8322 |
| `adaptive_eval.py` | 短文本自适应 DE 超参 | 0.6975 → 0.7058（弱） |
| `contrast_eval.py` | 对比式 DE | 未跑通，待验证 |

融合做法：`score = z(平均 log p) + λ · z(Agg-MDE)`，λ 在验证集上选（本次 0.6），
切分为 50 条参考 / 125 条验证 / 125 条测试，结果写入 `results/fusion_summary.json`。

**结论**：代理越大越准；文本越短越难；人类 MDE 始终低于 AI，方向未恢复。

---

## 怎么跑

环境已经配好（conda 环境 `G:\anaconda\envs\lastde-repro`，Python 3.11 + torch CPU）。

### 跑一个实验

编辑 `run_repro.bat` 里两行：

```bat
set "MODEL=gpt2"
set "DATA=xsum_gpt2_xl"
```

双击运行，结果在 `results\r_<模型>.csv`，日志在 `results\run_<模型>.log`。

### 跑长度实验

双击 `run_length.bat`，生成 `results\r_len64.csv`、`r_len128.csv`、`r_len256.csv`。

### 重新生成 PPT

```powershell
C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe make_final_ppt.py
```

会生成 `Lastde复现汇报_终版.pptx`，数字自动从 `results/` 读取。

---

## 常用参数

| 参数 | 作用 | 示例 |
|---|---|---|
| `--data` | 用哪份数据 | `xsum_gpt2_xl`、`reddit_gpt2_xl` |
| `--model` | 代理模型 | `distilgpt2`、`gpt2`、`gpt2-medium` |
| `--max-tokens` | 截断长度 | 64、128、256 |
| `--out` | 结果 CSV 路径 | `results\r_x.csv` |

---

## 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 窗口乱码 | 控制台编码 | bat 已加 `chcp 65001`，直接双击即可 |
| 窗口一闪就关 | 脚本没 `pause` 或提前报错 | 用现在的 bat；或在已打开的 cmd 里运行 |
| 找不到数据文件 | 数据名写错 | 文件名在 `D:\Lastde_Detector\datasets\human_llm_data_for_experiment` |
| 下载模型慢 | HuggingFace 网络 | bat 已设 `HF_ENDPOINT=https://hf-mirror.com` |

---

## 文档索引

| 文档 | 内容 |
|---|---|
| [README_小学生版](docs/README_小学生版.md) | 从零开始的步骤说明 |
| [代码逐行讲解](docs/代码逐行讲解.md) | 每个函数、每个公式的对应 |
| [复现与答辩全攻略](docs/复现与答辩全攻略.md) | 论文要点、实验矩阵、PPT 结构、20 个问答 |
| [作者 README 中文版](docs/作者README-中文版.md) | 官方仓库说明的翻译与解读 |
| [PPT 使用说明](docs/PPT使用说明.md) | 每页放什么、怎么更新数字 |

---

## GitHub 提交（课程要求）

课程要求 **Platform: GitHub to organize your team project**。建议仓库包含：

```
README.md            项目说明（本文件）
lastde_repro.py      主程序
analyze_results.py   消融分析
improve_fusion.py    改进实验
calibrate_eval.py    长度校准
make_final_ppt.py    PPT 生成
docs/ figures/ results/ tools/
requirements.txt     依赖
```

**不要提交**：`datasets/`、模型权重、`.venv/`、`tmp/`、缓存（已在 `.gitignore` 中）。

首次上传：

```powershell
git init
git add .
git commit -m "init: Lastde reproduction"
git branch -M main
git remote add origin https://github.com/<你的账号>/<仓库名>.git
git push -u origin main
```

协作建议：每人开自己的分支，提 PR 合并；保证提交记录里有三个人的贡献。

数据不在仓库里，报告里写清楚获取方式：从作者仓库 `D:\Lastde_Detector` 下载，或按 README 的说明放置。

## 数据与模型

- 数据：`D:\Lastde_Detector\datasets\human_llm_data_for_experiment\*.raw_data.json`
- 官方代码：`D:\Lastde_Detector`
- 模型缓存：`C:\Users\Administrator\.cache\huggingface\hub`
