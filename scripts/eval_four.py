#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""四格对照：模型 × 检索状态。数字类断言统一 12 条口径，逐条对齐 registry 真值。"""
import json
import os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
cache = json.load(open(os.path.join(BASE, "pkg_times_cache.json"), encoding="utf-8"))
ds2 = json.load(open(os.path.join(BASE, "claims_ds2.json"), encoding="utf-8"))
old = json.load(open(os.path.join(BASE, "draft_verdicts.json"), encoding="utf-8"))


def ym(ts):
    return ts[:7]


def month_diff(a, b):
    return (int(b[:4]) * 12 + int(b[5:7])) - (int(a[:4]) * 12 + int(a[5:7]))


def latest_of(pkg):
    return cache[pkg]["latest"]


def judge_range(pkg, claimed):
    """8.1.x / 3.6.x 这类写法：判断是否包含当前最新版"""
    latest = latest_of(pkg)
    prefix = claimed.replace(".x", ".")
    ok = latest.startswith(prefix)
    return ok, latest


print("=" * 78)
print("第二部分  DeepSeek 联网版（第 3 篇）：逐条对齐")
print("=" * 78)
right = wrong = 0
num_total = 0
for c in ds2["claims"]:
    if c["type"] == "version":
        num_total += 1
        if "claimed_version" in c:
            ok, latest = judge_range(c["pkg"], c["claimed_version"])
            if ok:
                right += 1
                print("  ✓ %-4s %-11s %-8s 是最新版所在线（latest=%s）" % (c["id"], c["tool"], c["claimed_version"], latest))
            else:
                wrong += 1
                print("  ✗ %-4s %-11s 写 %-8s，实际 latest=%s" % (c["id"], c["tool"], c["claimed_version"], latest))
    elif c["type"] == "major_date":
        num_total += 1
        v = c["truth_version"]
        t = cache and None
        # 从缓存取该版本发布日期
        pub = cache.get(c.get("pkg"), {}).get("time", {}).get(v)
        if not pub:
            print("  ? %-4s 真值版本 %s 不在缓存，跳过" % (c["id"], v))
            num_total -= 1
            continue
        d = month_diff(c["claimed_ym"], ym(pub))
        if d == 0:
            right += 1
            print("  ✓ %-4s %-11s 写 %s，真值 %s (%s)" % (c["id"], c["tool"], c["claimed_ym"], ym(pub), v))
        else:
            wrong += 1
            print("  ✗ %-4s %-11s 写 %s，真值 %s（%s %+d 个月）" % (
                c["id"], c["tool"], c["claimed_ym"], ym(pub), v, d))

feat = [c for c in ds2["claims"] if c["type"] == "feature"]
fok = sum(1 for c in feat if c["verdict"] == "真")
print("\n数字类 %d 条：对 %d，错 %d（正确率 %.0f%%）" % (num_total, right, wrong, 100 * right / num_total))
print("特性类 %d 条：官方原文证实 %d，无证据 %d" % (len(feat), fok, len(feat) - fok))

# ---------- 四格汇总 ----------
print("\n" + "=" * 78)
print("四格对照（数字类统一 12 条口径）")
print("=" * 78)
rows = [("DeepSeek（检索关）", 4, 12, 3, 4), ("DeepSeek（检索开）", right, num_total, fok, len(feat)),
        ("Gemini（检索开）", 11, 12, 3, 4)]
print("%-22s %-14s %-14s" % ("", "数字类", "特性类"))
for name, r, n, fr, fn in rows:
    print("%-22s %-14s %-14s" % (name, "%d/%d (%.0f%%)" % (r, n, 100 * r / n),
                                 "%d/%d" % (fr, fn)))
print("\n说明：DeepSeek 检索关 / Gemini 检索开的数字，来自 data/draft_verdicts.json 的逐条判定。")
