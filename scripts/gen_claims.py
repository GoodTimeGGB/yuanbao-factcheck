# -*- coding: utf-8 -*-
"""
Step 2：用人工核对过的 12 条真值，生成标注集（真假各半，共 24 条）

假值生成规则固定、可复现：真值月份 +7（跨年），保证与真值至少差 7 个月，
不会碰巧落在另一个真实发布月上。改法只有这一种，不含主观。

真值来源：官方发布公告页（URL 见每条 official_url），日期取自该页。
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 人工核对过的真值：(id, 实体, 中文名, 官方站, 真值年月, 公告页标题)
TRUTHS = [
    ("vue35",     "Vue 3.5",          "Vue 3.5",          "blog.vuejs.org",          "2024-09", "Announcing Vue 3.5"),
    ("vue34",     "Vue 3.4",          "Vue 3.4",          "blog.vuejs.org",          "2023-12", "Announcing Vue 3.4"),
    ("vite6",     "Vite 6.0",         "Vite 6.0",         "vitejs.dev",              "2024-11", "Vite 6.0 is out!"),
    ("vite5",     "Vite 5.0",         "Vite 5.0",         "vitejs.dev",              "2023-11", "Vite 5.0 is out!"),
    ("ts56",      "TypeScript 5.6",   "TypeScript 5.6",   "devblogs.microsoft.com",  "2024-09", "Announcing TypeScript 5.6"),
    ("ts50",      "TypeScript 5.0",   "TypeScript 5.0",   "devblogs.microsoft.com",  "2023-03", "Announcing TypeScript 5.0"),
    ("angular18", "Angular 18",       "Angular 18",       "blog.angular.dev",        "2024-05", "Angular v18 is now available!"),
    ("es815",     "Elasticsearch 8.15", "Elasticsearch 8.15", "elastic.co",          "2024-08", "Elastic 8.15"),
    ("react18",   "React 18",         "React 18",         "react.dev",               "2022-03", "React v18.0"),
    ("k8s131",    "Kubernetes 1.31",  "Kubernetes 1.31",  "kubernetes.io",           "2024-08", "Kubernetes v1.31: Elli"),
    ("redis8",    "Redis 8",          "Redis 8",          "redis.io",                "2025-05", "Redis 8 is now GA"),
    ("mysql84",   "MySQL 8.4",        "MySQL 8.4",        "dev.mysql.com",           "2024-04", "MySQL 8.4 GA"),
]


def shift(y: int, m: int, delta: int = 7) -> tuple[int, int]:
    """真值月份 +delta，跨年归一化"""
    idx = y * 12 + (m - 1) + delta
    return idx // 12, idx % 12 + 1


def find_url(cid: str) -> str:
    """从两轮采集结果里取公告页 URL"""
    for f in ("truth_candidates.json", "truth_candidates_refined.json"):
        p = DATA / f
        if not p.exists():
            continue
        for rec in json.loads(p.read_text(encoding="utf-8")):
            if rec.get("id") != cid:
                continue
            cand = (rec.get("top") or [None])[0]
            if f.endswith("refined.json"):
                cand = rec.get("hit") or {}
            if cand and cand.get("url"):
                return cand["url"]
    return ""


def main() -> None:
    claims = []
    for cid, entity, cn, site, truth, title in TRUTHS:
        ty, tm = (int(x) for x in truth.split("-"))
        url = find_url(cid)
        claims.append({
            "id": cid, "entity": entity, "official_site": site,
            "claim": "%s 于 %d 年 %d 月正式发布" % (cn, ty, tm),
            "value": truth, "label": True,
            "official_url": url, "official_title": title,
        })
        fy, fm = shift(ty, tm)
        claims.append({
            "id": cid + "_fake", "entity": entity, "official_site": site,
            "claim": "%s 于 %d 年 %d 月正式发布" % (cn, fy, fm),
            "value": "%d-%02d" % (fy, fm), "label": False,
            "truth": truth, "official_url": url, "official_title": title,
            "改法": "月份 +7（跨年归一）",
        })

    out = DATA / "claims_v2.json"
    out.write_text(json.dumps({"claims": claims}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("生成 %d 条（真 %d / 假 %d）-> %s"
          % (len(claims), sum(c["label"] for c in claims),
             sum(not c["label"] for c in claims), out))
    print("\n| 实体 | 真断言 | 假断言 | 官方公告页 |")
    print("|---|---|---|---|")
    for c in claims:
        if c["label"]:
            f = next(x for x in claims if x["id"] == c["id"] + "_fake")
            print("| %s | %s | %s | %s |" % (c["entity"], c["value"], f["value"],
                                             c["official_title"]))
    miss = [c["id"] for c in claims if not c["official_url"]]
    if miss:
        print("\n[!] 缺 url：", miss)


if __name__ == "__main__":
    main()
