#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把真实命令输出渲染成截图（终端卡片风格）。

注意：产物文件名带 render_ 前缀，正文用的是真实系统截图，不要直接覆盖。

所有内容均来自真实执行结果，不做任何修饰；只在关键行加底纹。
"""
import datetime
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "配图")
FONTS = [("C:/Windows/Fonts/simsun.ttc", 1), ("C:/Windows/Fonts/msyh.ttc", 0),
         ("C:/Windows/Fonts/consola.ttf", 0)]

BG = (28, 28, 30)
BAR = (44, 44, 48)
FG = (216, 216, 220)
DIM = (140, 140, 148)
GREEN = (126, 200, 120)
RED = (240, 120, 110)
YELLOW = (230, 190, 100)
BLUE = (130, 175, 245)
SEL = (72, 34, 34)


def font(size=15):
    for path, idx in FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()


def color_of(line):
    s = line.strip()
    if s.startswith(">>>"):
        return GREEN
    if s.startswith("$"):
        return BLUE
    if s.startswith("✗") or "假（" in s:
        return RED
    if s.startswith("·") or s.startswith("↑"):
        return YELLOW
    if s.startswith("[") and "/4]" in s:
        return BLUE
    if s.startswith("      ") or s.startswith("        "):
        return FG
    return FG


def render(title, cmd, body, out_name, sel=None, footer="2026-10-30  ·  元宝搜索 SearchPro 实测记录"):
    f = font(15)
    fb = font(13)
    lh = 25
    pad = 30
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    wmax = max(tmp.textlength(l, font=f) for l in [cmd] + body)
    W = int(max(760, wmax + pad * 2 + 20))
    H = pad * 2 + 46 + lh * (len(body) + 2) + 26

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 44], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 22, 15, 30 + i * 22, 29], fill=c)
    d.text((100, 14), title, font=fb, fill=(180, 180, 186))

    y = pad + 46
    d.text((pad, y), cmd, font=f, fill=BLUE)
    y += lh + 4

    for line in body:
        if sel and any(k in line for k in sel):
            d.rounded_rectangle([pad - 10, y - 3, W - pad + 6, y + lh - 6],
                                radius=6, fill=SEL)
        d.text((pad, y), line, font=f, fill=color_of(line))
        y += lh

    d.text((pad, H - 22), footer, font=fb, fill=DIM)
    p = os.path.join(OUT, out_name)
    img.save(p, quality=95)
    print(p)


def main():
    # ---------- 截图 1：npm view vue dist-tags ----------
    try:
        r = subprocess.run(["npm", "view", "vue", "dist-tags"],
                           capture_output=True, text=True, timeout=90, shell=True)
        npm_out = r.stdout.strip().splitlines()
    except Exception as e:
        npm_out = ["(npm 执行失败: %s)" % e]
    body = [""] + npm_out + ["", "  ↑ 3.6 线只有 alpha / beta / rc，latest 仍是 3.5.44"]
    render("命令提示符  —  npm view vue dist-tags",
           "$ npm view vue dist-tags", body, "render_fig04_npm-dist-tags.png",
           sel=["latest: '3.5.44'", "rc: '3.6.0-rc.13'"])

    # ---------- 截图 3：调用统计 ----------
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "stat_calls.py")],
                       capture_output=True, text=True, encoding="utf-8", shell=False)
    stat = [l.rstrip() for l in (r.stdout or "").strip().splitlines()]
    render("命令提示符  —  python scripts/stat_calls.py",
           "$ python scripts/stat_calls.py", [""] + stat,
           "render_fig08_call-stats.png", sel=["合计"])

    # ---------- 截图 4：单条断言全链路 ----------
    tp = os.path.join(ROOT, "data", "trace_vue.txt")
    trace = open(tp, encoding="utf-8").read().strip().splitlines()
    if trace and trace[0].startswith("$"):
        trace = trace[1:]          # 第一行是命令行，下面单独画
    render("命令提示符  —  python scripts/trace_one.py",
           "$ python scripts/trace_one.py", [""] + trace,
           "render_fig09_trace.png",
           sel=["[4/4]", "时间对齐："], footer="2026-10-30  ·  一次真实调用的完整中间结果")


if __name__ == "__main__":
    main()
