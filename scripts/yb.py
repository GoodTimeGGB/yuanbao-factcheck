# -*- coding: utf-8 -*-
"""
元宝搜索 SearchPro 调用底座（腾讯云 API 3.0 / TC3 签名）

- 端点 wsa.tencentcloudapi.com，Action=SearchPro，Version=2025-05-08
- 每次调用写一行 JSONL 日志（query / 参数 / 耗时 / 条数 / 版本 / 是否报错），
  这份日志就是征文要求的"运行证据"，可直接导成表格截图。
- 密钥只从 .env 读，不进日志、不进原始返回落盘。

用法：
    python scripts/yb.py "特斯拉股价" --mode 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tc3 import sign_request  # noqa: E402

HOST = "wsa.tencentcloudapi.com"
SERVICE = "wsa"
ENDPOINT = "https://" + HOST
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOG = DATA / "calls.jsonl"
RAW_DIR = DATA / "raw"
CST = timezone(timedelta(hours=8))

VALID_CNT = (10, 20, 30, 40, 50)


def _read_env_file(p: pathlib.Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip("'\"")
    return out


def load_creds() -> tuple[str, str]:
    """按 环境变量 → 项目根 .env 找 AK/SK。返回明文但不打印。"""
    sid = (os.getenv("TENCENTCLOUD_SECRET_ID") or "").strip()
    skey = (os.getenv("TENCENTCLOUD_SECRET_KEY") or "").strip()
    if sid and skey:
        return sid, skey
    for p in (ROOT / ".env", ROOT / "scripts" / ".env"):
        env = _read_env_file(p)
        sid = sid or env.get("TENCENTCLOUD_SECRET_ID", "")
        skey = skey or env.get("TENCENTCLOUD_SECRET_KEY", "")
        if sid and skey:
            return sid, skey
    sys.exit(
        "[x] 没找到密钥。在 %s 写两行：\n"
        "    TENCENTCLOUD_SECRET_ID=AKID...\n"
        "    TENCENTCLOUD_SECRET_KEY=..." % (ROOT / ".env")
    )


def _log(rec: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def search(
    query: str,
    mode: int | None = 2,
    cnt: int = 10,
    freshness: str | None = None,
    site: str | None = None,
    industry: str | None = None,
    deeplinks: bool | None = None,
    save_raw: bool = False,
    tag: str = "",
) -> dict:
    """调一次 SearchPro。返回 {pages, elapsed_ms, ok, err, version, request_id}"""
    if cnt not in VALID_CNT:
        raise ValueError("Cnt 只能取 10/20/30/40/50，收到 %r" % cnt)

    payload_obj = {"Query": query, "Cnt": cnt}
    if mode is not None:
        payload_obj["Mode"] = mode
    if freshness:
        payload_obj["Freshness"] = freshness
    if site:
        payload_obj["Site"] = site
    if industry:
        payload_obj["Industry"] = industry
    if deeplinks is not None:
        payload_obj["Deeplinks"] = deeplinks

    # 关键：签名与发送必须用同一个字符串，所以先序列化再复用
    body = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))
    sid, skey = load_creds()
    headers = sign_request(sid, skey, HOST, SERVICE, "SearchPro", body)

    ts = datetime.now(CST).isoformat(timespec="seconds")
    t0 = time.time()
    ok, err, pages, http_code, raw = False, "", [], None, None
    version = request_id = ""
    try:
        r = requests.post(
            ENDPOINT, headers=headers,
            data=body.encode("utf-8"), timeout=20
        )
        http_code = r.status_code
        r.raise_for_status()
        raw = r.json()
        body_resp = raw.get("Response") or {}
        request_id = body_resp.get("RequestId") or ""
        version = body_resp.get("Version") or ""
        if body_resp.get("Error"):
            e = body_resp["Error"]
            err = "%s: %s" % (e.get("Code"), e.get("Message"))
        else:
            pages = [json.loads(p) for p in (body_resp.get("Pages") or [])]
            ok = True
    except Exception as e:  # noqa: BLE001
        err = "%s: %s" % (type(e).__name__, e)
        if isinstance(e, requests.HTTPError) and e.response is not None:
            try:
                err += " | " + e.response.text[:300]
            except Exception:  # noqa: BLE001
                pass
    elapsed_ms = int((time.time() - t0) * 1000)

    _log({
        "ts": ts, "tag": tag, "query": query, "mode": mode, "cnt": cnt,
        "freshness": freshness, "site": site, "industry": industry,
        "n_results": len(pages), "elapsed_ms": elapsed_ms,
        "http": http_code, "version": version, "ok": ok, "err": err,
    })

    if save_raw and raw is not None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        h = hashlib.md5((query + str(mode) + ts).encode("utf-8")).hexdigest()[:12]
        (RAW_DIR / ("%s_%s.json" % (h, tag or "q"))).write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return {"pages": pages, "elapsed_ms": elapsed_ms, "ok": ok, "err": err,
            "version": version, "request_id": request_id}


def brief(pages: list[dict]) -> str:
    if not pages:
        return "  (0 条)"
    out = []
    for i, it in enumerate(pages, 1):
        extra = ""
        if it.get("authority_level") is not None:
            extra += " auth=%s" % it["authority_level"]
        if it.get("score") is not None:
            extra += " score=%.2f" % it["score"]
        out.append(
            "  [%d] %s\n      %s | %s%s\n      %s"
            % (i, (it.get("title") or "")[:70], it.get("site") or "?",
               it.get("date") or "无日期", extra, it.get("url") or "")
        )
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--mode", type=int, default=2, choices=[0, 1, 2])
    ap.add_argument("--cnt", type=int, default=10)
    ap.add_argument("--freshness", default=None)
    ap.add_argument("--site", default=None)
    ap.add_argument("--industry", default=None, choices=["gov", "news", "acad", "finance"])
    ap.add_argument("--raw", action="store_true")
    args = ap.parse_args()

    res = search(args.query, mode=args.mode, cnt=args.cnt,
                 freshness=args.freshness, site=args.site,
                 industry=args.industry, save_raw=args.raw, tag="cli")
    print("Query: %s | Mode=%s Cnt=%s | version=%s | %dms | %d 条"
          % (args.query, args.mode, args.cnt, res["version"] or "?",
             res["elapsed_ms"], len(res["pages"])))
    if res["err"]:
        print("[x] %s" % res["err"])
        return
    print(brief(res["pages"]))


if __name__ == "__main__":
    main()
