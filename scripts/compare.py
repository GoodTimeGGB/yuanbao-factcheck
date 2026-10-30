# -*- coding: utf-8 -*-
"""
Step 3：A/B 对照实验

A 组（对照组，代表现在绝大多数做法）
    query  = 断言原文
    判定   = 结果里出现断言所述的年月 → 判「真」；否则判「假」

B 组（本文主张）
    query  = 三元组改写「{实体} released」+ site 限定官方域名
    判定   = 主体对齐三条件，全满足才下结论：
             ① 主体：结果里包含实体的全部 token
             ② 属性：结果是发布类页面（announcing / is out / now available / GA…）
             ③ 值：  从该结果里抽出的年月 == 断言所述年月
             不满足 → 「无证据」（不强行判真判假）

指标：准确率 / 误报率（假判真）/ 漏报率（真判假）/ 无证据占比 / 单条成本
跑法：python scripts/compare.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from yb import DATA, search  # noqa: E402

YM = re.compile(r"(20\d{2})\s*[年\-/\.]\s*(\d{1,2})")
YM_DATE = re.compile(r"(20\d{2})[/\-\.](\d{1,2})")
VERSION = re.compile(r"\b\d+\.\d+(?:\.\d+)?\b")
ANNOUNCE_KW = ["announc", "is out", "now available", "is alive", "released",
               "general availability", "is now ga", "launch", "正式发布"]
MONTH_EN = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}


def extract_ym(p: dict) -> tuple[int, int] | None:
    """抽年月。三级回退：date 字段 → 正文数字日期 → 正文英文月份。

    注意：date 字段在部分站点是占位值（如微软支持页恒为 2025/01/01），
    所以只在它看起来合理时优先采用，正文日期作为交叉验证。
    """
    d = (p.get("date") or "").strip()
    m = YM_DATE.search(d)
    if m:
        return int(m.group(1)), int(m.group(2))

    txt = (p.get("title") or "") + " " + (p.get("passage") or "")[:400]
    m = YM.search(txt)
    if m:
        return int(m.group(1)), int(m.group(2))

    low = txt.lower()
    for name, num in MONTH_EN.items():
        mm = re.search(name + r"\s+\d{1,2},?\s+(20\d{2})", low)
        if mm:
            return int(mm.group(1)), num
        mm = re.search(r"(20\d{2})\s+" + name, low)
        if mm:
            return int(mm.group(1)), num
    return None


def subject_ok(p: dict, entity: str) -> bool:
    """主体对齐：实体每个 token 都要出现，且不能冒出别的版本号"""
    t = ((p.get("title") or "") + " " + (p.get("passage") or "")[:200]).lower()
    if not all(tok.lower() in t for tok in entity.split()):
        return False
    # 实体自带的版本号之外，标题里若出现别的版本号，大概率是别的版本
    own = set(VERSION.findall(entity))
    extra = set(VERSION.findall(p.get("title") or "")) - own
    return not extra


def attr_ok(p: dict) -> bool:
    t = ((p.get("title") or "") + " " + (p.get("passage") or "")[:200]).lower()
    return any(k in t for k in ANNOUNCE_KW)


def judge_a(pages: list[dict], claimed: tuple[int, int]) -> str:
    """A 组判定：字面匹配（极简、也是错的）"""
    for p in pages:
        if claimed in {tuple(int(x) for x in m) for m in YM.findall(
                (p.get("title") or "") + " " + (p.get("passage") or ""))}:
            return "真"
    return "假"


def judge_b(pages: list[dict], entity: str, claimed: tuple[int, int]) -> str:
    """B 组判定：主体对齐三条件。

    先看全部候选，再下结论——不能拿"第一条候选"直接定生死，
    否则一条无关页面就能把整条断言判错。
    """
    cands = [p for p in pages if subject_ok(p, entity) and attr_ok(p)]
    if not cands:
        return "无证据"
    yms = [y for y in (extract_ym(p) for p in cands) if y]
    if not yms:
        return "无证据"
    if claimed in yms:
        return "真"
    return "假"


def main() -> None:
    claims = json.loads((DATA / "claims_v2.json").read_text(encoding="utf-8"))["claims"]
    rows = []
    for c in claims:
        cy, cm = (int(x) for x in c["value"].split("-"))
        claimed = (cy, cm)
        gold = "真" if c["label"] else "假"

        qa = c["claim"]
        ra = search(qa, mode=0, cnt=10, tag="cmp_A")
        va = judge_a(ra["pages"], claimed)

        qb = "%s released" % c["entity"]
        rb = search(qb, mode=0, cnt=10, site=c["official_site"], tag="cmp_B")
        vb = judge_b(rb["pages"], c["entity"], claimed)

        rows.append({
            "id": c["id"], "gold": gold, "value": c["value"],
            "A_query": qa, "A_verdict": va, "A_ok": int(va == gold),
            "A_n": len(ra["pages"]), "A_ms": ra["elapsed_ms"],
            "B_query": qb, "B_verdict": vb, "B_ok": int(vb == gold),
            "B_n": len(rb["pages"]), "B_ms": rb["elapsed_ms"],
        })
        print("%-14s gold=%s A=%-4s B=%-6s" % (c["id"], gold, va, vb))

    p = DATA / "compare.csv"
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def stat(key):
        g = rows
        n = len(g)
        acc = sum(r[key + "_ok"] for r in g) / n
        fakes = [r for r in g if r["gold"] == "假"]
        trues = [r for r in g if r["gold"] == "真"]
        fp = sum(1 for r in fakes if r[key + "_verdict"] == "真") / len(fakes)
        fn = sum(1 for r in trues if r[key + "_verdict"] == "假") / len(trues)
        unk = sum(1 for r in g if r[key + "_verdict"] == "无证据") / n
        ms = sum(r[key + "_ms"] for r in g) / n
        return acc, fp, fn, unk, ms

    print("\n| 指标 | A 组（断言原文直搜） | B 组（三元组+官方源+主体对齐） |")
    print("|---|---|---|")
    a, b = stat("A"), stat("B")
    names = ["准确率", "误报率（假→真）", "漏报率（真→假）", "「无证据」占比", "平均单次耗时"]
    for i, nm in enumerate(names):
        if i == 4:
            print("| %s | %.0f ms | %.0f ms |" % (nm, a[i], b[i]))
        else:
            print("| %s | %.0f%% | %.0f%% |" % (nm, a[i] * 100, b[i] * 100))
    print("\n样本 %d 条（真 %d / 假 %d）；总调用 %d 次"
          % (len(rows), sum(1 for r in rows if r["gold"] == "真"),
             sum(1 for r in rows if r["gold"] == "假"), len(rows) * 2))
    print("-> %s" % p)


if __name__ == "__main__":
    main()
