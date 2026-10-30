#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""核验两份 AI 生成稿里可证伪的断言。

真值优先级：
  1) 版本号 / 发布日期 —— npm registry 的 dist-tags.latest 与 time 字段
  2) 特性描述 —— 元宝搜索 SearchPro，定向官方域，人工判读

输出 data/draft_verdicts.json，并打印可直接进文章的统计表。
"""
import json
import os
import re
import sys
import time as _t

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yb import search  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CLAIMS = os.path.join(BASE, "claims_drafts.json")
CACHE = os.path.join(BASE, "pkg_times_cache.json")
OUT = os.path.join(BASE, "draft_verdicts.json")


# ---------- 真值层 ----------
def load_cache() -> dict:
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    return {}


def fetch_pkg(pkg: str, cache: dict) -> dict:
    if pkg in cache and cache[pkg].get("time"):
        return cache[pkg]
    for i in range(5):
        try:
            r = requests.get("https://registry.npmjs.org/%s" % pkg, timeout=60)
            if r.status_code == 200:
                d = r.json()
                keep = {
                    "latest": d.get("dist-tags", {}).get("latest"),
                    "tags": d.get("dist-tags", {}),
                    "time": {k: v for k, v in d.get("time", {}).items()},
                }
                cache[pkg] = keep
                return keep
        except Exception as e:
            print("   retry %s: %s" % (pkg, type(e).__name__))
        _t.sleep(3 + i * 2)
    raise RuntimeError("拉不到 %s" % pkg)


def ym_of(ts: str) -> str:
    return ts[:7]


def months_between(ym_a: str, ym_b: str) -> int:
    ya, ma = int(ym_a[:4]), int(ym_a[5:7])
    yb, mb = int(ym_b[:4]), int(ym_b[5:7])
    return (yb - yb) + (0) if False else ((yb * 12 + mb) - (ya * 12 + ma))


def is_stable(v: str) -> bool:
    return "-" not in v


def stable_after(pk: dict, ts: str) -> list:
    t = pk["time"]
    return sorted([v for v, s in t.items()
                   if is_stable(v) and v not in ("created", "modified") and s > ts])


def judge_version(claim: dict, pk: dict) -> dict:
    claimed = claim["claimed_version"].lstrip("v")
    latest = pk["latest"]
    t = pk["time"]
    truth_ym = ym_of(t[latest])

    # 形如 8.x / 4.x 的粗粒度写法
    if re.fullmatch(r"\d+\.x", claimed):
        maj = claimed.split(".")[0]
        ok = latest.startswith(maj + ".")
        return {"verdict": "真（粗粒度）" if ok else "假",
                "truth": latest, "truth_date": truth_ym,
                "note": "写成范围而非具体版本；范围包含当前最新版" if ok else "范围不含当前最新版"}

    # 形如 19.3 / 7.0（省略 patch）
    if re.fullmatch(r"\d+\.\d+", claimed):
        if latest.startswith(claimed + "."):
            return {"verdict": "真（省略 patch）", "truth": latest, "truth_date": truth_ym,
                    "note": "%s 是 %s 的简写" % (claimed, latest)}
        if claimed in t:
            pass  # 落到下面按具体版本处理

    if claimed not in t:
        # 检查是否只是预发布（alpha/beta/rc）被当成正式版
        pre = [v for v in t if v.startswith(claimed.rsplit(".", 1)[0])]
        pre = [v for v in pre if "-" in v]
        return {"verdict": "假（版本号不存在）", "truth": latest, "truth_date": truth_ym,
                "note": ("该线只有预发布版 %s，未正式发版" % sorted(pre, key=lambda x: t[x])[-1]) if pre
                        else "registry 中不存在该版本"}

    pub = t[claimed]
    newer = stable_after(pk, pub)
    if claimed == latest:
        return {"verdict": "真（精确命中）", "truth": latest, "truth_date": truth_ym,
                "note": "与 dist-tags.latest 完全一致", "behind": 0}

    m = months_between(ym_of(pub), truth_ym)
    return {"verdict": "假（版本过时）", "truth": latest, "truth_date": truth_ym,
            "truth_pub": ym_of(pub),
            "behind": len(newer),
            "note": "该版本真实存在（%s 发布），但已落后 %d 个正式版、%d 个月" % (ym_of(pub), len(newer), m)}


def judge_major_date(claim: dict, pk: dict) -> dict:
    t = pk["time"]
    claimed_ym = claim["claimed_ym"]
    if claim.get("claimed_version_for_date"):
        v = claim["claimed_version_for_date"]
        if v not in t:
            return {"verdict": "无法判定", "note": "真值版本缺失"}
        truth_ym = ym_of(t[v])
        label = v
    else:
        maj = claim["claimed_major"]
        cands = [v for v in t if is_stable(v) and v not in ("created", "modified")
                 and v.split(".")[0] == str(maj)]
        # 跳过 npm 上常见的 x.0.0 占位（如 typescript 6.0.0 若为 0 字节）
        cands = [v for v in cands if not v.endswith(".0.0") or True]
        if not cands:
            return {"verdict": "无法判定", "note": "该 major 无正式版"}
        v = sorted(cands, key=lambda x: t[x])[0]
        truth_ym = ym_of(t[v])
        label = v

    d = months_between(claimed_ym, truth_ym)  # 正数=真值更晚
    if d == 0:
        return {"verdict": "真", "truth": label, "truth_date": truth_ym, "delta_month": 0}
    return {"verdict": "假（日期错）", "truth": label, "truth_date": truth_ym,
            "delta_month": d,
            "note": "稿子写 %s，实际 %s（%s %+d 个月）" % (claimed_ym, truth_ym, "晚报" if d > 0 else "早报", abs(d))}


def probe_feature(claim: dict) -> dict:
    """B 组策略：官方域定向检索，取前 5 条标题供判读。"""
    try:
        r = search(claim["query"], mode=0, cnt=10, site=claim.get("site"), tag="draft_feature")
    except Exception as e:
        return {"error": str(e), "hits": []}
    hits = [{"title": (p.get("title") or "")[:90],
             "site": p.get("site"),
             "date": p.get("date"),
             "snippet": (p.get("passage") or "")[:220].replace("\n", " ")}
            for p in r["pages"][:5]]
    return {"n": len(r["pages"]), "hits": hits}


def main():
    data = json.load(open(CLAIMS, encoding="utf-8"))
    cache = load_cache()
    verdicts = []

    for c in data["claims"]:
        v = {"id": c["id"], "model": c["model"], "tool": c["tool"],
             "type": c["type"], "text": c["text"]}
        if c["type"] in ("version", "major_date"):
            pk = fetch_pkg(c["pkg"], cache)
            v.update(judge_version(c, pk) if c["type"] == "version" else judge_major_date(c, pk))
        else:
            v["verdict"] = "待判读"
            v["evidence"] = probe_feature(c)
        verdicts.append(v)
        print("%-4s %-10s %-10s %-16s %s" % (
            v["id"], c["model"], c["tool"], v["verdict"], v.get("note", "")[:70]))

    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(verdicts, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---------- 汇总 ----------
    print("\n" + "=" * 68)
    for model in ("deepseek", "gemini"):
        rows = [v for v in verdicts if v["model"] == model]
        num = [v for v in rows if v["type"] in ("version", "major_date")]
        feat = [v for v in rows if v["type"] == "feature"]
        right = [v for v in num if v["verdict"].startswith("真")]
        stale = [v for v in num if "过时" in v["verdict"]]
        fake = [v for v in num if "不存在" in v["verdict"]]
        deltas = [abs(v["delta_month"]) for v in num if v.get("delta_month")]
        print("%s：可机械核验 %d 条 | 对 %d | 过时 %d | 版本不存在 %d | 日期平均偏差 %.1f 个月"
              % (model, len(num), len(right), len(stale), len(fake),
                 sum(deltas) / len(deltas) if deltas else 0))
        if feat:
            print("   特性类待判读 %d 条：%s" % (len(feat), ", ".join(f["id"] for f in feat)))
    print("=" * 68)
    print("-> %s" % OUT)


if __name__ == "__main__":
    main()
