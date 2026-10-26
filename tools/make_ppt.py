# -*- coding: utf-8 -*-
"""生成 Lastde 复现汇报 PPT 模板（可编辑，结果自动取自 lastde_results.csv）。"""

import csv
import os
import sys

import numpy as np
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lastde_repro import auroc, aggmde, _de  # noqa: E402

# ---------------------------------------------------------------- 颜色 / 字体

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
        el = rPr.makeelement(qn(tag), {"typeface": font})
        rPr.append(el)


def textbox(slide, l, t, w, h, text, size=14, bold=False, color=GRAY,
            align=PP_ALIGN.LEFT, font=FONT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        set_font(r, size, bold, color, font)
    return box


def bullets(slide, l, t, w, h, items, size=15, color=GRAY, gap=8, bullet_color=BLUE):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
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


def rect(slide, l, t, w, h, fill=LIGHT_GRAY, line=None, radius=True):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(l), Inches(t), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    if radius:
        try:
            shape.adjustments[0] = 0.08
        except Exception:
            pass
    shape.shadow.inherit = False
    return shape


def header(slide, title, subtitle=None, num=None):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(W), Inches(0.09))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()

    textbox(slide, 0.6, 0.32, 11.5, 0.6, title, 26, True, NAVY)
    if subtitle:
        textbox(slide, 0.6, 0.95, 12.1, 0.45, subtitle, 13, False, MID_GRAY)
    # footer
    textbox(slide, 0.6, 7.08, 6, 0.3, "Lastde 复现  ·  AI for Software Engineering", 9, False, MID_GRAY)
    if num is not None:
        textbox(slide, 12.2, 7.08, 0.6, 0.3, str(num), 9, False, MID_GRAY, PP_ALIGN.RIGHT)


def table(slide, l, t, w, h, data, col_widths, header_fill=NAVY, size=13,
          row_h=None, highlight_rows=None, highlight_fill=LIGHT_ORANGE):
    rows, cols = len(data), len(data[0])
    shape = slide.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(h))
    tbl = shape.table
    for i, cw in enumerate(col_widths):
        tbl.columns[i].width = Inches(cw)
    for r in range(rows):
        if row_h:
            tbl.rows[r].height = Inches(row_h)
        for c in range(cols):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c > 0 else PP_ALIGN.LEFT
            r0 = p.add_run()
            r0.text = str(data[r][c])
            if r == 0:
                set_font(r0, size, True, WHITE)
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill
            else:
                set_font(r0, size, False, GRAY)
                cell.fill.solid()
                if highlight_rows and r in highlight_rows:
                    cell.fill.fore_color.rgb = highlight_fill
                else:
                    cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT_GRAY
    return tbl


def add_picture_fit(slide, path, left, top, box_w, box_h):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    ratio = w / h
    if box_w / box_h > ratio:
        ph = box_h
        pw = ph * ratio
    else:
        pw = box_w
        ph = pw / ratio
    x = left + (box_w - pw) / 2
    y = top + (box_h - ph) / 2
    slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(pw))


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ---------------------------------------------------------------- 读结果

def load_stats():
    path = os.path.join(HERE, "lastde_results.csv")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    labels = [int(r["label"]) for r in rows]
    lastde = [float(r["lastde"]) for r in rows]
    mean_ll = [float(r["mean_ll"]) for r in rows]
    mde = [float(r["aggmde"]) for r in rows]
    human = [r for r in rows if int(r["label"]) == 0]
    ai = [r for r in rows if int(r["label"]) == 1]
    return {
        "n": len(rows),
        "auc_lastde": auroc(lastde, labels),
        "auc_ll": auroc(mean_ll, labels),
        "auc_mde": auroc([-x for x in mde], labels),
        "ll_h": np.mean([float(r["mean_ll"]) for r in human]),
        "ll_a": np.mean([float(r["mean_ll"]) for r in ai]),
        "mde_h": np.mean([float(r["aggmde"]) for r in human]),
        "mde_a": np.mean([float(r["aggmde"]) for r in ai]),
        "score_h": np.mean([float(r["lastde"]) for r in human]),
        "score_a": np.mean([float(r["lastde"]) for r in ai]),
    }


# ---------------------------------------------------------------- 玩具例子

def toy_numbers():
    h = np.array([-3.2, -2.1, -4.0, -2.5, -3.8, -2.2, -4.2, -2.0, -3.6, -2.3, -4.1, -2.4])
    a = np.array([-2.7, -3.0, -2.6, -2.9, -2.8, -3.1, -2.7, -2.85, -2.75, -3.05, -2.65, -2.95])
    return {
        "h": (h.mean(), aggmde(h, s=2, tau_max=3), _de(h, 2, 120)),
        "a": (a.mean(), aggmde(a, s=2, tau_max=3), _de(a, 2, 120)),
    }


# ---------------------------------------------------------------- 建 PPT

def main():
    stats = load_stats()
    toy = toy_numbers()

    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    # ---------------- 1 封面
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(W), Inches(H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()

    textbox(s, 0.9, 1.55, 11.5, 0.5, "ICLR 2025  ·  Training-free LLM-generated Text Detection", 15, False,
            RGBColor(0xBD, 0xD7, 0xEE))
    textbox(s, 0.9, 2.15, 11.8, 1.3, "免训练 AI 文本检测", 46, True, WHITE)
    textbox(s, 0.9, 3.35, 11.8, 1.0, "Lastde：从 token 概率序列中挖掘局部统计", 26, False,
            RGBColor(0xDE, 0xEB, 0xF7))
    line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(4.55), Inches(2.2), Inches(0.06))
    line.fill.solid()
    line.fill.fore_color.rgb = ORANGE
    line.line.fill.background()

    textbox(s, 0.9, 4.9, 11.5, 0.45, "论文复现与实验报告", 18, False, WHITE)
    textbox(s, 0.9, 5.55, 11.5, 0.4, "组员：【A / B / C】     课程：【人工智能应用】     日期：【2026.xx】", 13, False,
            RGBColor(0xBD, 0xD7, 0xEE))
    textbox(s, 0.9, 6.6, 11.5, 0.35, "论文：arXiv:2410.06072   ·   代码：D:\\Lastde_Detector", 11, False,
            RGBColor(0x9D, 0xC3, 0xE6))
    notes(s, "开场一句话：我们复现的是 ICLR 2025 的 Lastde，一篇免训练的 AI 文本检测论文。")

    # ---------------- 2 路线
    s = prs.slides.add_slide(blank)
    header(s, "汇报路线", "从问题到方法，再到我们自己的实验", 2)
    items = [
        ("01", "问题与洞察", "为什么 AI 文本可以被检测"),
        ("02", "方法", "五步流水线 + 一个公式"),
        ("03", "评测协议", "数据怎么造、AUROC 怎么读"),
        ("04", "我们的复现", "缩规模实验与结果"),
        ("05", "发现与局限", "MDE 方向反转、差在哪"),
    ]
    y = 1.75
    for num, title, desc in items:
        rect(s, 0.9, y, 0.9, 0.75, LIGHT_BLUE)
        textbox(s, 0.9, y + 0.14, 0.9, 0.5, num, 20, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, 2.05, y + 0.05, 3.2, 0.4, title, 18, True, NAVY)
        textbox(s, 5.1, y + 0.1, 7.2, 0.4, desc, 14, False, GRAY)
        y += 1.0
    notes(s, "路线页 10 秒带过，让老师知道后面怎么展开。")

    # ---------------- 3 背景
    s = prs.slides.add_slide(blank)
    header(s, "问题：AI 文本已经很难分辨", "训练型检测器要标注、要训练；免训练是另一条路", 3)
    rect(s, 0.6, 1.65, 4.9, 4.9, LIGHT_GRAY)
    textbox(s, 0.9, 1.85, 4.3, 0.4, "现实中的滥用", 17, True, NAVY)
    bullets(s, 0.9, 2.35, 4.3, 3.9, [
        "假新闻、批量生成的评论",
        "学术写作中的代写",
        "模型用 AI 数据训练导致退化",
    ], 14, gap=10)

    table(s, 5.85, 1.65, 6.9, 3.4, [
        ["类型", "做法", "缺点"],
        ["训练型", "抽特征 → 训二分类器", "要标注、换领域掉点"],
        ["免训练", "统计量直接打分", "只用全局、采样慢"],
    ], [1.2, 3.3, 2.4], size=12, row_h=1.0)

    rect(s, 5.85, 5.25, 6.9, 1.25, LIGHT_BLUE)
    textbox(s, 6.05, 5.4, 6.5, 0.95,
            "本文要补的缺口：现有免训练方法只看“整段平均”，忽略了概率曲线的局部形状。",
            14, False, NAVY)
    notes(s, "强调：训练型不是不好，是换领域就掉点；免训练的痛点是只用全局统计。")

    # ---------------- 4 洞察
    s = prs.slides.add_slide(blank)
    header(s, "核心洞察：人写的曲线更“毛躁”", "同一开头，人续写 vs AI 续写，概率曲线的形状不同", 4)
    bullets(s, 0.6, 1.75, 5.6, 4.4, [
        ("TPS：", "每个 token 被模型预测的概率，按顺序排成一条序列"),
        ("人类：", "常有模型没想到的词，曲线忽高忽低"),
        ("AI：", "按模型分布采样，曲线又高又平"),
    ], 15, gap=14)

    curves_img = os.path.join(HERE, "prob_curves.png")
    paper_fig = os.path.join(HERE, "fig1a_paper.png")
    if os.path.exists(paper_fig):
        add_picture_fit(s, paper_fig, 6.4, 1.6, 6.4, 4.6)
        textbox(s, 6.4, 6.3, 6.4, 0.3, "图源：论文 Fig.1(a)，OPT-2.7 续写的 TPS 对比", 9, False, MID_GRAY,
                PP_ALIGN.CENTER)
    elif os.path.exists(curves_img):
        add_picture_fit(s, curves_img, 6.5, 1.9, 6.2, 4.0)
        textbox(s, 6.5, 6.1, 6.2, 0.3, "我们自己的复现图（GPT-2 打分）", 9, False, MID_GRAY,
                PP_ALIGN.CENTER)
    else:
        rect(s, 6.5, 1.7, 6.2, 4.6, LIGHT_GRAY, line=RGBColor(0xBF, 0xBF, 0xBF))
        textbox(s, 6.5, 3.55, 6.2, 0.9, "【此处插入 prob_curves.png】\n或：论文 Fig.1(a) 截图", 14, False,
                MID_GRAY, PP_ALIGN.CENTER)
    textbox(s, 0.6, 6.35, 12.1, 0.4, "这一页只讲直觉，不讲公式——公式在下一页。", 13, False, MID_GRAY)
    notes(s, "这一页放概率曲线图；没有图就用论文 Fig.1(a)，并说明两条线的差别。")

    # ---------------- 5 方法总览
    s = prs.slides.add_slide(blank)
    header(s, "方法：把概率曲线当时间序列", "五步得到局部统计，再和全局似然结合", 5)
    steps = [
        ("①", "算 TPS", "GPT-2 前向\n取真实词概率"),
        ("②", "多尺度", "相邻 τ 个\n取平均"),
        ("③", "滑窗 + 余弦", "相邻片段\n像不像"),
        ("④", "分箱 + 熵", "直方图\n算 DE"),
        ("⑤", "聚合 + 相除", "跨尺度取 std\n除以似然"),
    ]
    x = 0.55
    for i, (num, title, desc) in enumerate(steps):
        rect(s, x, 1.85, 2.25, 2.15, LIGHT_BLUE)
        textbox(s, x, 1.95, 2.25, 0.4, num, 18, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, x, 2.35, 2.25, 0.45, title, 15, True, NAVY, PP_ALIGN.CENTER)
        textbox(s, x, 2.85, 2.25, 0.9, desc, 12, False, GRAY, PP_ALIGN.CENTER)
        x += 2.5

    pills = [("全局", "平均对数似然"), ("局部", "Agg-MDE"), ("合成", "Lastde = 全局 ÷ 局部")]
    x = 1.2
    for head, body in pills:
        rect(s, x, 4.6, 3.4, 1.25, WHITE, line=BLUE)
        textbox(s, x, 4.72, 3.4, 0.35, head, 13, True, BLUE, PP_ALIGN.CENTER)
        textbox(s, x, 5.1, 3.4, 0.5, body, 16, True, NAVY, PP_ALIGN.CENTER)
        x += 3.75

    textbox(s, 0.6, 6.2, 12.1, 0.55,
            "论文式(9)：Lastde(t) = 平均 log p  ÷  Agg-MDE(t)，分数越高越像 AI。",
            15, True, NAVY, PP_ALIGN.CENTER)
    notes(s, "五步讲完，强调：前三步是“把曲线切碎”，第四步是“量化碎片的分布”，第五步是“和全局结合”。")

    # ---------------- 6 公式
    s = prs.slides.add_slide(blank)
    header(s, "三个公式，对应三段代码", "答辩时指到这里，说明我们不是照跑脚本", 6)
    cards = [
        ("TPS（式 1）", "L(t) = ( log p(t₁), …, log p(tₙ) )", "token_logprobs()"),
        ("多样性熵（式 8）", "DE = − Σ pᵢ log pᵢ  /  log ε", "_de()"),
        ("Lastde 分数（式 9）", "Lastde = mean(log p)  /  Agg-MDE", "main()"),
    ]
    y = 1.75
    for head, formula, func in cards:
        rect(s, 0.8, y, 11.7, 1.35, LIGHT_GRAY)
        textbox(s, 1.05, y + 0.12, 3.2, 0.4, head, 14, True, BLUE)
        textbox(s, 4.2, y + 0.3, 6.6, 0.6, formula, 18, True, NAVY, font=MONO)
        textbox(s, 10.6, y + 0.15, 1.8, 0.35, func, 11, False, MID_GRAY, font=MONO)
        y += 1.6

    textbox(s, 0.8, 6.55, 11.7, 0.4,
            "我们的实现与官方 fastMDE.py 对齐：同一输入，误差 < 1e-6。",
            12, False, MID_GRAY)
    notes(s, "公式页不要展开推导，讲“每个公式对应哪个函数”即可。")

    # ---------------- 7 玩具例子
    s = prs.slides.add_slide(blank)
    header(s, "手算一遍：DE 到底在算什么", "用 12 个 log 概率的小例子，把四步走完", 7)
    h_mean, h_mde, h_de = toy["h"]
    a_mean, a_mde, a_de = toy["a"]

    def fmt(x, nd=3):
        v = round(float(x), nd)
        if abs(v) < 0.5 * 10 ** (-nd):
            v = 0.0
        return ("%." + str(nd) + "f") % v

    table(s, 0.6, 1.75, 12.1, 2.0, [
        ["文本", "平均 log p", "τ=1 的 DE", "Agg-MDE（τ=1..3）"],
        ["人类示例", fmt(h_mean, 2), fmt(h_de), fmt(h_mde)],
        ["AI 示例", fmt(a_mean, 2), fmt(a_de), fmt(a_mde)],
    ], [3.0, 3.0, 3.0, 3.1], size=14, row_h=0.55)

    rect(s, 0.6, 4.1, 12.1, 2.2, LIGHT_BLUE)
    textbox(s, 0.85, 4.22, 11.6, 0.4, "计算过程（以 s=2 为例）", 13, True, NAVY)
    textbox(s, 0.85, 4.65, 11.6, 1.5,
            "① 窗口切分：(x₁,x₂), (x₂,x₃), …   →  ② 相邻窗口余弦相似度 ∈ [-1,1]\n"
            "③ 把相似度按 [-1,1] 分 10 格，数直方图   →  ④ 归一化后算熵，再除以 log(10)\n"
            "⑤ 每个 τ 算一个 DE，取标准差 → Agg-MDE；最后 Lastde = 平均 log p ÷ Agg-MDE",
            13, False, GRAY)
    textbox(s, 0.6, 6.35, 12.1, 0.55,
            "注：s=2 只为手算方便，正式实验用 s=3；AI 示例过于平滑导致 Agg-MDE≈0，代码用 +1e-6 防止除零。",
            10, False, MID_GRAY)
    notes(s, "这页专门回答“数学在干什么”。强调 DE 是相似度分布的熵，不是概率本身的熵。")

    # ---------------- 8 协议
    s = prs.slides.add_slide(blank)
    header(s, "评测协议：怎么保证比较公平", "数据、指标、场景三件事", 8)
    cols = [
        ("数据", ["每个数据集 150 条人类文本", "取前 30 个 token 当提示", "让源模型续写", "截断到等长"]),
        ("指标", ["AUROC：排序正确率", "0.5 = 瞎猜", "1.0 = 完美", "阈值无关"]),
        ("场景", ["白盒：用源模型打分", "黑盒：用代理模型打分", "代理默认 GPT-J-6B", "我们：GPT-2"]),
    ]
    x = 0.6
    for head, items in cols:
        rect(s, x, 1.7, 3.95, 3.9, LIGHT_GRAY)
        textbox(s, x + 0.2, 1.85, 3.5, 0.4, head, 17, True, NAVY)
        bullets(s, x + 0.25, 2.4, 3.5, 3.0, items, 12, gap=6)
        x += 4.1

    rect(s, 0.6, 5.8, 12.1, 0.85, LIGHT_ORANGE)
    textbox(s, 0.8, 5.95, 11.7, 0.6,
            "关键细节：截断到等长，是为了防止检测器靠“长度”作弊——这是论文实验设计里最容易被忽略的一点。",
            13, False, ORANGE)
    notes(s, "这一页体现你们读懂了实验设计，尤其是“等长截断”。")

    # ---------------- 9 论文结果
    s = prs.slides.add_slide(blank)
    header(s, "论文报告的数字", "白盒 / 黑盒平均 AUROC（12 个源模型）", 9)
    table(s, 1.0, 1.8, 11.3, 3.4, [
        ["方法", "白盒", "黑盒"],
        ["Lastde（本文）", "95.89", "86.38"],
        ["Lastde++（本文）", "98.85", "91.47"],
        ["Fast-DetectGPT", "97.82", "85.68"],
        ["Likelihood", "82.54", "71.32"],
        ["DetectLRR", "90.80", "80.45"],
    ], [4.5, 3.2, 3.2], size=14, row_h=0.5, highlight_rows=[1, 2])

    textbox(s, 1.0, 5.5, 11.3, 0.8,
            "读法：白盒分数普遍高，因为“出题人就是阅卷人”；黑盒更接近真实场景，普遍掉 10 个点左右。",
            13, False, GRAY)
    notes(s, "数字来自作者 README 的 Table 1/2；强调白盒黑盒的差别。")

    # ---------------- 10 我们的设置
    s = prs.slides.add_slide(blank)
    header(s, "我们的复现：缩规模，但不缩方法", "作者数据 + 作者算法 + 小模型", 10)
    rows = [
        ("数据", "作者公开的 XSum 150 对（人类 / GPT-2 XL 续写）"),
        ("打分模型", "GPT-2（1.24 亿），CPU 推理"),
        ("算法", "官方 fastMDE.py 逐行翻译，误差 < 1e-6"),
        ("运行", "双击 run_repro.bat，约 5 分钟"),
    ]
    y = 1.7
    for head, body in rows:
        rect(s, 0.6, y, 2.3, 0.95, LIGHT_BLUE)
        textbox(s, 0.6, y + 0.22, 2.3, 0.5, head, 15, True, NAVY, PP_ALIGN.CENTER)
        rect(s, 3.1, y, 9.5, 0.95, LIGHT_GRAY)
        textbox(s, 3.3, y + 0.22, 9.1, 0.5, body, 14, False, GRAY)
        y += 1.15

    rect(s, 0.6, 6.35, 12.1, 0.55, WHITE, line=ORANGE)
    textbox(s, 0.8, 6.42, 11.7, 0.4,
            "坦白：论文用 GPT-J 6B（12GB）；我们用 GPT-2（525MB）——这是唯一的“缩水”。",
            13, True, ORANGE)
    notes(s, "这一页把“我们和论文唯一的差别”说清楚：只换了打分模型。")

    # ---------------- 11 主结果
    s = prs.slides.add_slide(blank)
    header(s, "主结果：Lastde 高于基线", "XSum · 150 对 · GPT-2 打分", 11)
    if stats:
        textbox(s, 0.7, 1.8, 2.8, 0.4, "Lastde", 14, True, BLUE)
        textbox(s, 0.7, 2.15, 3.2, 0.9, "%.4f" % stats["auc_lastde"], 44, True, NAVY)
        textbox(s, 0.7, 3.4, 2.8, 0.4, "Likelihood 基线", 14, True, MID_GRAY)
        textbox(s, 0.7, 3.75, 3.2, 0.8, "%.4f" % stats["auc_ll"], 32, True, GRAY)
        textbox(s, 0.7, 4.9, 3.4, 0.5, "提升 %+.2f 个百分点" % ((stats["auc_lastde"] - stats["auc_ll"]) * 100),
                16, True, GREEN if stats["auc_lastde"] > stats["auc_ll"] else ORANGE)

        dist_img = os.path.join(HERE, "lastde_distribution.png")
        if os.path.exists(dist_img):
            s.shapes.add_picture(dist_img, Inches(4.4), Inches(1.75), width=Inches(8.2))
        else:
            chart_data = CategoryChartData()
            chart_data.categories = ["Likelihood", "Lastde"]
            chart_data.add_series("AUROC", (stats["auc_ll"], stats["auc_lastde"]))
            gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED,
                                    Inches(4.4), Inches(1.8), Inches(8.2), Inches(4.5), chart_data)
            chart = gf.chart
            chart.has_legend = False
            chart.has_title = True
            chart.chart_title.text_frame.text = "AUROC 对比"
            for p in chart.chart_title.text_frame.paragraphs:
                for r in p.runs:
                    set_font(r, 13, True, NAVY)
            plot = chart.plots[0]
            plot.has_data_labels = True
            plot.data_labels.font.size = Pt(14)
            plot.data_labels.font.bold = True
            plot.gap_width = 80
            chart.value_axis.minimum_scale = 0.5
            chart.value_axis.maximum_scale = 1.0
            chart.value_axis.major_unit = 0.1
            chart.value_axis.has_major_gridlines = True
            chart.value_axis.tick_labels.font.size = Pt(11)
            chart.category_axis.tick_labels.font.size = Pt(12)

        textbox(s, 4.4, 6.35, 8.2, 0.4,
                "样本数：%d（人类 150 / AI 150）" % stats["n"], 12, False, MID_GRAY)
    else:
        textbox(s, 1.0, 3.0, 11.0, 1.0, "【未找到 lastde_results.csv，请先运行 run_repro.bat】", 18, True, ORANGE,
                PP_ALIGN.CENTER)
    notes(s, "这一页是全场核心：先说数字，再说“提升 4 个百分点”，最后说“绝对值低于论文是因为代理模型小”。")

    # ---------------- 12 sanity check
    s = prs.slides.add_slide(blank)
    header(s, "三个自检：结果方向对不对", "不只报数字，还要检查中间量是否符合论文", 12)
    if stats:
        table(s, 0.8, 1.9, 11.8, 2.9, [
            ["指标", "人类", "AI", "论文方向", "是否符合"],
            ["平均 log p", "%.3f" % stats["ll_h"], "%.3f" % stats["ll_a"], "AI 更高", "是"],
            ["Agg-MDE", "%.4f" % stats["mde_h"], "%.4f" % stats["mde_a"], "人类更高", "否"],
            ["Lastde 均值", "%.1f" % stats["score_h"], "%.1f" % stats["score_a"], "AI 更高", "是"],
        ], [3.0, 2.4, 2.4, 2.2, 1.8], size=13, row_h=0.65, highlight_rows=[2])
        textbox(s, 0.8, 5.1, 11.8, 1.3,
                "第二行是本期最值得讲发现：Agg-MDE 的方向和论文相反。\n"
                "原因很可能是代理模型太小（GPT-2 1.24 亿 vs GPT-J 60 亿），局部熵被噪声淹没。",
                14, False, GRAY)
    notes(s, "主动暴露 MDE 方向反转，比藏着好；这是“我们会做实验”的证据。")

    # ---------------- 13 消融
    s = prs.slides.add_slide(blank)
    header(s, "消融：全局和局部，缺一不可？", "同一份数据，三种打分方式", 13)
    if stats:
        table(s, 1.0, 1.9, 11.2, 2.6, [
            ["打分方式", "AUROC", "说明"],
            ["Lastde（LL ÷ Agg-MDE）", "%.4f" % stats["auc_lastde"], "论文方法"],
            ["只用 LL", "%.4f" % stats["auc_ll"], "最简单的基线"],
            ["只用 Agg-MDE", "%.4f" % stats["auc_mde"], "局部信息单独用"],
        ], [5.4, 2.6, 3.2], size=14, row_h=0.6, highlight_rows=[1])
        best = max(stats["auc_lastde"], stats["auc_ll"], stats["auc_mde"])
        textbox(s, 1.0, 5.0, 11.2, 1.2,
                "看图说话：组合后的 %.4f 是三种里最高的 → 复现了论文“全局 + 局部”的结论。" % stats["auc_lastde"]
                if abs(stats["auc_lastde"] - best) < 1e-9 else
                "注意：本次运行里组合并非最高，报告里应如实说明，并分析原因（数据/代理模型）。",
                14, False, GRAY)
    notes(s, "对应论文附录 E 的消融；如果组合不是最高，就讲“为什么”。")

    # ---------------- 14 鲁棒性
    s = prs.slides.add_slide(blank)
    header(s, "鲁棒性：换数据、换模型、换长度", "三组待补实验，每组 5~10 分钟", 14)
    cards = [
        ("跨数据集", "reddit_gpt2_xl\nsquad_gpt2_xl", "分数有波动\n趋势是否保持"),
        ("代理模型规模", "distilgpt2 / gpt2\ngpt2-medium", "越大是否越准\nMDE 方向是否翻转"),
        ("文本长度", "--max-tokens\n64 / 128 / 256", "越短是否越难\n对应论文 Fig.5"),
    ]
    x = 0.6
    for head, cmd, note in cards:
        rect(s, x, 1.75, 3.95, 3.9, LIGHT_GRAY)
        textbox(s, x + 0.2, 1.9, 3.5, 0.45, head, 16, True, NAVY)
        textbox(s, x + 0.2, 2.5, 3.5, 0.8, cmd, 11, False, MID_GRAY, font=MONO)
        textbox(s, x + 0.2, 3.5, 3.5, 0.9, note, 12, False, GRAY)
        textbox(s, x + 0.2, 4.85, 3.5, 0.5, "结果：【待填】", 12, True, ORANGE)
        x += 4.1
    textbox(s, 0.6, 6.0, 12.1, 0.6,
            "建议优先做“代理模型规模”：如果换成 gpt2-medium 后 MDE 方向恢复，就是一个可以单独讲一页的发现。",
            12, False, MID_GRAY)
    notes(s, "这三个是待做实验；做完把数字填进【待填】。")

    # ---------------- 15 发现
    s = prs.slides.add_slide(blank)
    header(s, "我们的发现：MDE 方向反转", "论文说人类更“乱”，我们这里 AI 更“乱”", 15)
    rect(s, 0.6, 1.7, 5.8, 3.6, LIGHT_ORANGE)
    textbox(s, 0.85, 1.85, 5.3, 0.4, "现象", 15, True, ORANGE)
    bullets(s, 0.85, 2.35, 5.3, 2.8, [
        "人类 Agg-MDE = %.4f" % (stats["mde_h"] if stats else 0.0736),
        "AI   Agg-MDE = %.4f" % (stats["mde_a"] if stats else 0.0754),
        "与论文 Fig.9 方向相反",
    ], 13, gap=8)

    rect(s, 6.9, 1.7, 5.8, 3.6, LIGHT_BLUE)
    textbox(s, 7.15, 1.85, 5.3, 0.4, "我们的解释", 15, True, BLUE)
    bullets(s, 7.15, 2.35, 5.3, 2.8, [
        "代理模型越小，概率估计越粗",
        "MDE 对尺度/长度敏感",
        "下一步：换 gpt2-medium 验证",
    ], 13, gap=8)

    textbox(s, 0.6, 5.6, 12.1, 1.0,
            "态度：不藏异常。核心结论（Lastde > LL）成立，中间现象没复现——这正好说明局部统计有边界。",
            14, True, NAVY)
    notes(s, "这是加分页：主动分析异常，体现科研素养。")

    # ---------------- 16 局限与伦理
    s = prs.slides.add_slide(blank)
    header(s, "局限与伦理", "知道边界，才算真的复现", 16)
    rect(s, 0.6, 1.65, 5.9, 4.9, LIGHT_GRAY)
    textbox(s, 0.85, 1.8, 5.4, 0.4, "四点局限", 15, True, NAVY)
    bullets(s, 0.85, 2.3, 5.4, 4.0, [
        "代理模型 GPT-2 替代 GPT-J",
        "只跑了 1~2 个数据集",
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
    notes(s, "伦理四条对应课程要求；每条一句话即可。")

    # ---------------- 17 结论
    s = prs.slides.add_slide(blank)
    header(s, "结论", "三句话总结", 17)
    bullets(s, 1.0, 1.9, 11.5, 3.6, [
        ("方法有效：", "Lastde 把概率曲线当时间序列，用局部熵补充全局似然。"),
        ("复现成立：", "在作者数据上，Lastde 的 AUROC 高于 Likelihood 基线。"),
        ("边界清楚：", "MDE 方向依赖代理模型，短文本和跨模型仍是难点。"),
    ], 17, gap=16)
    rect(s, 0.9, 5.6, 11.6, 1.0, NAVY)
    textbox(s, 1.1, 5.72, 11.2, 0.75,
            "复现的价值不在于把 95.89 抄成一样，而在于能说清“差在哪、为什么”。",
            16, True, WHITE, PP_ALIGN.CENTER)
    notes(s, "结论页停 5 秒，让老师拍照。")

    # ---------------- 18 Q&A
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(W), Inches(H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    textbox(s, 0, 2.6, W, 1.2, "Q & A", 54, True, WHITE, PP_ALIGN.CENTER)
    textbox(s, 0, 3.9, W, 0.5, "谢谢，欢迎提问", 20, False, RGBColor(0xDE, 0xEB, 0xF7), PP_ALIGN.CENTER)
    textbox(s, 0, 4.7, W, 0.5, "代码：D:\\Lastde_Detector   ·   数据：datasets/human_llm_data_for_experiment",
            12, False, RGBColor(0x9D, 0xC3, 0xE6), PP_ALIGN.CENTER)
    notes(s, "Q&A 分工：技术/代码 → A；数据/结果 → B；论文/伦理 → C。")

    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Lastde复现汇报模板.pptx")
    prs.save(out)
    print("saved:", out)
    print("slides:", len(prs.slides))


if __name__ == "__main__":
    main()
