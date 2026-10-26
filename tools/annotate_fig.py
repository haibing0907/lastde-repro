# -*- coding: utf-8 -*-
"""生成一张“怎么读 Fig.1(a)”的说明图：左边原图，右边四条注解。"""

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fig1a_paper.png")
OUT = os.path.join(HERE, "fig1a_howto.png")

NAVY = (31, 56, 100)
ORANGE = (197, 90, 17)
GREEN = (0, 128, 96)
GRAY = (70, 70, 70)
LIGHT = (242, 242, 242)

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def f(size, bold=False):
    path = FONT_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def main():
    fig = Image.open(SRC).convert("RGB")
    fh = 660
    fw = int(fig.width * fh / fig.height)
    fig = fig.resize((fw, fh), Image.LANCZOS)

    pad = 30
    panel_w = 720
    W = pad + fw + 30 + panel_w + pad
    H = fh + 2 * pad
    img = Image.new("RGB", (W, H), (255, 255, 255))
    img.paste(fig, (pad, pad))

    d = ImageDraw.Draw(img)
    x0 = pad + fw + 30
    y = pad + 4

    d.text((x0, y), "怎么读这张图", font=f(30, True), fill=NAVY)
    y += 52

    items = [
        ("①", "每个点 = 一个 token",
         "横轴是第几个词；纵轴是模型给它的 log 概率。", NAVY),
        ("②", "log 概率是什么",
         "p 是模型猜中这个词的概率，log p 就是取对数：\n"
         "p=1 → 0；p=0.14 → -2；p=0.0000008 → -14。", ORANGE),
        ("③", "竖线是什么",
         "只是把相邻两个点连起来，不是误差棒、也不是置信区间。\n"
         "200 多个 token 挤在一小段横轴上，所以看起来特别陡。", GRAY),
        ("④", "向下的尖刺是什么",
         "某个词模型几乎没想到（概率极低），\n"
         "先骤降、再回升，就形成一个尖刺。", GREEN),
    ]

    for num, head, body, color in items:
        d.text((x0, y), num + " " + head, font=f(22, True), fill=color)
        y += 34
        for line in body.split("\n"):
            d.text((x0 + 26, y), line, font=f(18), fill=GRAY)
            y += 28
        y += 22

    # bottom conclusion box
    box_y = H - pad - 150
    d.rounded_rectangle([x0, box_y, W - pad, H - pad], radius=14, fill=LIGHT)
    d.text((x0 + 18, box_y + 14), "一句话结论", font=f(20, True), fill=NAVY)
    d.text((x0 + 18, box_y + 48), "橙色尖刺多 → 人写得更“意外”；", font=f(18), fill=ORANGE)
    d.text((x0 + 18, box_y + 78), "绿色贴着顶 → AI 写得更“顺”。", font=f(18), fill=GREEN)
    d.text((x0 + 18, box_y + 110), "数据：OPT-2.7 对同一 30-token 前缀的两种续写打分", font=f(14), fill=GRAY)

    img.save(OUT)
    print("saved", OUT, img.size)


if __name__ == "__main__":
    main()
