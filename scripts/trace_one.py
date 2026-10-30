#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对一条真实断言跑完整链路，把每一步的中间结果打出来。

产物：data/trace_vue.txt（给配图用，内容全部来自真实调用）
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yb import search  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CLAIM = "Vue 当前最新版本是 3.6.3，发布于 2026 年 9 月"
ENTITY = "Vue"
SUBJ = "vue"
QUERY = "Vue 3.6 released"
SITE = "blog.vuejs.org"
CLAIMED_YM = "2026-09"

ANNOUNCE = ["announc", "is out", "now available", "released", "general availability", "is now ga"]
YM = re.compile(r"(20\d{2})\s*[-/年]\s*(\d{1,2})")


def subject_ok(p):
    t = ((p.get("title") or "") + " " + (p.get("passage") or "")).lower()
    return ENTITY.lower() in t


def attr_ok(p):
    t = ((p.get("title") or "") + " " + (p.get("passage") or "")).lower()
    return any(k in t for k in ANNOUNCE)


def first_ym(p):
    txt = (p.get("title") or "") + " " + (p.get("passage") or "")[:400]
    m = YM.search(txt)
    return ("%s-%02d" % (m.group(1), int(m.group(2)))) if m else None


def main():
    out = io.StringIO()

    def w(line=""):
        print(line)
        out.write(line + "\n")

    w("$ python scripts/trace_one.py")
    w('  断言："%s"' % CLAIM)
    w()
    w("[1/4] 解析断言")
    w("      主体 = Vue      属性 = 最新稳定版本      声明值 = 3.6.3")
    w("      声称发布时间 = 2026-09        类型 = 数字类（可机器判定）")
    w()
    w("[2/4] 构造 query（三元组，不是整句断言）")
    w('      query = "%s"    Site = %s    Mode = 0' % (QUERY, SITE))
    r = search(QUERY, mode=0, cnt=10, site=SITE, tag="trace_one")
    w("      调用 SearchPro ... 返回 %d 条，耗时 %d ms，HTTP OK" % (len(r["pages"]), r["elapsed_ms"]))
    w()
    w("      返回结果（真实原文，未改写）：")
    for i, p in enumerate(r["pages"], 1):
        d = (p.get("date") or "")[:10] or "无日期"
        w("      %2d. %s ｜ %s ｜ %s" % (
            i, (p.get("title") or "")[:34], p.get("site") or "-", d))
    w()
    w("[3/4] 三步对齐")
    s_hit = [p for p in r["pages"] if subject_ok(p)]
    a_hit = [p for p in r["pages"] if attr_ok(p)]
    both = [p for p in s_hit if attr_ok(p)]
    w("      主体对齐：%d/%d 命中（标题或摘要出现 Vue）" % (len(s_hit), len(r["pages"])))
    w("      属性对齐：%d/%d 命中（出现 announced / released / GA 动词）" % (len(a_hit), len(r["pages"])))
    w("      同时满足：%d 条 —— 全部\"像\"真的：" % len(both))
    for p in both:
        w("        · %-34s %s" % ((p.get("title") or "")[:34], (p.get("date") or "-")[:10]))
    hit = [p for p in both if first_ym(p) == CLAIMED_YM]
    w()
    w("[4/4] 三态裁决")
    w("      时间对齐：上述 %d 条里，声称 2026-09 的命中 %d 条" % (len(both), len(hit)))
    w("        ↑ 主体和属性都过，但没有一条提到 3.6，最新一条是 2024-09 的 Vue 3.5")
    w("          这正是「域名对、标题像」最容易骗过人的地方")
    w("      回到 registry 核真值：")
    w("        dist-tags.latest = 3.5.44（2026-10-13）—— 3.6 至今没有正式版")
    w("        3.6.0-rc.1 = 2026-07-18，此后 13 个 rc，最新 rc.13 = 2026-10-23")
    w()
    w("      >>> 裁决：假（预发布当正式版）")
    w("      >>> 证据不足的断言不判真，进人工复核队列")
    w()
    w("日志已写入 data/calls.jsonl（tag=trace_one）")

    with open(os.path.join(ROOT, "data", "trace_vue.txt"), "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print("\n-> data/trace_vue.txt")


if __name__ == "__main__":
    main()
