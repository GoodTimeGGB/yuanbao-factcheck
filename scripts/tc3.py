# -*- coding: utf-8 -*-
"""
腾讯云 API 3.0 TC3-HMAC-SHA256 签名（仅标准库，无 SDK 依赖）

单独抽出来是为了征文里能直接贴这一段——签名是多数人接 API 时卡住的第一个坑。
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sign_request(
    secret_id: str,
    secret_key: str,
    host: str,
    service: str,
    action: str,
    payload: str,
    content_type: str = "application/json; charset=utf-8",
    timestamp: int | None = None,
) -> dict:
    """返回可直接塞进 requests.post 的 headers。

    payload 必须是「即将发送的那个字符串」本身——签名算的是它的哈希，
    所以调用方要保证签名用的 body 和实际发送的 body 逐字节相同。
    """
    ts = timestamp or int(time.time())
    date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

    # --- 1. 拼规范请求串 ---
    http_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    # 参与签名的 header 必须与实际发送的一致；x-tc-action 的签名值取小写
    canonical_headers = (
        "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (content_type, host, action.lower())
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = _sha256_hex(payload)
    canonical_request = "\n".join(
        [http_method, canonical_uri, canonical_querystring,
         canonical_headers, signed_headers, hashed_payload]
    )

    # --- 2. 拼待签字符串 ---
    algorithm = "TC3-HMAC-SHA256"
    credential_scope = "%s/%s/tc3_request" % (date, service)
    string_to_sign = "\n".join(
        [algorithm, str(ts), credential_scope, _sha256_hex(canonical_request)]
    )

    # --- 3. 逐级派生签名密钥（注意第一级是 "TC3" + SecretKey）---
    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, service)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # --- 4. Authorization ---
    authorization = (
        "%s Credential=%s/%s, SignedHeaders=%s, Signature=%s"
        % (algorithm, secret_id, credential_scope, signed_headers, signature)
    )

    return {
        "Authorization": authorization,
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Version": "2025-05-08",
        "X-TC-Timestamp": str(ts),
    }


if __name__ == "__main__":
    # 自检：用官方文档里的示例参数打一遍，确认不抛异常
    h = sign_request("AKIDxxx", "SECRETxxx", "wsa.tencentcloudapi.com", "wsa",
                     "SearchPro", '{"Query":"人工智能发展现状"}', timestamp=1700000000)
    print(h["Authorization"][:120] + "...")
