# -*- coding: utf-8 -*-
"""
Step 1b：对首轮没拿到"发布公告页"的实体，换更精确的 query 再试一次。

这本身也在回答一个问题：
    单次检索不够用时，query 迭代能把命中率提升多少？
    （这是"检索策略"章节的第三个数据点）
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from yb import DATA, search  # noqa: E402

KW = ["announc", "is out", "now available", "is alive", "released",
      "general availability", "release notes", "launch", "正式发布", "发布"]


def is_announce(title: str, passage: str) -> bool:
    t = (title + " " + passage).lower()
    return any(k in t for k in KW)


def main() -> None:
    cands = json.loads((DATA / "truth_candidates.json").read_text(encoding="utf-8"))
    # 只看首条不是公告页的
    todo = [c for c in cands
            if not (c["top"] and is_announce(c["top"][0]["title"] or "",
                                             c["top"][0]["passage"] or ""))]
    print("需补采 %d 个实体\n" % len(todo))

    out = []
    got = 0
    for c in todo:
        q = "%s released" % c["entity"]
        res = search(q, mode=0, cnt=10, site=c["site"], tag="refine_truth")
        hit = None
        for p in res["pages"]:
            if is_announce(p.get("title") or "", p.get("passage") or ""):
                hit = p
                break
        ok = hit is not None
        got += ok
        out.append({"id": c["id"], "entity": c["entity"], "cn": c["cn"],
                    "site": c["site"], "query": q,
                    "hit": {"title": hit.get("title"), "date": hit.get("date"),
                            "url": hit.get("url"),
                            "passage": (hit.get("passage") or "")[:200]} if ok else None})
        print("%-11s %s | %s | %s"
              % (c["id"], "OK " if ok else "MISS",
                 (hit.get("title") or "-")[:50] if ok else "-",
                 (hit.get("date") or "-") if ok else "-"))

    p = DATA / "truth_candidates_refined.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n补采命中 %d/%d（首轮 8/%d）" % (got, len(todo), len(cands)))


if __name__ == "__main__":
    main()
