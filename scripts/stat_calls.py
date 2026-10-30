#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 data/calls.jsonl 汇总成一张可截图的统计表。"""
import json
import os
import statistics
import unicodedata
from collections import Counter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LOG = os.path.join(ROOT, "data", "calls.jsonl")

TAG_CN = {
    "probe_mode": "Mode 边界探针",
    "harvest_truth": "真值采集（30 实体）",
    "refine_truth": "真值二次精化",
    "gen_claims": "标注集生成",
    "cmp_A": "对照组：断言原文直搜",
    "cmp_B": "本文做法：三元组+官方域",
    "probe_claims": "三级策略预实验",
    "why_unknown": "无证据成因排查",
    "draft_feature": "稿件特性断言核验",
    "confirm": "官方原文确认",
    "verify": "人工核验",
    "debug": "调试",
    "cli": "命令行单次调用",
    "ds2_feature": "第 3 篇 特性断言核验",
    "trace_one": "单条断言全链路追踪",
}


def dw(s):
    """终端显示宽度：中日韩全角字符算 2 格"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s, w):
    return s + " " * max(0, w - dw(s))


def main():
    rows = [json.loads(l) for l in open(LOG, encoding="utf-8")]
    print("元宝搜索 SearchPro 调用统计")
    print("数据源：data/calls.jsonl    采集：2026-10-30\n")
    print(pad("用途", 30) + pad("调用", 6) + pad("失败", 6) + pad("零结果", 8) + pad("中位耗时", 10))
    print("-" * 62)
    for tag, n in Counter(r["tag"] for r in rows).most_common():
        sub = [r for r in rows if r["tag"] == tag]
        ms = statistics.median([r["elapsed_ms"] for r in sub])
        print(pad(TAG_CN.get(tag, tag), 30) + pad(str(n), 6)
              + pad(str(sum(1 for r in sub if not r["ok"])), 6)
              + pad(str(sum(1 for r in sub if r["ok"] and r["n_results"] == 0)), 8)
              + pad("%dms" % ms, 10))
    print("-" * 62)
    ms = sorted(r["elapsed_ms"] for r in rows)
    print(pad("合计", 30) + pad(str(len(rows)), 6)
          + pad(str(sum(1 for r in rows if not r["ok"])), 6)
          + pad(str(sum(1 for r in rows if r["ok"] and r["n_results"] == 0)), 8)
          + pad("%dms" % statistics.median(ms), 10))
    print("\nP90 耗时 %d ms  |  最大 %d ms  |  额度剩余 %d / 6000"
          % (ms[int(len(ms) * 0.9)], ms[-1], 6000 - len(rows)))


if __name__ == "__main__":
    main()
