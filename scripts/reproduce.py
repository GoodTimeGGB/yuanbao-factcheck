#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键复核：不联网、不新增任何 API 调用，只用仓库里的原始数据把征文里的数字重算一遍。

用法：
    python scripts/reproduce.py           # 复核；有 FAIL 退出码 1
    python scripts/reproduce.py --lock     # 首次运行，生成配图哈希锁 data/fig_md5.json

复核项：
    C1 调用日志      220 次 / 0 失败 / 中位耗时
    C2 A/B 对照      准确率、误报率（假判真）、漏报率、无证据占比
    C3 四格对照      33% / 75% / 92%
    C4 配图          10 张齐全、图号 1–10 连续、哈希与锁文件一致
    C5 正文硬性项    字数 ≥1500、标题含元宝搜索、图号引用连续
    C6 密钥扫描      除 .env 外不得出现 AK/SK

设计原则：只读。除了 --lock 会写 data/fig_md5.json，其余任何文件都不动。
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIGS = ROOT / "配图"
SCRIPTS = ROOT / "scripts"
LOCK = DATA / "fig_md5.json"

RESULTS: list[tuple[str, bool, str]] = []


def ok(name: str, good: bool, detail: str = "") -> None:
    RESULTS.append((name, good, detail))
    print("  %s  %-22s %s" % ("[PASS]" if good else "[FAIL]", name, detail))


def head(title: str) -> None:
    print("\n" + "─" * 74)
    print(title)
    print("─" * 74)


def read(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def md5(p: pathlib.Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


# ───────────────────────── C1 调用日志 ─────────────────────────
def check_calls() -> None:
    head("C1  调用日志  data/calls.jsonl")
    log = DATA / "calls.jsonl"
    if not log.exists():
        ok("日志存在", False, "缺 data/calls.jsonl")
        return
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    total = len(rows)
    fails = [r for r in rows if not r.get("ok")]
    lat = sorted(r["elapsed_ms"] for r in rows)
    med = statistics.median(lat)
    versions = {r.get("version") for r in rows}

    print("  总调用 %d 次，失败 %d 次，中位耗时 %.0f ms，P90 %d ms"
          % (total, len(fails), med, lat[int(len(lat) * 0.9)]))
    print("  返回版本：%s    时间跨度：%s → %s"
          % (",".join(sorted(v or "?" for v in versions)), rows[0]["ts"][:16], rows[-1]["ts"][:16]))

    ok("总调用 = 220", total == 220, "实测 %d" % total)
    ok("失败 = 0", not fails, "实测 %d" % len(fails))
    ok("中位耗时 ≈440ms", 380 <= med <= 500, "%d ms" % med)
    ok("无密钥字段落盘", all("secret" not in json.dumps(r).lower() for r in rows))


# ───────────────────────── C2 A/B 对照 ─────────────────────────
def check_ab() -> None:
    head("C2  A/B 对照  data/compare.csv × claims_v2.json")
    cmp_p, clm_p = DATA / "compare.csv", DATA / "claims_v2.json"
    if not (cmp_p.exists() and clm_p.exists()):
        ok("数据齐备", False, "缺 compare.csv 或 claims_v2.json")
        return
    labels = {c["id"]: ("真" if c["label"] else "假") for c in read(clm_p)["claims"]}
    with cmp_p.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    def metric(key: str) -> dict:
        g = [r for r in rows if r["id"] in labels]
        n = len(g)
        acc = sum(r[key + "_verdict"] == labels[r["id"]] for r in g) / n
        fakes = [r for r in g if labels[r["id"]] == "假"]
        trues = [r for r in g if labels[r["id"]] == "真"]
        fp = sum(r[key + "_verdict"] == "真" for r in fakes) / len(fakes)
        fn = sum(r[key + "_verdict"] == "假" for r in trues) / len(trues)
        unk = sum(r[key + "_verdict"] == "无证据" for r in g) / n
        ms = sum(int(r[key + "_ms"]) for r in g) / n
        return dict(n=n, acc=acc, fp=fp, fn=fn, unk=unk, ms=ms,
                    n_true=len(trues), n_false=len(fakes))

    a, b = metric("A"), metric("B")
    print("  样本 %d 条（真 %d / 假 %d）\n" % (a["n"], a["n_true"], a["n_false"]))
    print("  %-14s %10s %10s" % ("指标", "对照组(A)", "本文做法(B)"))
    for label, k, pct in [("准确率", "acc", 1), ("误报率 假→真", "fp", 1),
                          ("漏报率 真→假", "fn", 1), ("无证据占比", "unk", 1),
                          ("平均耗时", "ms", 0)]:
        print("  %-14s %10s %10s" % (label,
              ("%.0f%%" % (a[k] * 100)) if pct else ("%.0f ms" % a[k]),
              ("%.0f%%" % (b[k] * 100)) if pct else ("%.0f ms" % b[k])))
    print()
    ok("样本 = 24", a["n"] == 24, "%d 条" % a["n"])
    ok("A 准确率 54%", round(a["acc"] * 100) == 54, "%.0f%%" % (a["acc"] * 100))
    ok("A 误报率 58%", round(a["fp"] * 100) == 58, "%.0f%%" % (a["fp"] * 100))
    ok("B 准确率 75%", round(b["acc"] * 100) == 75, "%.0f%%" % (b["acc"] * 100))
    ok("B 误报率 0%", b["fp"] == 0, "%.0f%%（%d 条假断言无一被判真）" % (b["fp"] * 100, b["n_false"]))
    ok("B 无证据 25%", round(b["unk"] * 100) == 25, "%.0f%%" % (b["unk"] * 100))


# ───────────────────────── C3 四格对照 ─────────────────────────
def check_four() -> None:
    head("C3  四格对照  scripts/eval_four.py（离线，读 pkg_times_cache.json）")
    try:
        r = subprocess.run([sys.executable, str(SCRIPTS / "eval_four.py")],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
    except Exception as e:  # noqa: BLE001
        ok("脚本可运行", False, "%s: %s" % (type(e).__name__, e))
        return
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"数字类 (\d+) 条：对 (\d+)，错 (\d+)（正确率 (\d+)%）", out)
    if not m:
        ok("输出可解析", False, out.strip().splitlines()[0][:80] if out.strip() else "无输出")
        return
    n, right, wrong, pct = map(int, m.groups())
    print("  %s" % m.group(0))
    for ln in out.splitlines():
        if re.match(r"^(DeepSeek|Gemini)", ln.strip()):
            print("  %s" % ln.strip())
    ok("数字类 = 12 条", n == 12, "%d" % n)
    ok("DeepSeek 检索开 = 75%", pct == 75 and right == 9, "%d/%d = %d%%" % (right, n, pct))
    ok("与文中 33/75/92 一致", "4/12 (33%)" in out and "11/12 (92%)" in out)


# ───────────────────────── C4 配图 ─────────────────────────
def check_figs() -> None:
    head("C4  配图  配图/fig*.png × data/uploaded_urls.json")
    files = sorted(FIGS.glob("fig*.png"))
    print("  发现 %d 张：%s" % (len(files), ", ".join(f.name for f in files[:4]) + " …"))
    ok("配图 = 10 张", len(files) == 10, "%d 张" % len(files))

    nums = [int(re.match(r"fig(\d+)", f.name).group(1)) for f in files if re.match(r"fig\d+", f.name)]
    ok("图号 1–10 连续", nums == list(range(1, 11)), str(nums))

    up = DATA / "uploaded_urls.json"
    if up.exists():
        recs = read(up)
        ok("上传记录 = 10 条", len(recs) == 10, "%d 条" % len(recs))
        ok("图号与文件一一对应", sorted(int(x["fig"]) for x in recs) == list(range(1, 11)))
        missing = [x["path"] for x in recs if not (ROOT / x["path"]).exists()]
        ok("记录指向的文件都在", not missing, "缺 %d 个" % len(missing) if missing else "")

    cur = {f.name: md5(f) for f in files}
    if "--lock" in sys.argv or not LOCK.exists():
        LOCK.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        print("  [锁] 已写入 %s（提交到仓库后，后续运行将逐张比对）" % LOCK.relative_to(ROOT))
        ok("哈希锁已生成", True, "%d 张" % len(cur))
        return
    old = read(LOCK)
    diff = [k for k in old if old.get(k) != cur.get(k)]
    ok("哈希与锁一致", not diff, "全部一致" if not diff else "变动：%s" % ", ".join(diff))


# ───────────────────────── C5 正文 ─────────────────────────
def check_article() -> None:
    head("C5  正文硬性项  文章-CSDN终稿.md")
    cands = sorted(ROOT.glob("文章-CSDN终稿.md"))
    if not cands:
        ok("正文存在", False, "没找到 文章-CSDN终稿.md")
        return
    art = cands[-1]
    text = art.read_text(encoding="utf-8")
    print("  文件：%s" % art.name)

    lines, body, in_code = text.splitlines(), [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or s.startswith("|") or re.match(r"^!\[", s):
            continue
        if re.match(r"^\*?\*?图\s*\d+", s):   # 图注不计入
            continue
        body.append(s)
    b = "\n".join(body)
    words = len(re.findall(r"[\u4e00-\u9fff]", b)) + len(re.findall(r"[A-Za-z][A-Za-z0-9._/-]*", b))
    print("  正文 %d 字（去代码块/表格/图片行/图注；口径比文中自报的 6294 更严）" % words)
    ok("正文 ≥ 1500 字", words >= 1500, "%d 字，%.1f 倍" % (words, words / 1500))

    first = lines[0].strip()
    ok("标题包含元宝搜索", first.startswith("# 数字是填空") and "元宝搜索" in first, first[:24] + "…")

    figs_in_text = [int(x) for x in re.findall(r"^\*?图\s*(\d+)｜", text, re.M)]
    ok("图注编号 1–10 连续", figs_in_text == list(range(1, 11)), str(figs_in_text))

    imgs = re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)", text)
    ok("线上图片 = 10 张", len(imgs) == 10, "%d 张，全部 COS 直链" % len(imgs))

    # 只认「**作品阶段**：X」这种显式标注；文中引用旧表述不算
    m = re.search(r"\*\*作品阶段\*\*\s*[:：]\s*(学习实验|可演示原型|已用于日常工作|已上线服务)", text)
    ok("标注作品阶段", bool(m), m.group(1) if m else "未找到显式标注")
    ok("文首 + 文末两处声明", len(re.findall(r"作品阶段", text)) >= 2,
       "%d 处" % len(re.findall(r"作品阶段", text)))


# ───────────────────────── C6 密钥 ─────────────────────────
def check_secrets() -> None:
    head("C6  密钥扫描")
    pat = re.compile(r"AKID[A-Za-z0-9]{13,}")
    hits = []
    skip = {".git", "__pycache__", ".venv", "venv", "node_modules"}
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.name in {".env", ".env.example"} or set(p.parts) & skip:
            continue
        if p.suffix.lower() in {".png", ".jpg", ".pyc", ".zip"}:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        if pat.search(t):
            hits.append(str(p.relative_to(ROOT)))
    ok("无 AKID 明文", not hits, "干净" if not hits else "泄露：%s" % ", ".join(hits[:5]))
    ok(".env 已被 .gitignore 覆盖",
       (ROOT / ".gitignore").exists() and ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8"))


# ───────────────────────── main ─────────────────────────
def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    print("元宝搜索征文 · 一键复核")
    print("仓库：%s" % ROOT)
    print("python %s" % sys.version.split()[0])

    check_calls()
    check_ab()
    check_four()
    check_figs()
    check_article()
    check_secrets()

    bad = [r for r in RESULTS if not r[1]]
    head("汇总")
    print("  共 %d 项，通过 %d，失败 %d" % (len(RESULTS), len(RESULTS) - len(bad), len(bad)))
    if bad:
        print("\n  未通过：")
        for name, _, detail in bad:
            print("    - %s  %s" % (name, detail))
        print("\n  复核不通过。若你改动过原始数据，上面的差异就是原因。")
        sys.exit(1)
    print("\n  全部通过：文中每个数字都能用 data/ 下的原始数据重算出来。")


if __name__ == "__main__":
    main()
