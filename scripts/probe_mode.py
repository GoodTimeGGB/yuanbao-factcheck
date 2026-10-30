# -*- coding: utf-8 -*-
"""
探针一：Mode=1（权威垂直信源）的 query 边界

要回答的问题（也是文章里第一个反直觉发现）：
  同一个实体，query 越"像人话"、限定词越多，Mode=1 的召回是变好还是变差？

设计：3 个实体类别 × 3 种 query 形态 × 2 个 Mode（1 / 2），共 18 次调用。
输出：data/probe_mode.csv + 终端 markdown 表（可直接贴进文章）。

跑法：
    python scripts/probe_mode.py            # 真跑
    python scripts/probe_mode.py --dry-run  # 只打印计划，不耗额度
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from yb import DATA, search  # noqa: E402

# (类别, 极简形态, 加限定词形态, 长问句形态)
CASES = [
    ("行情", "特斯拉股价", "特斯拉股价 盘前最新", "特斯拉今天的股价是多少钱一股"),
    ("天气", "北京天气", "北京明天天气 降水概率", "北京明天会不会下雨要带伞吗"),
    ("金价", "今日金价", "今日金价 周大福 最新报价", "现在黄金多少钱一克值得买吗"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cnt", type=int, default=10)
    args = ap.parse_args()

    rows = []
    for cat, simple, limited, long_q in CASES:
        for shape, q in (("极简", simple), ("加限定词", limited), ("长问句", long_q)):
            for mode in (1, 2):
                if args.dry_run:
                    rows.append((cat, shape, q, mode, "-", "-"))
                    print("%-4s %-6s Mode=%d  %s" % (cat, shape, mode, q))
                    continue
                res = search(q, mode=mode, cnt=args.cnt, tag="probe_mode")
                rows.append((cat, shape, q, mode, len(res["pages"]), res["err"] or "ok"))
                print("%-4s %-6s Mode=%d  %-2d条 %5dms  %s"
                      % (cat, shape, mode, len(res["pages"]), res["elapsed_ms"], q))

    if args.dry_run:
        print("\n共 %d 次调用（dry-run，未消耗额度）" % len(rows))
        return

    out = DATA / "probe_mode.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["类别", "query形态", "query", "Mode", "条数", "状态"])
        w.writerows(rows)
    print("\n-> %s" % out)

    # markdown 透视表：行=类别/形态，列=Mode
    print("\n| 类别 | query 形态 | 示例 query | Mode=1 条数 | Mode=2 条数 |")
    print("|---|---|---|---|---|")
    idx = {(r[0], r[1], r[3]): r[4] for r in rows}
    for cat, simple, limited, long_q in CASES:
        for shape, q in (("极简", simple), ("加限定词", limited), ("长问句", long_q)):
            print("| %s | %s | `%s` | %s | %s |"
                  % (cat, shape, q, idx.get((cat, shape, 1), "-"), idx.get((cat, shape, 2), "-")))


if __name__ == "__main__":
    main()
