# -*- coding: utf-8 -*-
"""
Step 1：采集真值候选

对 30 个技术实体，用「实体 + release date」+ 官方站限定，各搜一次。
输出每条的官方结果（title / date / passage 片段），由人核对后写入 truths.json。

这一步同时是一个独立实验：
    「限定官方源」这个策略，在 30 个不同实体上的首条命中率是多少？
    如果高，说明策略有效；如果低，说明"搜得到"本身就是个问题。

跑法：python scripts/harvest_truth.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from yb import DATA, search  # noqa: E402

# (id, 实体, 官方站, 中文名)
TARGETS = [
    ("vue35", "Vue 3.5", "blog.vuejs.org", "Vue 3.5"),
    ("vue34", "Vue 3.4", "blog.vuejs.org", "Vue 3.4"),
    ("react19", "React 19", "react.dev", "React 19"),
    ("react18", "React 18", "react.dev", "React 18"),
    ("vite6", "Vite 6", "vitejs.dev", "Vite 6"),
    ("vite5", "Vite 5", "vitejs.dev", "Vite 5"),
    ("ts56", "TypeScript 5.6", "devblogs.microsoft.com", "TypeScript 5.6"),
    ("ts50", "TypeScript 5.0", "devblogs.microsoft.com", "TypeScript 5.0"),
    ("tw4", "Tailwind CSS 4.0", "tailwindcss.com", "Tailwind CSS 4.0"),
    ("next15", "Next.js 15", "nextjs.org", "Next.js 15"),
    ("nuxt3", "Nuxt 3", "nuxt.com", "Nuxt 3"),
    ("angular18", "Angular 18", "blog.angular.dev", "Angular 18"),
    ("svelte5", "Svelte 5", "svelte.dev", "Svelte 5"),
    ("node22", "Node.js 22", "nodejs.org", "Node.js 22"),
    ("node20", "Node.js 20", "nodejs.org", "Node.js 20"),
    ("py313", "Python 3.13", "python.org", "Python 3.13"),
    ("py312", "Python 3.12", "python.org", "Python 3.12"),
    ("net9", ".NET 9", "dotnet.microsoft.com", ".NET 9"),
    ("net8", ".NET 8", "dotnet.microsoft.com", ".NET 8"),
    ("go123", "Go 1.23", "go.dev", "Go 1.23"),
    ("go122", "Go 1.22", "go.dev", "Go 1.22"),
    ("rust180", "Rust 1.80", "blog.rust-lang.org", "Rust 1.80"),
    ("java21", "Java 21", "oracle.com", "Java 21"),
    ("spring34", "Spring Boot 3.4", "spring.io", "Spring Boot 3.4"),
    ("pg17", "PostgreSQL 17", "postgresql.org", "PostgreSQL 17"),
    ("mysql84", "MySQL 8.4", "dev.mysql.com", "MySQL 8.4"),
    ("k8s131", "Kubernetes 1.31", "kubernetes.io", "Kubernetes 1.31"),
    ("redis8", "Redis 8", "redis.io", "Redis 8"),
    ("mongo80", "MongoDB 8.0", "mongodb.com", "MongoDB 8.0"),
    ("es815", "Elasticsearch 8.15", "elastic.co", "Elasticsearch 8.15"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    targets = TARGETS[: args.limit] if args.limit else TARGETS

    out = []
    for cid, entity, site, cn in targets:
        q = "%s release date" % entity
        res = search(q, mode=0, cnt=10, site=site, tag="harvest_truth")
        pages = res["pages"]
        n_off = sum(1 for p in pages
                    if site.split(".")[0] in ((p.get("site") or "") + (p.get("url") or "")))
        cands = [{
            "title": p.get("title"),
            "date": p.get("date"),
            "url": p.get("url"),
            "passage": (p.get("passage") or "")[:260],
        } for p in pages[:3]]
        out.append({"id": cid, "entity": entity, "cn": cn, "site": site,
                    "query": q, "n": len(pages), "n_official": n_off,
                    "top": cands})
        first = cands[0] if cands else {}
        print("%-11s n=%-2d off=%-2d | %s | %s"
              % (cid, len(pages), n_off, (first.get("title") or "-")[:52],
                 first.get("date") or "-"))

    p = DATA / "truth_candidates.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    hit = sum(1 for r in out if r["n_official"] > 0)
    first_off = sum(1 for r in out
                    if r["top"] and (r["site"].split(".")[0] in
                                     ((r["top"][0].get("url") or "") + (r["top"][0].get("title") or ""))))
    print("\n官方源命中：%d/%d 条有官方结果；首条即官方：%d/%d"
          % (hit, len(out), first_off, len(out)))
    print("-> %s" % p)


if __name__ == "__main__":
    main()
