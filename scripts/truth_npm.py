#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 npm registry 拉取权威版本与发布时间，作为"真值锚点"。

为什么要第三方锚点：我（模型）的知识截止早于 2026，凭记忆判真值等于用错误
检错误。npm registry 的 version + time 字段是发布方自己写进去的，且可复核。

产出 data/npm_truth.json
"""
import json
import os
import sys
import time as _t

import requests

PKGS = ["vue", "react", "vite", "typescript", "next", "tailwindcss"]
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "npm_truth.json")


def fetch(pkg: str, tries: int = 5) -> dict | None:
    url = "https://registry.npmjs.org/%s" % pkg
    for i in range(tries):
        try:
            r = requests.get(url, timeout=40)
            if r.status_code == 200:
                return r.json()
            print("  [%s] HTTP %d" % (pkg, r.status_code))
        except Exception as e:
            print("  [%s] try%d %s" % (pkg, i + 1, type(e).__name__))
        _t.sleep(2 + i * 2)
    return None


def major_of(v: str) -> int | None:
    try:
        return int(v.split("-")[0].split(".")[0])
    except Exception:
        return None


def main():
    out = {}
    for pkg in PKGS:
        print("fetch %s ..." % pkg)
        d = fetch(pkg)
        if not d:
            print("  !! 放弃 %s" % pkg)
            continue
        times = d.get("time", {})
        latest = d.get("dist-tags", {}).get("latest", "")
        maj = major_of(latest)
        # 该 major 的第一个正式版（跳过 alpha/beta/rc/canary/next）
        major_first = None
        for v, ts in times.items():
            if v in ("created", "modified"):
                continue
            if any(k in v for k in ("-", "alpha", "beta", "rc", "canary", "next", "insiders")):
                continue
            if major_of(v) == maj:
                if major_first is None or ts < major_first[1]:
                    major_first = (v, ts)
        # 最近 5 个正式版，便于后面看"最新"是否被漏
        stable = [(v, ts) for v, ts in times.items()
                  if v not in ("created", "modified") and "-" not in v]
        stable.sort(key=lambda x: x[1])
        out[pkg] = {
            "latest": latest,
            "latest_published": times.get(latest),
            "major": maj,
            "major_first_version": major_first[0] if major_first else None,
            "major_first_published": major_first[1] if major_first else None,
            "recent_stable": [{"v": v, "t": ts} for v, ts in stable[-5:]],
        }
        print("  latest=%s (%s) | major=%s 首发=%s (%s)" % (
            latest, times.get(latest, "")[:10], maj,
            out[pkg]["major_first_version"],
            (out[pkg]["major_first_published"] or "")[:10]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n-> %s（%d 个包）" % (OUT, len(out)))


if __name__ == "__main__":
    main()
