# Lastde 复现（AI for Software Engineering 期末项目）

复现论文：**Training-free LLM-generated Text Detection by Mining Token Probability Sequences**
（ICLR 2025，[arXiv:2410.06072](https://arxiv.org/abs/2410.06072)）。

做法：作者公开数据 + 作者 MDE 算法 + GPT-2 打分，CPU 上做缩规模复现，并针对复现中发现的
“MDE 方向反转”提出改进（加权 z 融合）。

**一句话结论**：Lastde 的 AUROC 为 **0.8938**，高于 Likelihood 基线的 **0.8535**（+4.03 pp）；
改进后的加权融合在同一测试集上从 **0.8835 提升到 0.8955**（+1.2 pp）。

---

## 目录结构

```
lastde-repro/
├── lastde_repro.py          主程序：读数据 → 算 TPS/DE → 打分 → AUROC → 画图
├── analyze_results.py       读 CSV，输出消融用的三个 AUROC
├── improve_fusion.py        改进：加权 z 融合（输出 results/fusion_summary.json）
├── calibrate_eval.py        长度分桶校准（混合长度实验）
├── adaptive_eval.py         短文本自适应 DE 超参（弱改进，仅记录）
├── contrast_eval.py         对比式 DE（未跑通，待验证）
├── make_final_ppt.py        生成终版 PPT（自动读 results/ 和 figures/）
├── make_lambda_fig.py       画 λ 扫描曲线 figures/lambda_curve.png
├── run_repro.bat            跑单个实验（改 MODEL / DATA 即可切换）
├── run_length.bat           一次跑 64 / 128 / 256 三组长度实验
├── requirements.txt         依赖
├── Lastde复现汇报_终版.pptx  汇报 PPT（28 页）
├── figures/                 论文插图与实验结果图
├── results/                 所有 CSV、日志、融合结果 JSON
└── tools/                   旧版生成器与画图脚本（备用）
```

---

## 文件说明

| 文件 | 作用 | 是否常改 |
|---|---|---|
| `lastde_repro.py` | 主程序，一次实验全流程 | 不改，用参数控制 |
| `analyze_results.py` | 消融：Lastde / 只用 LL / 只用 MDE | 不改 |
| `improve_fusion.py` | 改进实验：`z(log p) + λ·z(MDE)` | 不改 |
| `calibrate_eval.py` | 长度校准：混合 64/128/256 | 不改 |
| `make_final_ppt.py` | 重新生成 PPT | 不改 |
| `make_lambda_fig.py` | 生成 λ 曲线图 | 不改 |
| `run_repro.bat` / `run_length.bat` | 双击运行 | 只改顶部变量 |

---

## 代码地图（`lastde_repro.py`）

| 函数 | 对应论文 | 作用 |
|---|---|---|
| `load_model(name)` | — | 加载 tokenizer + 模型 |
| `token_logprobs(text, ...)` | 式(1) | 前向一次，取每个位置真实词的 log 概率 |
| `_cosine_adjacent(x, s)` | 式(5) | 相邻窗口余弦相似度 |
| `_de(x, s, bins)` | 式(8) | 直方图 + 归一化熵 |
| `aggmde(x, ...)` | 式(9) 分母 | 多尺度 DE 取标准差 |
| `auroc(scores, labels)` | 4.2 节 | 秩和公式算 AUROC |
| `load_pairs(path)` | 附录 B.1 | 读作者数据（original / sampled） |
| `main()` | 全流程 | 参数解析、逐条打分、输出 CSV 与图 |

关键一行（论文式 9）：

```python
lastde = mean_ll / (aggmde + 1e-6)
```

---

## 实验设置

| 项 | 设置 |
|---|---|
| 数据 | 作者公开 XSum，150 条人类 + 150 条 GPT-2 XL 续写 |
| 打分模型 | GPT-2（1.24 亿），CPU |
| 默认长度 | 最多 256 token（不足不补） |
| 指标 | AUROC |

### 与论文的差异

| 论文 | 本复现 | 原因 |
|---|---|---|
| GPT-J 6B 打分 | GPT-2 打分 | 显存不足 |
| 6 个数据集 | 1 个（XSum） | 时间 |
| Lastde++ | 未实现 | 100 次采样成本高 |
| — | 增加加权融合改进 | 复现中发现 MDE 方向反转 |

---

## 实验结果

### 主结果

| 方法 | AUROC |
|---|---|
| **Lastde** | **0.8938** |
| Likelihood | 0.8535 |
| 只用 Agg-MDE（按论文方向） | 0.4096 |

### 三个自检

| 指标 | 人类 | AI | 论文方向 | 是否符合 |
|---|---|---|---|---|
| 平均 log p | −3.280 | −2.815 | AI 更高 | 是 |
| Agg-MDE | 0.0736 | 0.0754 | 人类更高 | **否** |
| Lastde 均值 | −44.7 | −37.6 | AI 更高 | 是 |

### 代理模型规模

| 代理 | 参数量 | Lastde | Likelihood | 人类 MDE | AI MDE |
|---|---|---|---|---|---|
| distilgpt2 | 0.82 亿 | 0.8655 | 0.7917 | 0.0758 | 0.0780 |
| gpt2 | 1.24 亿 | 0.8938 | 0.8535 | 0.0736 | 0.0754 |
| gpt2-medium | 3.55 亿 | 0.9137 | 0.8217 | 0.0693 | 0.0737 |

**结论**：代理越大越准；但人类 MDE 始终低于 AI，方向未恢复。

### 文本长度

| max-tokens | Lastde | Likelihood |
|---|---|---|
| 64 | 0.6975 | 0.6894 |
| 128 | 0.8576 | 0.7997 |
| 256 | 0.8938 | 0.8535 |

**结论**：越短越难，与论文 Fig.5 一致。

### 改进：加权 z 融合

公式：

```
score = z(mean log p) + λ · z(Agg-MDE)
```

数据切分：前 50 条人类做参考，125 条验证（选 λ），125 条测试（只报告）。

| 方法 | 测试集 AUROC |
|---|---|
| 原 Lastde（除法） | 0.8835 |
| 只用 log p | 0.8885 |
| **加权融合（λ=0.6）** | **0.8955** |

### 短文本检查（70 token）

| 方法 | AUROC |
|---|---|
| 原 Lastde | 0.7150 |
| 只用 log p | 0.7048 |
| 加权融合 | **0.7355** |

**结论**：短文本下改进仍然有效，但整体远低于 256 token。

### 长度校准（辅助）

| 场景 | 结果 |
|---|---|
| 混合长度 750 条 | 0.8206 → **0.8322** |
| 64 token 误报率 | 12% → 8% |
| 等长基准 | 不变（桶内排序不变） |

---

## 怎么跑

环境已配好：`G:\anaconda\envs\lastde-repro\python.exe`（Python 3.11 + torch CPU）。

### 跑一个实验

编辑 `run_repro.bat` 顶部两行：

```bat
set "MODEL=gpt2"
set "DATA=xsum_gpt2_xl"
```

双击运行，结果在 `results\r_<模型>.csv`，日志在 `results\run_<模型>.log`。

### 跑长度实验

双击 `run_length.bat`，生成 `results\r_len64.csv`、`r_len128.csv`、`r_len256.csv`。

### 跑改进实验

```powershell
G:\anaconda\envs\lastde-repro\python.exe improve_fusion.py
```

### 重新生成 PPT

```powershell
C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe make_final_ppt.py
```

---

## 常用参数

| 参数 | 作用 | 示例 |
|---|---|---|
| `--data` | 数据集 | `xsum_gpt2_xl`、`reddit_gpt2_xl` |
| `--model` | 代理模型 | `distilgpt2`、`gpt2`、`gpt2-medium` |
| `--max-tokens` | 截断长度 | 64、128、256 |
| `--out` | 结果 CSV | `results\r_x.csv` |

---

## 环境

```powershell
conda create -n lastde-repro python=3.11
conda activate lastde-repro
pip install -r requirements.txt
```

模型缓存默认在 `C:\Users\Administrator\.cache\huggingface`。

---

## 数据与模型

- 数据：`D:\Lastde_Detector\datasets\human_llm_data_for_experiment\*.raw_data.json`
- 官方代码：`D:\Lastde_Detector`
- 数据**不在本仓库**，体积大且受版权限制；按作者仓库说明下载。

---

## GitHub

```powershell
git init
git add .
git commit -m "init: Lastde reproduction"
git branch -M main
git remote add origin https://github.com/<账号>/<仓库名>.git
git push -u origin main
```

**不要提交**：`datasets/`、模型权重、`.venv/`、`tmp/`、缓存（`.gitignore` 已排除）。

---

## 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 控制台乱码 | 编码 | bat 已加 `chcp 65001` |
| 窗口一闪就关 | 没 `pause` 或提前报错 | 用现有 bat，或在 cmd 里运行 |
| 找不到数据 | 数据名写错 | 核对 `D:\Lastde_Detector\datasets\...` |
| 下载模型慢 | 网络 | bat 已设 `HF_ENDPOINT=https://hf-mirror.com` |
| 结果和论文差很多 | 代理模型更小 | 见“与论文的差异” |
