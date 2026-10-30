# -*- coding: utf-8 -*-
"""
实验二：同一批断言，三种检索策略的取证质量对照

策略：
  S1 断言原文直搜      —— 把所有"人写的句子"直接丢给搜索（最直觉的做法）
  S2 三元组改写        —— 拆成「实体 + 属性」，去掉主观修饰
  S3 三元组 + 官方源   —— 再加 site 限定，直取权威原文

对每条断言统计三个可自动计算的指标：
  n_official   返回结果里来自官方域名的条数
  value_hit    结果里是否出现了"断言声称的值"（假的断言若命中，说明搜索在附和它）
  truth_hit    结果里是否出现了"真实值"（命中即说明拿到了可纠错的证据）

真值来自 claims.json 的 truth_source，人工标注，可核验。
跑法：python scripts/probe_claims.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from yb import DATA, search  # noqa: E402

DATE_RE = re.compile(r"(20\d{2})\s*[年\-/\.]\s*(\d{1,2})")


def ym(s: str) -> tuple[int, int] | None:
    m = DATE_RE.match(s.strip()) if DATE_RE.fullmatch(s.strip()) is None else DATE_RE.match(s.strip())
    if not m:
        m = DATE_RE.search(s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def text_of(pages: list[dict]) -> str:
    parts = []
    for p in pages:
        parts.append(p.get("title") or "")
        parts.append(p.get("passage") or "")
        parts.append(p.get("content") or "")
    return " ".join(parts)


def scan(pages: list[dict], site_want: str, value: tuple[int, int], truth: tuple[int, int]) -> dict:
    txt = text_of(pages)
    pairs = set(DATE_RE.findall(txt))
    pairs = {(int(y), int(m)) for y, m in pairs if 1 <= int(m) <= 12}
    n_official = sum(
        1 for p in pages if site_want and site_want in (p.get("site") or "") + (p.get("url") or "")
    )
    return {
        "value_hit": int(value in pairs),
        "truth_hit": int(truth in pairs),
        "n_official": n_official,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条断言（成对出现）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads((DATA / "claims.json").read_text(encoding="utf-8"))["claims"]
    if args.limit:
        data = data[: args.limit]

    rows = []
    for c in data:
        truth = ym(c.get("真值") or c["value"])
        value = ym(c["value"])
        plans = [
            ("S1_原文", c["claim"], None),
            ("S2_三元组", "%s %s" % (c["entity"], c["attr"]), None),
            ("S3_三元组+官方源", "%s %s" % (c["entity"], c["attr"]), c["official_site"]),
        ]
        for strat, q, site in plans:
            if args.dry_run:
                print("%-8s %-16s site=%s  %s" % (c["id"], strat, site, q))
                continue
            res = search(q, mode=0, cnt=10, site=site, tag="probe_claims")
            st = scan(res["pages"], c["official_site"], value, truth)
            rows.append({
                "id": c["id"], "label": "真" if c["label"] else "假",
                "strategy": strat, "query": q, "site": site,
                "n": len(res["pages"]), "ms": res["elapsed_ms"], **st,
            })
            print("%-12s %-16s n=%-2d official=%-2d value_hit=%d truth_hit=%d  %s"
                  % (c["id"], strat, len(res["pages"]), st["n_official"],
                     st["value_hit"], st["truth_hit"], q))

    if args.dry_run:
        print("\n共 %d 次调用（dry-run）" % (len(data) * 3))
        return

    out = DATA / "probe_claims.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 汇总：按策略 × 真/假 求平均
    print("\n| 策略 | 真断言 n平均 | 真断言 truth_hit率 | 假断言 n平均 | 假断言 value_hit率(被附和) | 假断言 truth_hit率(可纠错) | 官方源命中率 |")
    print("|---|---|---|---|---|---|---|")
    for strat in ("S1_原文", "S2_三元组", "S3_三元组+官方源"):
        def agg(label):
            g = [r for r in rows if r["strategy"] == strat and r["label"] == label]
            if not g:
                return None
            return {
                "n": sum(r["n"] for r in g) / len(g),
                "value": sum(r["value_hit"] for r in g) / len(g),
                "truth": sum(r["truth_hit"] for r in g) / len(g),
                "off": sum(1 for r in g if r["n_official"] > 0) / len(g),
            }
        t, f_ = agg("真"), agg("假")
        print("| %s | %.1f | %.0f%% | %.1f | %.0f%% | %.0f%% | %.0f%% |"
              % (strat, t["n"], t["truth"] * 100, f_["n"], f_["value"] * 100,
                 f_["truth"] * 100, f_["off"] * 100))
    print("\n-> %s" % out)


if __name__ == "__main__":
    main()
