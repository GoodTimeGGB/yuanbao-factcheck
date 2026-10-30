#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""上传后核对：正文里的 10 张图是否全部换成线上 URL，顺序与图注号是否对得上。

用法：
    python scripts/check_links.py            # 只看本地/线上状态
    python scripts/check_links.py --http     # 顺带逐个请求，确认 URL 能打开
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "文章正文-v1.md")

IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
CAP = re.compile(r"\*图\s*(\d+)｜")


def main():
    check_http = "--http" in sys.argv
    text = open(MD, encoding="utf-8").read()

    rows = []
    for m in IMG.finditer(text):
        alt, path = m.group(1), m.group(2)
        # 图注紧跟在图片后，通常在 200 字内
        tail = text[m.end(): m.end() + 400]
        cap = CAP.search(tail)
        rows.append({
            "alt": alt,
            "path": path,
            "fig": cap.group(1) if cap else "?",
            "remote": path.startswith(("http://", "https://")),
        })

    local = [r for r in rows if not r["remote"]]
    remote = [r for r in rows if r["remote"]]

    print("正文图片总数：%d（本地 %d / 线上 %d）\n" % (len(rows), len(local), len(remote)))

    print("%-4s %-4s %-34s %s" % ("序号", "图注", "alt", "路径"))
    print("-" * 96)
    for i, r in enumerate(rows, 1):
        p = r["path"] if r["remote"] else r["path"]
        mark = "" if r["remote"] else "  ← 待上传"
        print("%-4d 图%-3s %-34s %s%s" % (i, r["fig"], (r["alt"] or "")[:32], p[-58:], mark))

    print()
    order = [r["fig"] for r in rows]
    expect = [str(i) for i in range(1, len(rows) + 1)]
    if order == expect:
        print(">>> 顺序正确：正文第 N 张 → 图 N")
    else:
        print(">>> 顺序异常：实际 %s，应为 %s" % (order, expect))

    if local:
        print(">>> 未完成：还有 %d 张是本地路径" % len(local))
    else:
        print(">>> 通过：全部为线上链接")

    plain = [r for r in remote if r["path"].startswith("http://")]
    if plain:
        print(">>> 注意：有 %d 张是 http:// 而非 https://，CSDN 编辑器可能拦" % len(plain))
    encoded = [r for r in remote if "%" in r["path"]]
    if encoded:
        print(">>> 注意：有 %d 张 URL 带百分号编码（中文文件名导致），能用但不好看" % len(encoded))

    if check_http and remote:
        try:
            import requests
        except ImportError:
            print("\n未安装 requests，跳过 HTTP 检查")
            return 0 if not local else 1
        print("\n逐个请求确认可访问：")
        bad = 0
        for i, r in enumerate(remote, 1):
            try:
                resp = requests.head(r["path"], timeout=15, allow_redirects=True)
                if resp.status_code >= 400:
                    resp = requests.get(r["path"], timeout=15, stream=True)
                code = resp.status_code
            except Exception as e:
                code = type(e).__name__
            if code != 200:
                bad += 1
                print("  BAD %-22s 第 %d 张（图 %s）" % (code, i, r["fig"]))
        print("打不开的：%d 张" % bad)
        return 0 if bad == 0 and not local else 1

    return 0 if not local else 1


if __name__ == "__main__":
    sys.exit(main())
