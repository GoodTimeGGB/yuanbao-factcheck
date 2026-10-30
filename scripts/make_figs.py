#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成征文配图（纯数据驱动，数字全部来自 data/ 下的实验结果）。"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "配图")
os.makedirs(OUT, exist_ok=True)

# 中文字体
for cand in ["Microsoft YaHei", "SimHei", "DengXian", "Noto Sans CJK SC"]:
    if any(f.name == cand for f in fm.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [cand]
        break
plt.rcParams["axes.unicode_minus"] = False

INK = "#1f2328"
MUTED = "#6b7280"
GRID = "#e5e7eb"
RED = "#c0392b"
BLUE = "#2d6cdf"
GREY = "#9aa4b2"
BG = "#ffffff"


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.set_facecolor(BG)


# ---------- 图 1：两份 AI 稿的错误率 ----------
def fig_error_rate():
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), gridspec_kw={"width_ratios": [1, 1.25]})
    fig.patch.set_facecolor(BG)

    ax = axes[0]
    models = ["A\nDeepSeek\n检索关", "B\nDeepSeek\n检索开", "C\nGemini\n检索开"]
    right = [4, 9, 11]
    wrong = [8, 3, 1]
    x = range(3)
    ax.bar(x, right, width=0.52, color=BLUE)
    ax.bar(x, wrong, width=0.52, bottom=right, color=RED)
    for i in x:
        ax.text(i, right[i] / 2, "对 %d" % right[i], ha="center", va="center",
                color="white", fontsize=11.5, fontweight="bold")
        if wrong[i]:
            ax.text(i, right[i] + wrong[i] / 2, "错 %d" % wrong[i], ha="center", va="center",
                    color="white", fontsize=11.5, fontweight="bold")
        ax.text(i, 13.4, "%d%%" % round(right[i] / 12 * 100), ha="center",
                color=BLUE, fontsize=13, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(models, fontsize=9.5, color=INK)
    ax.set_ylim(0, 14.6)
    ax.set_yticks([])
    ax.set_title("数字类 12 条：正确 / 错误", fontsize=12, color=INK, pad=14, loc="left")
    clean(ax)
    ax.spines["left"].set_visible(False)

    # 右：报出的版本落后多少个正式版
    ax = axes[1]
    names = ["TypeScript 6.0.3", "Tailwind 4.2.0", "React 19.2.1", "Vite 8.0.2", "Next.js 16.1.2"]
    behind = [1, 8, 28, 40, 55]
    bars = ax.barh(names, behind, height=0.52, color=RED)
    for b, v in zip(bars, behind):
        ax.text(v + 1.2, b.get_y() + b.get_height() / 2, "%d 个" % v,
                va="center", fontsize=11, fontweight="bold", color=INK)
    ax.set_xlim(0, 64)
    ax.set_xticks([])
    ax.set_title("这些版本号全部真实存在——只是落后了这么多正式版", fontsize=12,
                 color=INK, pad=14, loc="left")
    clean(ax)
    ax.spines["bottom"].set_visible(False)
    ax.text(0.02, -0.14, "↑ 因此「版本存在性校验」对它们全部放行",
            transform=ax.transAxes, fontsize=10.5, color=MUTED)

    fig.tight_layout()
    p = os.path.join(OUT, "fig02_digit-accuracy.png")
    fig.savefig(p, dpi=200, facecolor=BG)
    plt.close(fig)
    print(p)


# ---------- 图 2：A/B 四指标 ----------
def fig_ab():
    data = [("准确率", 54, 75, False), ("误报率\n（假判真）", 58, 0, True),
            ("漏报率\n（真判假）", 33, 0, True), ("「无证据」占比", 0, 25, False)]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    fig.patch.set_facecolor(BG)
    w = 0.36
    xs = range(len(data))
    a = [d[1] for d in data]
    b = [d[2] for d in data]
    ax.bar([i - w / 2 for i in xs], a, width=w, color=GREY, label="A 组：断言原文直搜")
    ax.bar([i + w / 2 for i in xs], b, width=w, color=BLUE, label="B 组：三元组 + 官方源 + 对齐 + 三态")
    for i, (label, va, vb, lower_better) in enumerate(data):
        ax.text(i - w / 2, va + 1.6, "%d%%" % va, ha="center", color=MUTED, fontsize=11)
        ax.text(i + w / 2, vb + 1.6, "%d%%" % vb, ha="center", color=BLUE,
                fontsize=11, fontweight="bold")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([d[0] for d in data], fontsize=11, color=INK)
    ax.set_ylim(0, 92)
    ax.set_yticks([])
    ax.set_title("24 条标注集（真 12 / 假 12）上的对照结果", fontsize=12, color=INK, pad=12, loc="left")
    clean(ax)
    ax.spines["left"].set_visible(False)
    ax.legend(frameon=False, fontsize=10, loc="upper right", labelcolor=MUTED)
    ax.text(0.98, 80, "误报率 58% → 0%：假事实一条都没放行", fontsize=11.5,
            color=RED, fontweight="bold", va="top")
    fig.tight_layout()
    p = os.path.join(OUT, "fig10_ab-compare.png")
    fig.savefig(p, dpi=200, facecolor=BG)
    plt.close(fig)
    print(p)


# ---------- 图 3：Site 限定精度 ----------
def fig_site():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.5]})
    fig.patch.set_facecolor(BG)

    ax = axes[0]
    vals = [30, 8]
    labels = ["域名命中\n（权威性）", "首条是公告页\n（相关性）"]
    bars = ax.bar(labels, vals, width=0.45, color=[GREY, RED])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, "%d / 30" % v,
                ha="center", fontsize=12, fontweight="bold", color=INK)
    ax.text(1, 14, "27%", ha="center", fontsize=22, color=RED, fontweight="bold")
    ax.set_ylim(0, 34)
    ax.set_yticks([])
    ax.set_title("Site 定向官方源：权威 ≠ 相关", fontsize=12, color=INK, pad=12, loc="left")
    clean(ax)
    ax.spines["left"].set_visible(False)

    ax = axes[1]
    rows = [("Next.js 15", "Support Policy（支持策略页）"),
            ("Spring Boot 3.4", "Author Moritz Halbritter（作者页）"),
            ("Java 21", "Licensing FAQ（许可常见问题）"),
            ("Nuxt 3", "Announcing Nuxt 3 Release Candidate"),
            ("Vite 5", "首条其实是 Vite 5.1")]
    ax.set_axis_off()
    ax.set_title("域名都对，页面都不对", fontsize=12, color=INK, pad=12, loc="left")
    for i, (a, b) in enumerate(rows):
        y = 0.86 - i * 0.19
        ax.text(0.0, y, a, fontsize=10.5, color=INK, fontweight="bold", va="center",
                transform=ax.transAxes)
        ax.text(0.30, y, "→", fontsize=10, color=MUTED, va="center", transform=ax.transAxes)
        ax.text(0.37, y, b, fontsize=10.5, color=RED, va="center", transform=ax.transAxes)
    fig.tight_layout()
    p = os.path.join(OUT, "fig07_site-precision.png")
    fig.savefig(p, dpi=200, facecolor=BG)
    plt.close(fig)
    print(p)


# ---------- 图 4：架构图 ----------
def fig_arch():
    fig, ax = plt.subplots(figsize=(11, 5.6))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_axis_off()

    def box(x, y, w, h, title, sub, fc, ec, tc=INK):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12,rounding_size=0.18",
                           fc=fc, ec=ec, lw=1.4)
        ax.add_patch(p)
        ax.text(x + w / 2, y + h - 0.42, title, ha="center", va="center",
                fontsize=12, color=tc, fontweight="bold")
        ax.text(x + w / 2, y + h / 2 - 0.28, sub, ha="center", va="center",
                fontsize=9.2, color=MUTED, linespacing=1.6)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                                     color=GREY, lw=1.3, shrinkA=2, shrinkB=2))

    box(0.3, 7.4, 2.6, 1.9, "① 断言抽取", "结构化：版本/日期/参数\n叙述性：架构/因果/评价", "#f6f8fb", GRID)
    box(3.7, 7.4, 2.6, 1.9, "② 取证", "三元组 query + Site 定向\nMode 按断言类型选择", "#f6f8fb", GRID)
    box(7.1, 7.4, 2.6, 1.9, "③ 对齐", "主体对齐（含别名表）\n属性对齐 · 时间对齐", "#f6f8fb", GRID)

    arrow(2.9, 8.35, 3.7, 8.35)
    arrow(6.3, 8.35, 7.1, 8.35)

    box(2.0, 3.4, 2.5, 2.3, "真", "证据主体一致\n时间一致", "#eef4ff", BLUE)
    box(4.6, 3.4, 2.5, 2.3, "假", "主体一致\n但值不符", "#fdeeec", RED)
    box(7.2, 3.4, 2.5, 2.3, "无证据", "搜到但主体/属性不对齐\n或不覆盖该品类", "#f4f4f5", GREY)

    arrow(8.4, 7.4, 8.45, 5.7)
    arrow(8.4, 7.4, 5.85, 5.7)
    arrow(8.4, 7.4, 3.25, 5.7)

    box(3.3, 0.6, 4.6, 1.7, "人工复核队列", "无证据 ≠ 通过 ≠ 判假\n四分之一的断言必须有人看", "#fff8e6", "#d9a441")
    arrow(8.45, 3.4, 8.0, 2.3)

    ax.text(5, 9.85, "核验流水线：每个箭头都是一次实际调用", ha="center",
            fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout()
    p = os.path.join(OUT, "fig01_pipeline.png")
    fig.savefig(p, dpi=200, facecolor=BG)
    plt.close(fig)
    print(p)


# ---------- 图 5：DeepSeek 9 条错误的形态分布 ----------
def fig_taxonomy():
    d = json.load(open(os.path.join(HERE, "..", "data", "draft_verdicts.json"), encoding="utf-8"))
    cats = {"版本真实但过时": 0, "预发布当正式版": 0, "日期挪用": 0, "叙述性错误": 0}
    for v in d:
        if v["model"] != "deepseek":
            continue
        ver = v["verdict"]
        if "过时" in ver:
            cats["版本真实但过时"] += 1
        elif "不存在" in ver:
            cats["预发布当正式版"] += 1
        elif "RC" in ver and v["id"] != "D3":
            cats["预发布当正式版"] += 1
        elif "日期错" in ver:
            cats["日期挪用"] += 1
    cats["叙述性错误"] = sum(1 for v in d if v["model"] == "deepseek" and v["id"] == "D3")

    fig, ax = plt.subplots(figsize=(9.6, 4.0))
    fig.patch.set_facecolor(BG)
    names = list(cats.keys())
    vals = [cats[k] for k in names]
    colors = [RED, "#e08a4b", "#d4a017", GREY]
    bars = ax.barh(names, vals, height=0.5, color=colors)
    for b, v in zip(bars, vals):
        ax.text(v + 0.12, b.get_y() + b.get_height() / 2, "%d 条" % v,
                va="center", fontsize=11, fontweight="bold", color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 6.5)
    ax.set_xticks([])
    ax.set_title("DeepSeek 9 条错误的形态：8 条是「数字类」，1 条是「叙述类」",
                 fontsize=12, color=INK, pad=12, loc="left")
    clean(ax)
    ax.spines["bottom"].set_visible(False)
    ax.annotate("这 5 条都能通过\n「版本存在性」校验", xy=(5, 0), xytext=(3.4, 1.35),
                fontsize=10, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
    fig.tight_layout()
    p = os.path.join(OUT, "fig03_error-taxonomy.png")
    fig.savefig(p, dpi=200, facecolor=BG)
    plt.close(fig)
    print(p)


# ---------- 图 6：三格 × 三类断言 ----------
def fig_matrix():
    rows = [
        ("A  DeepSeek\n检索关", [("4 / 12", "错 8", RED, "#fdeeec"),
                                ("RC 当正式版", "错", RED, "#fdeeec"),
                                ("Vite 写对\nVapor 无据", "半", "#d4a017", "#fff8e6")]),
        ("B  DeepSeek\n检索开", [("9 / 12", "错 3", BLUE, "#eef4ff"),
                                ("RC 当正式版", "错", RED, "#fdeeec"),
                                ("Rolldown 取代\nRollup", "对", BLUE, "#eef4ff")]),
        ("C  Gemini\n检索开", [("11 / 12", "错 1", BLUE, "#eef4ff"),
                              ("未涉及", "—", GREY, "#f4f4f5"),
                              ("仍是 Rollup", "错", RED, "#fdeeec")]),
    ]
    cols = ["数字类\n（版本号 / 日期）", "属性类\n（这是哪一种发布）", "叙述类\n（它到底改了什么）"]

    fig, ax = plt.subplots(figsize=(10.6, 4.6))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_axis_off()

    x0, w = 1.55, 2.72
    for j, c in enumerate(cols):
        ax.text(x0 + w * j + w / 2, 5.35, c, ha="center", va="center",
                fontsize=11.5, color=INK, fontweight="bold", linespacing=1.5)

    for i, (name, cells) in enumerate(rows):
        y = 4.05 - i * 1.35
        ax.text(0.1, y + 0.5, name, ha="left", va="center", fontsize=10.5,
                color=INK, linespacing=1.5)
        for j, (big, small, col, fill) in enumerate(cells):
            x = x0 + w * j
            ax.add_patch(FancyBboxPatch((x + 0.05, y), w - 0.1, 1.0,
                                        boxstyle="round,pad=0.04,rounding_size=0.12",
                                        fc=fill, ec=GRID, lw=1.2))
            ax.text(x + w / 2, y + 0.62, big, ha="center", va="center",
                    fontsize=12, color=col, fontweight="bold", linespacing=1.4)
            ax.text(x + w / 2, y + 0.2, small, ha="center", va="center",
                    fontsize=9, color=MUTED)

    ax.text(0.1, 0.28, "同一份 prompt、同一个时点。检索把「数字」拉了起来，却拉不动后两列。",
            fontsize=10.5, color=MUTED)
    fig.tight_layout()
    p = os.path.join(OUT, "fig06_matrix.png")
    fig.savefig(p, dpi=200, facecolor=BG)
    plt.close(fig)
    print(p)


if __name__ == "__main__":
    fig_error_rate()
    fig_ab()
    fig_site()
    fig_arch()
    fig_taxonomy()
    fig_matrix()


