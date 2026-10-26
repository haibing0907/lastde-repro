# Lastde 复现

课程项目，复现 ICLR 2025 的论文 *Training-free LLM-generated Text Detection by Mining Token Probability Sequences*（arXiv:2410.06072）。

数据用作者公开的 XSum（150 条人类 + 150 条 GPT-2 XL 续写），打分模型换成 GPT-2，在 CPU 上跑。

结果：Lastde 的 AUROC 是 0.8938，Likelihood 是 0.8535。我们自己改的加权融合在测试集上从 0.8835 到 0.8955。另外，Agg-MDE 的方向和论文相反，换了三个代理模型都没恢复。

## 文件

```
lastde_repro.py      主程序，跑一次实验
analyze_results.py   读 CSV 算三个 AUROC
improve_fusion.py    改进实验，输出 results/fusion_summary.json
calibrate_eval.py    长度分桶校准
adaptive_eval.py     短文本调 DE 超参，效果不好，留个记录
contrast_eval.py     对比式 DE，没跑通
make_final_ppt.py    生成 PPT
make_lambda_fig.py   画 lambda 曲线
run_repro.bat        跑单个实验
run_length.bat       跑 64/128/256 三组
requirements.txt     依赖
Lastde复现汇报-算法部分.pptx
figures/  results/  tools/
```

`tools/` 里是早期写的脚本，现在不用了，留着备查。

## 代码结构

`lastde_repro.py` 按论文顺序写：

- `load_model()` 加载模型
- `token_logprobs()` 取每个位置真实词的 log 概率（论文式 1）
- `_cosine_adjacent()` 相邻窗口余弦（式 5）
- `_de()` 直方图 + 熵（式 8）
- `aggmde()` 多尺度 DE 取标准差（式 9 分母）
- `auroc()` 秩和公式
- `load_pairs()` 读作者数据
- `main()` 串起来

分数就是一行：

```python
lastde = mean_ll / (aggmde + 1e-6)
```

## 怎么跑

环境在 `G:\anaconda\envs\lastde-repro`，Python 3.11 + torch CPU。

改 `run_repro.bat` 顶部两行，双击：

```bat
set "MODEL=gpt2"
set "DATA=xsum_gpt2_xl"
```

结果在 `results\r_<模型>.csv`。

长度实验直接双击 `run_length.bat`。

改进实验：

```powershell
G:\anaconda\envs\lastde-repro\python.exe improve_fusion.py
```

重新生成 PPT：

```powershell
C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe make_final_ppt.py
```

## 结果

主结果：

| 方法 | AUROC |
|---|---|
| Lastde | 0.8938 |
| Likelihood | 0.8535 |
| 只用 Agg-MDE（按论文方向） | 0.4096 |

代理模型：

| 代理 | Lastde | 人类 MDE | AI MDE |
|---|---|---|---|
| distilgpt2 | 0.8655 | 0.0758 | 0.0780 |
| gpt2 | 0.8938 | 0.0736 | 0.0754 |
| gpt2-medium | 0.9137 | 0.0693 | 0.0737 |

文本长度：

| max-tokens | Lastde | Likelihood |
|---|---|---|
| 64 | 0.6975 | 0.6894 |
| 128 | 0.8576 | 0.7997 |
| 256 | 0.8938 | 0.8535 |

改进（前 50 条人类做参考，125 条验证选 λ，125 条测试）：

| 方法 | AUROC |
|---|---|
| 原 Lastde | 0.8835 |
| 只用 log p | 0.8885 |
| 加权融合（λ=0.6） | 0.8955 |

70 token 的短文本上，融合也有一点用：0.7150 → 0.7355，但整体比 256 token 差很多。

长度校准只在混合长度时有意义：750 条混在一起，AUROC 0.8206 → 0.8322。同长度下没有变化。

## 和论文不一样的地方

| 论文 | 我们 | 原因 |
|---|---|---|
| GPT-J 6B 打分 | GPT-2 | 显存不够 |
| 6 个数据集 | 只跑 XSum | 时间 |
| 实现了 Lastde++ | 没做 | 100 次采样太慢 |

所以绝对值比论文低，这是预期的。

## 踩过的坑

- 一开始 `.venv` 里的 numpy 是 cp314 的，Python 3.11 用不了，后来重建了环境。
- PyCharm 里装包会报临时目录错误，改成在普通终端里装。
- matplotlib 在这个环境里 `savefig` 会静默退出，图是用 Pillow 画的。
- 控制台中文乱码，bat 里加了 `chcp 65001`。
- PPT 被占用时保存失败，改成另存新文件。

## 数据

在 `D:\Lastde_Detector\datasets\human_llm_data_for_experiment\`，不在仓库里，体积大。

官方代码在 `D:\Lastde_Detector`。

## GitHub

```powershell
git init
git add .
git commit -m "init: Lastde reproduction"
git branch -M main
git remote add origin https://github.com/<账号>/<仓库名>.git
git push -u origin main
```

`.gitignore` 已经排除了数据、模型权重、`.venv`、`tmp`、缓存。
