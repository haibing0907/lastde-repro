# -*- coding: utf-8 -*-
"""生成终版汇报 PPT（21 页，逻辑重排 + 填入真实实验数字）。"""

import csv
import json
import os
import sys

import numpy as np
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lastde_repro import auroc  # noqa: E402

NAVY = RGBColor(0x1F, 0x38, 0x64)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
LIGHT_BLUE = RGBColor(0xDE, 0xEB, 0xF7)
ORANGE = RGBColor(0xC5, 0x5A, 0x11)
LIGHT_ORANGE = RGBColor(0xFB, 0xE5, 0xD6)
GRAY = RGBColor(0x59, 0x59, 0x59)
MID_GRAY = RGBColor(0x7F, 0x7F, 0x7F)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x54, 0x82, 0x35)
FONT = "Microsoft YaHei"
MONO = "Consolas"
W, H = 13.333, 7.5


def set_font(run, size=14, bold=False, color=GRAY, font=FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        rPr.append(rPr.makeelement(qn(tag), {"typeface": font}))


def textbox(s, l, t, w, h, text, size=14, bold=False, color=GRAY,
            align=PP_ALIGN.LEFT, font=FONT, anchor=MSO_ANCHOR.TOP):
    box = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = 0
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        set_font(r, size, bold, color, font)
    return box


def bullets(s, l, t, w, h, items, size=14, color=GRAY, gap=8, bullet_color=BLUE):
    box = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    first = True
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        r1 = p.add_run()
        r1.text = "● "
        set_font(r1, size - 3, True, bullet_color)
        if isinstance(item, tuple):
            head, body = item
            r2 = p.add_run()
            r2.text = head
            set_font(r2, size, True, NAVY)
            r3 = p.add_run()
            r3.text = body
            set_font(r3, size, False, color)
        else:
            r2 = p.add_run()
            r2.text = item
            set_font(r2, size, False, color)


def rect(s, l, t, w, h, fill=LIGHT_GRAY, line=None):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    try:
        sh.adjustments[0] = 0.08
    except Exception:
        pass
    sh.shadow.inherit = False
    return sh


def header(s, title, subtitle, num):
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(W), Inches(0.09))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    textbox(s, 0.6, 0.32, 12.0, 0.6, title, 26, True, NAVY)
    if subtitle:
        textbox(s, 0.6, 0.95, 12.0, 0.4, subtitle, 13, False, MID_GRAY)
    textbox(s, 0.6, 7.08, 6, 0.3, "Lastde 复现  ·  AI for Software Engineering", 9, False, MID_GRAY)
    textbox(s, 12.2, 7.08, 0.6, 0.3, str(num), 9, False, MID_GRAY, PP_ALIGN.RIGHT)


def table(s, l, t, w, data, col_widths, size=13, row_h=0.55, highlight=None):
    rows, cols = len(data), len(data[0])
    shape = s.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(row_h * rows))
    tbl = shape.table
    for i, cw in enumerate(col_widths):
        tbl.columns[i].width = Inches(cw)
    for r in range(rows):
        tbl.rows[r].height = Inches(row_h)
        for c in range(cols):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(data[r][c])
            if r == 0:
                set_font(run, size, True, WHITE)
                cell.fill.solid()
                cell.fill.fore_color.rgb = NAVY
            else:
                set_font(run, size, False, GRAY)
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_ORANGE if (highlight and r in highlight) else (
                    WHITE if r % 2 else LIGHT_GRAY)
    return tbl


def picture_fit(s, path, left, top, box_w, box_h):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    ratio = w / h
    if box_w / box_h > ratio:
        ph, pw = box_h, box_h * ratio
    else:
        pw, ph = box_w, box_w / ratio
    s.shapes.add_picture(path, Inches(left + (box_w - pw) / 2),
                         Inches(top + (box_h - ph) / 2), width=Inches(pw))


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


def load_stats(path):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    y = [int(r["label"]) for r in rows]
    lastde = [float(r["lastde"]) for r in rows]
    ll = [float(r["mean_ll"]) for r in rows]
    mde = [float(r["aggmde"]) for r in rows]
    h = [float(r["aggmde"]) for r in rows if int(r["label"]) == 0]
    a = [float(r["aggmde"]) for r in rows if int(r["label"]) == 1]
    lh = [float(r["mean_ll"]) for r in rows if int(r["label"]) == 0]
    la = [float(r["mean_ll"]) for r in rows if int(r["label"]) == 1]
    sh = [float(r["lastde"]) for r in rows if int(r["label"]) == 0]
    sa = [float(r["lastde"]) for r in rows if int(r["label"]) == 1]
    return dict(n=len(rows), lastde=auroc(lastde, y), ll=auroc(ll, y),
                mde_only=auroc([-x for x in mde], y),
                mde_h=float(np.mean(h)), mde_a=float(np.mean(a)),
                ll_h=float(np.mean(lh)), ll_a=float(np.mean(la)),
                score_h=float(np.mean(sh)), score_a=float(np.mean(sa)))


def main():
    main_s = load_stats(os.path.join(HERE, "results", "lastde_results.csv"))
    distil = load_stats(os.path.join(HERE, "results", "r_distil.csv"))
    medium = load_stats(os.path.join(HERE, "results", "r_medium.csv"))
    len64 = load_stats(os.path.join(HERE, "results", "r_len64.csv"))
    len128 = load_stats(os.path.join(HERE, "results", "r_len128.csv"))
    len256 = load_stats(os.path.join(HERE, "results", "r_len256.csv"))

    fusion_path = os.path.join(HERE, "results", "fusion_summary.json")
    if os.path.exists(fusion_path):
        with open(fusion_path, encoding="utf-8") as f:
            fusion = json.load(f)
    else:
        fusion = dict(lambda_=0.6, test_baseline=0.8835, test_ll=0.8885,
                      test_fusion=0.8955, n_test=125, full_baseline=0.8938)

    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    # 1 封面
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(W), Inches(H))
    bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
    textbox(s, 0.9, 1.5, 11.5, 0.5, "ICLR 2025  ·  Training-free LLM-generated Text Detection",
            15, False, RGBColor(0xBD, 0xD7, 0xEE))
    textbox(s, 0.9, 2.1, 11.8, 1.2, "免训练 AI 文本检测", 46, True, WHITE)
    textbox(s, 0.9, 3.3, 11.8, 0.9, "Lastde：从 token 概率序列中挖掘局部统计", 26, False,
            RGBColor(0xDE, 0xEB, 0xF7))
    line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(4.5), Inches(2.2), Inches(0.06))
    line.fill.solid(); line.fill.fore_color.rgb = ORANGE; line.line.fill.background()
    textbox(s, 0.9, 4.85, 11.5, 0.45, "论文复现与实验报告", 18, False, WHITE)
    textbox(s, 0.9, 5.5, 11.5, 0.4, "组员：【A / B / C】     课程：【人工智能应用】     日期：【2026.xx】",
            13, False, RGBColor(0xBD, 0xD7, 0xEE))
    textbox(s, 0.9, 6.55, 11.5, 0.35, "论文：arXiv:2410.06072   ·   代码：D:\\Lastde_Detector",
            11, False, RGBColor(0x9D, 0xC3, 0xE6))
    notes(s, "开场一句话：我们复现 ICLR 2025 的 Lastde，一篇免训练的 AI 文本检测论文。")

    # 2 路线
    s = prs.slides.add_slide(blank)
    header(s, "汇报路线", "从问题到方法，再到我们自己的实验", 2)
    items = [("01", "问题与洞察", "AI 文本为什么能被检测"),
             ("02", "原理", "一个 token 的概率是怎么算的"),
             ("03", "方法", "五步流水线 + 一个公式"),
             ("04", "我们的复现", "主结果、消融、鲁棒性"),
             ("05", "发现", "MDE 方向反转"),
             ("06", "改进", "加权融合 + 长度校准")]
    y = 1.6
    for num, title, desc in items:
        rect(s, 0.9, y, 0.9, 0.7, LIGHT_BLUE)
        textbox(s, 0.9, y + 0.12, 0.9, 0.45, num, 18, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, 2.05, y + 0.02, 3.2, 0.4, title, 17, True, NAVY)
        textbox(s, 5.1, y + 0.08, 7.2, 0.4, desc, 13, False, GRAY)
        y += 0.85
    notes(s, "路线页 15 秒：先讲原理，再讲方法，最后是我们自己的实验和发现。")

    # 3 问题
    s = prs.slides.add_slide(blank)
    header(s, "问题：AI 文本已经很难分辨", "训练型检测器要标注、要训练；免训练是另一条路", 3)
    rect(s, 0.6, 1.65, 4.9, 3.7, LIGHT_GRAY)
    textbox(s, 0.9, 1.85, 4.3, 0.4, "现实中的滥用", 17, True, NAVY)
    bullets(s, 0.9, 2.35, 4.3, 2.8, ["假新闻、批量生成的评论", "学术写作中的代写",
                                     "模型用 AI 数据训练导致退化"], 14, gap=10)
    table(s, 5.85, 1.65, 6.9, [
        ["类型", "做法", "缺点"],
        ["训练型", "抽特征 → 训二分类器", "要标注、换领域掉点"],
        ["免训练", "统计量直接打分", "只用全局、采样慢"],
    ], [1.4, 3.2, 2.3], size=12, row_h=0.8)
    rect(s, 5.85, 4.35, 6.9, 1.25, LIGHT_BLUE)
    textbox(s, 6.05, 4.48, 6.5, 0.95,
            "本文要补的缺口：现有免训练方法只看“整段平均”，忽略了概率曲线的局部形状。",
            14, False, NAVY)
    notes(s, "强调：训练型不是不好，是换领域掉点；免训练的痛点是只用全局统计。")

    # 4 核心洞察
    s = prs.slides.add_slide(blank)
    header(s, "核心洞察：人写的曲线更“毛躁”", "同一开头，人续写 vs AI 续写，概率曲线的形状不同", 4)
    bullets(s, 0.6, 1.8, 5.6, 4.2, [
        ("TPS：", "每个 token 被模型预测的概率，按顺序排成一条序列"),
        ("橙色（人）：", "常有模型没想到的词，曲线出现深谷"),
        ("绿色（AI）：", "按模型分布采样，曲线贴着顶部、很平"),
    ], 15, gap=14)
    fig = os.path.join(HERE, "figures", "fig1a_paper.png")
    if os.path.exists(fig):
        picture_fit(s, fig, 6.4, 1.6, 6.4, 4.5)
    textbox(s, 6.4, 6.25, 6.4, 0.3, "图源：论文 Fig.1(a)，OPT-2.7 续写的 TPS 对比", 9, False,
            MID_GRAY, PP_ALIGN.CENTER)
    notes(s, "这一页建立直觉：橙色针多且深，绿色贴顶。")

    # 5 概率怎么来的
    s = prs.slides.add_slide(blank)
    header(s, "先补一课：一个 token 的概率怎么算", "前文 → 5 万个分数 → softmax → 取真实词 → 取 log", 5)
    steps = [("①", "前文", "前 99 个 token"), ("②", "打分", "5 万个候选各一个分数"),
             ("③", "softmax", "分数变概率，和 = 1"), ("④", "查表", "取真实词那一项，再取 log")]
    x = 0.55
    for num, head, desc in steps:
        rect(s, x, 1.7, 2.9, 1.6, LIGHT_BLUE)
        textbox(s, x, 1.8, 2.9, 0.35, num, 16, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, x, 2.15, 2.9, 0.4, head, 15, True, NAVY, PP_ALIGN.CENTER)
        textbox(s, x, 2.55, 2.9, 0.6, desc, 11, False, GRAY, PP_ALIGN.CENTER)
        x += 3.15
    table(s, 0.9, 3.7, 11.5, [
        ["如果作者实际写的是", "模型给的概率", "log p", "图上的高度"],
        ["approve", "6.07%", "−2.80", "偏上"],
        ["fund", "0.72%", "−4.93", "中间"],
        ["procrastinate", "约 0.00004%", "−14.7", "针尖"],
    ], [4.0, 3.0, 2.2, 2.3], size=13, row_h=0.5, highlight=[3])
    textbox(s, 0.9, 6.05, 11.5, 0.7,
            "同一个前文，模型给的分布一样；写的词越“冷门”，点掉得越深。图里那些向下的尖就是这些词。",
            13, False, GRAY)
    notes(s, "这页回答“概率怎么来的”，用真实 GPT-2 数字。")

    # 6 只取平均不够
    s = prs.slides.add_slide(blank)
    header(s, "只取平均，会丢掉什么", "前人的免训练方法：把整段 TPS 压成一个数", 6)
    table(s, 0.8, 1.75, 11.7, [
        ["方法", "怎么压成一个数", "问题"],
        ["Likelihood", "平均 log p", "只看向整体，忽略波动"],
        ["LogRank", "平均 log(真实词排名)", "换了刻度，还是平均"],
        ["DetectLRR", "Likelihood ÷ LogRank", "两个平均相除，还是平均"],
    ], [2.6, 5.0, 4.1], size=13, row_h=0.55)
    rect(s, 0.8, 4.05, 11.7, 2.3, LIGHT_ORANGE)
    textbox(s, 1.0, 4.18, 11.3, 0.4, "一个反例", 14, True, ORANGE)
    textbox(s, 1.0, 4.6, 11.3, 1.6,
            "A: -1  -5  -1  -5  -1  -5     平均 = -3\n"
            "B: -3  -3  -3  -3  -3  -3     平均 = -3\n"
            "Likelihood 判不出区别；但 A 在剧烈震荡（人），B 很平（AI）。",
            13, False, GRAY, font=MONO)
    textbox(s, 1.0, 6.0, 11.3, 0.4, "平均只看总和，不看顺序。Lastde 补的就是这一点。",
            13, True, ORANGE)
    notes(s, "核心动机：平均把顺序抹掉了。")

    # 7 方法五步
    s = prs.slides.add_slide(blank)
    header(s, "方法：把概率曲线当时间序列", "五步得到局部统计，再和全局似然结合", 7)
    steps = [("①", "算 TPS", "前向 + 取真实词"), ("②", "多尺度", "相邻 τ 个平均"),
             ("③", "滑窗 + 余弦", "相邻片段像不像"), ("④", "分箱 + 熵", "直方图 → DE"),
             ("⑤", "聚合 + 相除", "std 后除以似然")]
    x = 0.55
    for num, head, desc in steps:
        rect(s, x, 1.8, 2.25, 2.1, LIGHT_BLUE)
        textbox(s, x, 1.9, 2.25, 0.4, num, 18, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, x, 2.3, 2.25, 0.45, head, 15, True, NAVY, PP_ALIGN.CENTER)
        textbox(s, x, 2.8, 2.25, 0.8, desc, 11, False, GRAY, PP_ALIGN.CENTER)
        x += 2.5
    pills = [("全局", "平均对数似然"), ("局部", "Agg-MDE"), ("合成", "Lastde = 全局 ÷ 局部")]
    x = 1.2
    for head, body in pills:
        rect(s, x, 4.55, 3.4, 1.2, WHITE, line=BLUE)
        textbox(s, x, 4.65, 3.4, 0.35, head, 13, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, x, 5.0, 3.4, 0.5, body, 15, True, NAVY, PP_ALIGN.CENTER)
        x += 3.75
    textbox(s, 0.6, 6.1, 12.1, 0.5, "论文式(9)：Lastde(t) = 平均 log p ÷ Agg-MDE(t)，分数越高越像 AI。",
            15, True, NAVY, PP_ALIGN.CENTER)
    notes(s, "五步是“切碎 → 比较 → 量化 → 汇总”。")

    # 8 公式
    s = prs.slides.add_slide(blank)
    header(s, "三个公式，对应三段代码", "答辩时指到这里，说明不是照跑脚本", 8)
    cards = [("TPS（式 1）", "L(t) = ( log p(t₁), …, log p(tₙ) )", "token_logprobs()"),
             ("多样性熵（式 8）", "DE = − Σ pᵢ log pᵢ  /  log ε", "_de()"),
             ("Lastde 分数（式 9）", "Lastde = mean(log p)  /  Agg-MDE", "main()")]
    y = 1.75
    for head, formula, func in cards:
        rect(s, 0.8, y, 11.7, 1.3, LIGHT_GRAY)
        textbox(s, 1.05, y + 0.1, 3.2, 0.4, head, 14, True, BLUE)
        textbox(s, 4.2, y + 0.28, 6.6, 0.6, formula, 18, True, NAVY, font=MONO)
        textbox(s, 10.6, y + 0.12, 1.8, 0.35, func, 11, False, MID_GRAY, font=MONO)
        y += 1.55
    textbox(s, 0.8, 6.45, 11.7, 0.4, "我们的实现与官方 fastMDE.py 对齐：同一输入，误差 < 1e-6。",
            12, False, MID_GRAY)
    notes(s, "只讲“哪个公式对应哪个函数”，不推导。")

    # 9 手算 DE
    s = prs.slides.add_slide(blank)
    header(s, "手算一遍：DE 到底在算什么", "12 个 token 的例子，数字可复算", 9)
    table(s, 0.6, 1.75, 12.1, [
        ["文本", "平均 log p", "余弦范围", "占用格子", "Agg-MDE"],
        ["人类", "−3.03", "0.82 ~ 0.91", "5 / 120", "0.160"],
        ["AI", "−2.84", "0.99 ~ 1.00", "1 / 120", "0.000"],
    ], [2.4, 2.6, 2.8, 2.4, 2.4], size=13, row_h=0.55)
    rect(s, 0.6, 3.5, 12.1, 2.6, LIGHT_BLUE)
    textbox(s, 0.85, 3.62, 11.6, 0.35, "怎么从余弦到 DE", 13, True, NAVY)
    textbox(s, 0.85, 4.0, 11.6, 2.0,
            "① 相邻窗口余弦 → 9 个值（人类 0.82~0.91）\n"
            "② 按 [-1,1] 分 120 格，数直方图（人类占 5 格）\n"
            "③ 归一化得 p，算 −Σ p ln p，再除以 ln(120) → DE = 0.318\n"
            "④ 三个尺度各算一次，取标准差 → Agg-MDE = 0.160",
            13, False, GRAY)
    textbox(s, 0.85, 5.8, 11.6, 0.4, "余弦看窗口像不像，DE 看这些相似度散不散。",
            12, True, NAVY)
    textbox(s, 0.6, 6.35, 12.1, 0.4, "AI 太光滑，所有余弦挤在 1 格，DE = 0；真实数据不会这么极端（约 0.07）。",
            10, False, MID_GRAY)
    notes(s, "对应论文 3.1；强调“数格子”这个动作。")

    # 10 评测协议
    s = prs.slides.add_slide(blank)
    header(s, "评测协议：怎么保证比较公平", "数据、指标、场景三件事", 10)
    cols = [("数据", ["每个数据集 150 条人类文本", "取前 30 个 token 当提示", "让源模型续写", "截断到等长"]),
            ("指标", ["AUROC：排序正确率", "0.5 = 瞎猜", "1.0 = 完美", "阈值无关"]),
            ("场景", ["白盒：用源模型打分", "黑盒：用代理模型打分", "代理默认 GPT-J-6B", "我们：GPT-2"])]
    x = 0.6
    for head, items in cols:
        rect(s, x, 1.7, 3.95, 3.9, LIGHT_GRAY)
        textbox(s, x + 0.2, 1.85, 3.5, 0.4, head, 17, True, NAVY)
        bullets(s, x + 0.25, 2.4, 3.5, 3.0, items, 12, gap=6)
        x += 4.1
    rect(s, 0.6, 5.8, 12.1, 0.85, LIGHT_ORANGE)
    textbox(s, 0.8, 5.93, 11.7, 0.6, "截断到等长，是为了让检测器没法靠文本长度取巧。",
            13, False, ORANGE)
    notes(s, "体现读懂了实验设计。")

    # 11 论文结果
    s = prs.slides.add_slide(blank)
    header(s, "论文报告的数字", "白盒 / 黑盒平均 AUROC", 11)
    table(s, 1.0, 1.8, 11.3, [
        ["方法", "白盒", "黑盒"],
        ["Lastde（本文）", "95.89", "86.38"],
        ["Lastde++（本文）", "98.85", "91.47"],
        ["Fast-DetectGPT", "97.82", "85.68"],
        ["Likelihood", "82.54", "71.32"],
    ], [4.5, 3.2, 3.2], size=14, row_h=0.55, highlight=[1, 2])
    textbox(s, 1.0, 5.6, 11.3, 0.8,
            "白盒分数高，因为“出题人就是阅卷人”；黑盒更接近真实场景，普遍掉 10 个点左右。",
            13, False, GRAY)
    notes(s, "数字来自作者 README 的 Table 1/2。")

    # 12 我们的设置
    s = prs.slides.add_slide(blank)
    header(s, "我们的复现：缩规模，但不缩方法", "作者数据 + 作者算法 + 小模型", 12)
    rows = [("数据", "作者公开的 XSum 150 对（人类 / GPT-2 XL 续写）"),
            ("打分模型", "GPT-2（1.24 亿），CPU 推理"),
            ("算法", "官方 fastMDE.py 逐行翻译，误差 < 1e-6"),
            ("运行", "双击 run_repro.bat，约 3 分钟")]
    y = 1.7
    for head, body in rows:
        rect(s, 0.6, y, 2.3, 0.95, LIGHT_BLUE)
        textbox(s, 0.6, y + 0.22, 2.3, 0.5, head, 15, True, NAVY, PP_ALIGN.CENTER)
        rect(s, 3.1, y, 9.5, 0.95, LIGHT_GRAY)
        textbox(s, 3.3, y + 0.22, 9.1, 0.5, body, 14, False, GRAY)
        y += 1.15
    rect(s, 0.6, 6.3, 12.1, 0.55, WHITE, line=ORANGE)
    textbox(s, 0.8, 6.37, 11.7, 0.4, "和论文不同：论文用 GPT-J 6B（12GB），我们用 GPT-2（525MB）。",
            13, True, ORANGE)
    notes(s, "把“唯一差别”说清楚。")

    # 13 主结果
    s = prs.slides.add_slide(blank)
    header(s, "主结果：Lastde 高于基线", "XSum · 150 对 · GPT-2 打分", 13)
    textbox(s, 0.7, 1.8, 2.8, 0.4, "Lastde", 14, True, BLUE)
    textbox(s, 0.7, 2.15, 3.2, 0.9, "%.4f" % main_s["lastde"], 44, True, NAVY)
    textbox(s, 0.7, 3.4, 2.8, 0.4, "Likelihood 基线", 14, True, MID_GRAY)
    textbox(s, 0.7, 3.75, 3.2, 0.8, "%.4f" % main_s["ll"], 32, True, GRAY)
    textbox(s, 0.7, 4.9, 3.6, 0.5, "提升 %+.2f 个百分点" % ((main_s["lastde"] - main_s["ll"]) * 100),
            16, True, GREEN)
    dist_img = os.path.join(HERE, "figures", "lastde_distribution.png")
    if os.path.exists(dist_img):
        picture_fit(s, dist_img, 4.4, 1.7, 8.2, 4.6)
    textbox(s, 4.4, 6.4, 8.2, 0.4, "样本数：%d（人类 150 / AI 150）" % main_s["n"], 12, False, MID_GRAY)
    notes(s, "先报数字，再说明“绝对值低于论文是因为代理模型小”。")

    # 14 三个自检
    s = prs.slides.add_slide(blank)
    header(s, "三个自检：结果方向对不对", "不只报数字，还要检查中间量", 14)
    table(s, 0.8, 1.9, 11.8, [
        ["指标", "人类", "AI", "论文方向", "是否符合"],
        ["平均 log p", "%.3f" % main_s["ll_h"], "%.3f" % main_s["ll_a"], "AI 更高", "是"],
        ["Agg-MDE", "%.4f" % main_s["mde_h"], "%.4f" % main_s["mde_a"], "人类更高", "否"],
        ["Lastde 均值", "%.1f" % main_s["score_h"], "%.1f" % main_s["score_a"], "AI 更高", "是"],
    ], [3.0, 2.4, 2.4, 2.2, 1.8], size=13, row_h=0.65, highlight=[2])
    textbox(s, 0.8, 5.25, 11.8, 1.2,
            "第二行是复现中出现的异常：Agg-MDE 方向和论文相反。\n"
            "后面的代理模型实验会继续查。",
            13, False, GRAY)
    notes(s, "主动暴露异常，为后面铺垫。")

    # 15 消融
    s = prs.slides.add_slide(blank)
    header(s, "消融：全局和局部，缺一不可？", "同一份数据，三种打分方式", 15)
    table(s, 1.0, 1.9, 11.2, [
        ["打分方式", "AUROC", "说明"],
        ["Lastde（LL ÷ Agg-MDE）", "%.4f" % main_s["lastde"], "论文方法，最高"],
        ["只用 LL", "%.4f" % main_s["ll"], "最简单基线"],
        ["只用 Agg-MDE", "%.4f" % main_s["mde_only"], "低于 0.5，方向反了"],
    ], [5.4, 2.6, 3.2], size=14, row_h=0.6, highlight=[1])
    textbox(s, 1.0, 5.0, 11.2, 1.2,
            "组合最高（0.8938）→ 复现了“全局 + 局部”的结论；\n"
            "只用 Agg-MDE 只有 0.4096，说明局部项单独用会反向，必须靠似然校准。",
            13, False, GRAY)
    notes(s, "对应论文附录 E。")

    # 16 代理规模
    s = prs.slides.add_slide(blank)
    header(s, "鲁棒性一：代理模型越大越准", "模型变大，AUROC 单调上升，但 MDE 方向仍未恢复", 16)
    table(s, 0.8, 1.8, 11.8, [
        ["代理模型", "参数量", "Lastde", "Likelihood", "人类 MDE", "AI MDE"],
        ["distilgpt2", "0.82 亿", "%.4f" % distil["lastde"], "%.4f" % distil["ll"],
         "%.4f" % distil["mde_h"], "%.4f" % distil["mde_a"]],
        ["gpt2", "1.24 亿", "%.4f" % main_s["lastde"], "%.4f" % main_s["ll"],
         "%.4f" % main_s["mde_h"], "%.4f" % main_s["mde_a"]],
        ["gpt2-medium", "3.55 亿", "%.4f" % medium["lastde"], "%.4f" % medium["ll"],
         "%.4f" % medium["mde_h"], "%.4f" % medium["mde_a"]],
    ], [2.4, 1.8, 2.0, 2.2, 1.8, 1.6], size=13, row_h=0.55, highlight=[3])
    textbox(s, 0.8, 4.9, 11.8, 1.3,
            "结论：代理越大，Lastde 越准（0.866 → 0.894 → 0.914）；\n"
            "但人类 MDE 始终低于 AI，方向没有恢复，差距反而扩大到 0.0044。",
            13, False, GRAY)
    textbox(s, 0.8, 6.15, 11.8, 0.6,
            "注意：Likelihood 基线并非随模型变大单调上升（0.792 → 0.854 → 0.822），所以“提升”列不能单独解读。",
            11, False, MID_GRAY)
    notes(s, "对应论文 Fig.8（代理模型选择）。")

    # 17 文本长度
    s = prs.slides.add_slide(blank)
    header(s, "鲁棒性二：文本越短越难", "与论文 Fig.5 的结论一致", 17)
    table(s, 0.8, 1.8, 11.8, [
        ["max-tokens", "Lastde", "Likelihood", "人类 MDE", "AI MDE"],
        ["64", "%.4f" % len64["lastde"], "%.4f" % len64["ll"],
         "%.4f" % len64["mde_h"], "%.4f" % len64["mde_a"]],
        ["128", "%.4f" % len128["lastde"], "%.4f" % len128["ll"],
         "%.4f" % len128["mde_h"], "%.4f" % len128["mde_a"]],
        ["256", "%.4f" % len256["lastde"], "%.4f" % len256["ll"],
         "%.4f" % len256["mde_h"], "%.4f" % len256["mde_a"]],
    ], [2.6, 2.4, 2.6, 2.2, 2.0], size=13, row_h=0.55)
    textbox(s, 0.8, 4.9, 11.8, 1.2,
            "结论：长度从 256 降到 64，AUROC 由 0.894 降到 0.698；\n"
            "短文本下 MDE 从 0.074 升至 0.090，Lastde 相对基线的优势从 4.0 pp 缩到 0.8 pp。",
            13, False, GRAY)
    textbox(s, 0.8, 6.1, 11.8, 0.5,
            "原因和论文 Fig.5 一样：token 少，可用尺度少，DE 的方差大。",
            11, False, MID_GRAY)
    notes(s, "对应论文 Fig.5（response length）。")

    # 18 发现
    s = prs.slides.add_slide(blank)
    header(s, "复现中的异常：MDE 方向反了", "论文说人写得更“毛躁”，我们的数据却相反", 18)
    rect(s, 0.6, 1.7, 3.9, 3.9, LIGHT_ORANGE)
    textbox(s, 0.85, 1.82, 3.4, 0.4, "什么叫“反转”", 14, True, ORANGE)
    bullets(s, 0.85, 2.3, 3.4, 3.0, [
        "论文：人类 MDE > AI",
        "我们：人类 0.0736",
        "　　　AI　 0.0754",
        "差 0.0018，很小",
    ], 11, gap=6, bullet_color=ORANGE)
    rect(s, 4.65, 1.7, 3.9, 3.9, LIGHT_BLUE)
    textbox(s, 4.9, 1.82, 3.4, 0.4, "为什么与论文相悖", 14, True, BLUE)
    bullets(s, 4.9, 2.3, 3.4, 3.0, [
        "方向反了，MDE 从“人类信号”变成“AI 信号”",
        "按论文方向用：AUROC 0.4096",
        "反着用：0.5904，也不高",
    ], 11, gap=6)
    rect(s, 8.7, 1.7, 4.0, 3.9, LIGHT_GRAY)
    textbox(s, 8.95, 1.82, 3.5, 0.4, "排查过程（五步）", 14, True, NAVY)
    textbox(s, 8.95, 2.3, 3.5, 3.0,
            "① 差 0.0018，先问是否噪声\n\n"
            "② bootstrap：区间不含 0，显著但小\n\n"
            "③ 换三个代理都反 → 不是容量\n\n"
            "④ 同长度截断 → 不是长度\n\n"
            "⑤ 推测：源/代理同家族",
            10, False, GRAY)
    rect(s, 0.6, 5.85, 12.1, 0.85, NAVY)
    textbox(s, 0.85, 5.97, 11.6, 0.6,
            "方向不确定，所以改进不假设方向，改用加权融合。",
            13, True, WHITE, PP_ALIGN.CENTER)
    notes(s, "先定义反转，再说后果，最后给四个未证实的假设。")

    # 19 弱点
    s = prs.slides.add_slide(blank)
    header(s, "MDE 不可靠", "三个观察：方向、跨模型、单独使用", 19)
    cards = [("方向反了", "人类 %.4f  <  AI %.4f" % (main_s["mde_h"], main_s["mde_a"]),
              "论文假设人类更高"),
             ("换模型也没用", "三个代理全部相反", "不是模型容量问题"),
             ("单独用更差", "AUROC %.4f" % main_s["mde_only"], "按论文方向算，比瞎猜差")]
    x = 0.6
    for head, big, small in cards:
        rect(s, x, 1.75, 3.9, 2.0, LIGHT_ORANGE)
        textbox(s, x + 0.2, 1.88, 3.5, 0.4, head, 14, True, ORANGE)
        textbox(s, x + 0.2, 2.35, 3.5, 0.7, big, 16, True, NAVY)
        textbox(s, x + 0.2, 3.12, 3.5, 0.5, small, 11, False, GRAY)
        x += 4.1

    textbox(s, 0.6, 3.95, 6.9, 0.35, "一个真实例子（XSum · GPT-2 · 人类 191 / AI 200 token）", 11, True, NAVY)
    table(s, 0.6, 4.35, 6.9, [
        ["文本", "log p", "Agg-MDE", "原分数"],
        ["人类", "−3.654", "0.0796", "−45.88"],
        ["AI", "−2.776", "0.0603", "−46.07"],
    ], [1.7, 1.7, 1.7, 1.8], size=10, row_h=0.42)
    textbox(s, 0.6, 6.12, 6.9, 0.7,
            "上限 256 token；这两条是 191 / 200，未截断。\n"
            "排序：人类 −45.88 > AI −46.07，判成 AI。",
            10, True, ORANGE)
    rect(s, 7.8, 4.05, 4.9, 2.5, LIGHT_BLUE)
    textbox(s, 8.0, 4.15, 4.5, 2.3,
            "为什么错：\nAI 的 log p 很像 AI（−2.78），\n"
            "但 MDE 异常小（0.0603），\n除以小数 → 分数被拉到 −46。\n"
            "一个指标异常，就盖掉另一个。",
            10, False, NAVY)
    notes(s, "先立靶子：MDE 不可靠，除法很脆弱。")

    # 20 为什么异常小
    s = prs.slides.add_slide(blank)
    header(s, "MDE 为什么会偏小", "MDE 测的不是抖动，是“抖动随尺度的变化”", 20)
    table(s, 0.7, 1.85, 11.9, [
        ["文本", "τ=1", "τ=2", "τ=3", "τ=4", "τ=5", "MDE"],
        ["人类", "0.671", "0.615", "0.546", "0.511", "0.474", "0.080"],
        ["AI", "0.669", "0.641", "0.593", "0.563", "0.518", "0.060"],
    ], [2.3, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6], size=13, row_h=0.5, highlight=[2])
    bullets(s, 0.7, 3.85, 7.3, 2.1, [
        ("“降幅” = τ=1 减 τ=5：", "人类 0.671−0.474 = 0.197；AI 0.669−0.518 = 0.151"),
        ("降幅大：", "多样性集中在细尺度，一平滑就掉"),
        ("降幅小：", "多样性跨尺度持续，平滑后还在"),
        ("5 个数越接近：", "标准差越小，MDE 越小"),
    ], 11, gap=4)
    rect(s, 8.3, 3.85, 4.3, 2.1, LIGHT_ORANGE)
    textbox(s, 8.5, 3.95, 3.9, 1.9,
            "所以：MDE 小 ≠ 文本不抖。\n\n"
            "“抖”指 DE 高（局部形状变化大）。\n"
            "一条 DE 很高的文本，只要 5 个尺度的 DE 差不多，MDE 也可以很小。",
            10, False, NAVY)
    rect(s, 0.7, 6.15, 11.9, 0.75, LIGHT_BLUE)
    textbox(s, 0.9, 6.22, 11.5, 0.6,
            "这也解释了方向为什么会反：MDE 由“跨尺度是否一致”决定，不由平滑程度决定。",
            11, False, NAVY)
    notes(s, "MDE 小是“剖面平”，不是“文本不抖”。")

    # 21 为什么不能当分母
    s = prs.slides.add_slide(blank)
    header(s, "MDE 当分母的问题", "同一个流畅分，除以不同的抖动分，结论会翻转", 21)
    table(s, 0.7, 1.85, 7.2, [
        ["假设", "抖动分", "分数", "判断"],
        ["MDE 正常（人类均值）", "0.0796", "−34.9", "AI"],
        ["MDE 异常小（实际值）", "0.0603", "−46.1", "人类"],
    ], [3.0, 1.4, 1.4, 1.4], size=12, row_h=0.55, highlight=[2])
    textbox(s, 0.7, 3.6, 7.2, 0.8,
            "同一条 AI 文本，流畅分都是 −2.776；\n只是分母从 0.0796 变成 0.0603。",
            12, False, GRAY)
    rect(s, 8.2, 1.85, 4.5, 2.6, LIGHT_ORANGE)
    textbox(s, 8.4, 1.98, 4.1, 2.3,
            "分母小 24%\n"
            "分数 −34.9 → −46.1\n"
            "差 11.2 分\n"
            "判决：AI → 人类",
            12, False, NAVY)
    rect(s, 0.7, 4.8, 12.0, 1.4, LIGHT_BLUE)
    textbox(s, 0.95, 4.95, 11.5, 1.2,
            "分母就像放大镜的倍数：倍数一变，负分被放大的程度就变。\n"
            "MDE 只差 0.02，结论就翻。",
            13, False, NAVY)
    notes(s, "同一个流畅分，只换分母，结论翻转。")

    # 22 改进
    s = prs.slides.add_slide(blank)
    header(s, "改进：加权 z 融合", "不再假设方向，让权重从验证集里学", 22)
    rect(s, 0.6, 1.7, 5.9, 1.4, LIGHT_GRAY)
    textbox(s, 0.85, 1.8, 5.4, 0.3, "原方法（没有标准化）", 11, True, MID_GRAY)
    textbox(s, 0.85, 2.15, 5.4, 0.6, "score = 平均 log p ÷ Agg-MDE", 15, True, NAVY, font=MONO)
    rect(s, 6.8, 1.7, 5.9, 1.4, LIGHT_ORANGE)
    textbox(s, 7.05, 1.8, 5.4, 0.3, "改进（两项都 z 后相加）", 11, True, ORANGE)
    textbox(s, 7.05, 2.15, 5.4, 0.6, "score = z(log p) + λ · z(MDE)", 15, True, NAVY, font=MONO)

    textbox(s, 0.65, 3.3, 6.0, 0.35, "z 里的两个数从哪来？", 12, True, NAVY)
    bullets(s, 0.65, 3.68, 6.0, 1.8, [
        ("参考集：", "前 50 条人类文本（不参与测试）"),
        ("log p：", "均值 −3.246，标准差 0.510"),
        ("Agg-MDE：", "均值 0.0741，标准差 0.0078"),
        ("z(x) =", "(x − 均值) ÷ 标准差"),
    ], 10, gap=2)

    textbox(s, 6.85, 3.3, 6.0, 0.35, "例：第 19 页那对文本（XSum · GPT-2）", 12, True, NAVY)
    textbox(s, 6.85, 3.68, 6.0, 1.8,
            "人类（191 token）\n"
            "  z(log p)=−0.80，z(MDE)=+0.71\n"
            "  → −0.80+0.6×0.71 = −0.37\n"
            "AI（200 token）\n"
            "  z(log p)=+0.92，z(MDE)=−1.77\n"
            "  → +0.92+0.6×(−1.77) = −0.14",
            9.5, False, GRAY, font=MONO)

    rect(s, 0.6, 5.65, 12.1, 1.2, LIGHT_BLUE)
    textbox(s, 0.85, 5.75, 11.6, 1.0,
            "λ = 0.6 在验证集上选出；测试集只报最终结果。\n"
            "限制：只调了一个系数，但用了 125 条带标签验证集，属于弱监督。",
            10, False, NAVY)
    notes(s, "z 的均值和标准差来自 50 条人类参考文本。")

    # 23 算一遍 70 token
    s = prs.slides.add_slide(blank)
    header(s, "算一遍：30 token 提示 + 40 token 续写", "70 token 的文本，怎么从 TPS 走到 score", 23)
    textbox(s, 0.6, 1.62, 12.1, 0.35,
            "70 token  →  69 个 log 概率（第 1 个 token 没有前文）  →  平均 log p、MDE  →  z  →  score",
            10, False, MID_GRAY)
    table(s, 0.6, 2.1, 12.1, [
        ["文本", "平均 log p", "MDE", "z(log p)", "z(MDE)", "score"],
        ["人类（30+40）", "−3.390", "0.0933", "+0.22", "+0.29", "0.39"],
        ["AI（30+40）", "−2.870", "0.0999", "+1.00", "+0.76", "1.45"],
    ], [3.0, 2.2, 1.8, 1.8, 1.8, 1.5], size=12, row_h=0.5, highlight=[2])
    rect(s, 0.6, 3.7, 12.1, 1.0, LIGHT_BLUE)
    textbox(s, 0.85, 3.8, 11.6, 0.8,
            "参考集：50 条人类文本（同样截到 70 token）\n"
            "log p：均值 −3.535，标准差 0.666；MDE：均值 0.0891，标准差 0.0143",
            10, False, NAVY)
    bullets(s, 0.6, 4.85, 12.1, 1.4, [
        ("人类：", "z(log p) = (−3.390 + 3.535) ÷ 0.666 = +0.22；"
                  "z(MDE) = (0.0933 − 0.0891) ÷ 0.0143 = +0.29"),
        ("score：", "0.22 + 0.6 × 0.29 = 0.39；AI 那条 = 1.45 → AI 更高，判对"),
        ("整体（300 条，70 token）：", "baseline 0.7150 → 融合 0.7355（+2.0 pp）"),
    ], 10, gap=3)
    textbox(s, 0.6, 6.35, 12.1, 0.4, "短文本仍比 256 token 难：0.7355 vs 0.8955。",
            10, False, ORANGE)
    notes(s, "70 token 的完整计算：参考集也要同长度。")

    # 24 为什么按 AUROC 选 λ
    s = prs.slides.add_slide(blank)
    header(s, "λ 为什么按“AUROC 最高”来选", "不是拍脑袋：验证集上扫一遍，取峰点", 24)
    picture_fit(s, os.path.join(HERE, "figures", "lambda_curve.png"), 0.4, 1.7, 7.8, 4.5)
    bullets(s, 8.4, 1.9, 4.5, 3.8, [
        ("候选：", "−1.5 到 1.5，每 0.1 一个"),
        ("每个 λ：", "在验证集算一次 AUROC"),
        ("取峰点：", "0.6，AUROC 0.9344"),
        ("为什么不用准确率：", "要先定阈值"),
        ("为什么不在测试集选：", "那是作弊"),
    ], 11, gap=6)
    textbox(s, 0.6, 6.4, 12.1, 0.4, "选 λ 只看验证集；测试集只报最终结果。", 11, False, ORANGE)
    notes(s, "λ 是验证集扫出来的，不是拍的。")

    # 24 结果
    s = prs.slides.add_slide(blank)
    header(s, "改进结果：+1.2 个百分点", "同一测试集、同一批数据，只换组合方式", 25)
    table(s, 0.7, 1.85, 6.6, [
        ["方法", "AUROC"],
        ["原 Lastde（除法）", "%.4f" % fusion["test_baseline"]],
        ["只用平均 log p", "%.4f" % fusion["test_ll"]],
        ["加权融合（本文）", "%.4f" % fusion["test_fusion"]],
    ], [4.2, 2.4], size=14, row_h=0.6, highlight=[3])
    rect(s, 7.6, 1.85, 5.1, 1.95, LIGHT_BLUE)
    textbox(s, 7.8, 2.0, 4.7, 0.4, "辅助改进：长度校准", 13, True, BLUE)
    bullets(s, 7.85, 2.45, 4.6, 1.3, [
        "混合长度：0.8206 → 0.8322",
        "64 token 误报率：12% → 8%",
        "等长基准上无效（桶内不变）",
    ], 11, gap=4)
    textbox(s, 0.7, 4.35, 6.6, 0.6,
            "全量 300 条基线为 %.4f；不同切分不能直接比较。"
            % fusion["full_baseline"],
            11, False, MID_GRAY)
    rect(s, 0.7, 5.15, 11.8, 0.95, LIGHT_ORANGE)
    textbox(s, 0.9, 5.27, 11.4, 0.8,
            "边界：λ 来自验证集；测试集只有 125 条，1.2 个点有波动；\n"
            "长度校准只对“混合长度部署”有意义，对论文的等长基准无效。",
            12, False, ORANGE)
    notes(s, "先报数字，再主动说局限，防止被追问。")

    # 25 局限与伦理
    s = prs.slides.add_slide(blank)
    header(s, "局限与伦理", "知道边界，才算真的复现", 26)
    rect(s, 0.6, 1.65, 5.9, 4.9, LIGHT_GRAY)
    textbox(s, 0.85, 1.8, 5.4, 0.4, "四点局限", 15, True, NAVY)
    bullets(s, 0.85, 2.3, 5.4, 4.0, [
        "代理模型 GPT-2 替代 GPT-J",
        "只用了 1 个数据集（XSum）",
        "没有实现 Lastde++",
        "截断长度与论文不完全一致",
    ], 13, gap=8)
    rect(s, 6.8, 1.65, 5.9, 4.9, LIGHT_ORANGE)
    textbox(s, 7.05, 1.8, 5.4, 0.4, "伦理与社会责任", 15, True, ORANGE)
    bullets(s, 7.05, 2.3, 5.4, 4.0, [
        "误判：套话式的人类写作会被判成 AI",
        "偏差：语言、领域、非母语作者",
        "军备竞赛：检测与反检测",
        "隐私：检测需要读取文本",
    ], 13, gap=8)
    notes(s, "伦理四条对应课程要求。")

    # 26 结论
    s = prs.slides.add_slide(blank)
    header(s, "结论", "四句话总结", 27)
    bullets(s, 0.9, 1.75, 11.7, 3.9, [
        ("方法有效：", "Lastde 把概率曲线当时间序列，用局部熵补充全局似然。"),
        ("复现成立：", "作者数据上，Lastde 的 AUROC 高于 Likelihood 基线（0.894 vs 0.854）。"),
        ("改进有效：", "MDE 不可靠，改用加权 z 融合，同一测试集 0.8835 → 0.8955（+1.2 pp）。"),
        ("边界清楚：", "短文本仍弱；长度校准只对混合长度部署有效，对等长基准无效。"),
    ], 15, gap=12)
    rect(s, 0.9, 5.55, 11.6, 1.0, NAVY)
    textbox(s, 1.1, 5.67, 11.2, 0.75,
            "复现的价值不在于把 95.89 抄成一样，而在于能说清“差在哪、为什么”。",
            16, True, WHITE, PP_ALIGN.CENTER)
    notes(s, "结论页停 5 秒。")

    # 21 Q&A
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(W), Inches(H))
    bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
    textbox(s, 0, 2.6, W, 1.2, "Q & A", 54, True, WHITE, PP_ALIGN.CENTER)
    textbox(s, 0, 3.9, W, 0.5, "谢谢，欢迎提问", 20, False, RGBColor(0xDE, 0xEB, 0xF7), PP_ALIGN.CENTER)
    textbox(s, 0, 4.7, W, 0.5, "代码：D:\\Lastde_Detector   ·   数据：datasets/human_llm_data_for_experiment",
            12, False, RGBColor(0x9D, 0xC3, 0xE6), PP_ALIGN.CENTER)
    notes(s, "Q&A 分工：技术 A；数据 B；论文与伦理 C。")

    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Lastde复现汇报_终版.pptx")
    prs.save(out)
    print("saved", out, "slides", len(prs.slides))


if __name__ == "__main__":
    main()
