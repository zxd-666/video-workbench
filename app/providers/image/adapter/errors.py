from __future__ import annotations

import json
import urllib.error
import urllib.request

from .constants import (
    IMAGE_AUTH_SUGGESTION,
    IMAGE_BALANCE_SUGGESTION,
    IMAGE_QUOTA_SUGGESTION,
    ImageError,
    PROMPT_POLICY_SUGGESTION,
)

def _extract_provider_error(raw: str) -> tuple[str, str, str]:
    message = raw.strip()
    code = ""
    error_type = ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return message, code, error_type
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or message)
            code = str(error.get("code") or "")
            error_type = str(error.get("type") or "")
        else:
            message = str(data.get("message") or data.get("detail") or message)
            code = str(data.get("code") or "")
            error_type = str(data.get("type") or "")
    return message.strip(), code.strip(), error_type.strip()

def _is_prompt_policy_error(message: str, code: str = "", error_type: str = "") -> bool:
    text = " ".join([message or "", code or "", error_type or ""]).lower()
    english_markers = (
        "content_policy_violation",
        "policy_violation",
        "content policy",
        "safety policy",
        "safety system",
        "moderation",
        "blocked",
        "unsafe",
        "sensitive",
    )
    chinese_markers = ("违反", "不合规", "防护限制", "内容安全", "安全策略", "敏感", "违规", "审核")
    return any(marker in text for marker in english_markers) or any(marker in message for marker in chinese_markers)

_BALANCE_MARKERS = (
    "insufficient balance",
    "insufficient_quota",
    "insufficient quota",
    "insufficient funds",
    "exceeded your current quota",
    "payment required",
    "billing",
    "余额不足",
    "余额不够",
    "额度不足",
    "欠费",
    "充值",
)

_AUTH_MARKERS = (
    "invalid api key",
    "incorrect api key",
    "invalid_api_key",
    "unauthorized",
    "authentication",
    "api key not valid",
    "no permission",
    "密钥无效",
    "鉴权失败",
)


def _is_balance_error(status_code: int, detail: str) -> bool:
    if status_code == 402:
        return True
    return any(marker in detail for marker in _BALANCE_MARKERS)


def _is_auth_error(status_code: int, detail: str) -> bool:
    if status_code in (401, 403):
        return True
    return any(marker in detail for marker in _AUTH_MARKERS)


def classify_image_http_error(status_code: int, raw_detail: str) -> ImageError:
    message, code, error_type = _extract_provider_error(raw_detail)
    quota_text = " ".join([message or "", code or "", error_type or ""]).lower()
    # 余额/欠费是账号级问题：这一张失败，后面的几百张也会一样失败，
    # 所以单独归类成 balance（非重试、整批停机），不要把 429 限流也混进来 —— 限流是会恢复的。
    if _is_balance_error(status_code, quota_text):
        return ImageError(
            f"生图接口余额/额度不足：{message or raw_detail}",
            code=code or f"http_{status_code}",
            category="balance",
            status_code=status_code,
            suggestion=IMAGE_BALANCE_SUGGESTION,
        )
    if _is_auth_error(status_code, quota_text):
        return ImageError(
            f"生图接口鉴权失败（HTTP {status_code}）：{message or raw_detail}",
            code=code or f"http_{status_code}",
            category="auth",
            status_code=status_code,
            suggestion=IMAGE_AUTH_SUGGESTION,
        )
    if status_code == 429 or "quota" in quota_text or "rate limit" in quota_text or "too many requests" in quota_text:
        return ImageError(
            f"图片接口额度不足或限流：{message or raw_detail}",
            code=code or f"http_{status_code}",
            category="quota",
            status_code=status_code,
            suggestion=IMAGE_QUOTA_SUGGESTION,
        )
    if _is_prompt_policy_error(message, code, error_type):
        return ImageError(
            f"提示词被内容安全策略拦截：{message}",
            code=code or f"http_{status_code}",
            category="prompt_policy",
            status_code=status_code,
            suggestion=PROMPT_POLICY_SUGGESTION,
        )
    return ImageError(
        f"Image HTTP {status_code}: {message or raw_detail}",
        code=code or f"http_{status_code}",
        category="request",
        status_code=status_code,
    )

