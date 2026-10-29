from __future__ import annotations

from app.image_adapter import ImageError, classify_image_http_error


def _classify(status_code: int, detail: str) -> ImageError:
    return classify_image_http_error(status_code, detail)


def test_insufficient_balance_is_balance_and_not_retried():
    """402 insufficient balance 是账号级的：必须归到 balance，且不进重试循环。"""

    err = _classify(402, '{"error": {"message": "insufficient balance", "code": "insufficient_balance"}}')

    assert err.category == "balance"
    assert err.status_code == 402
    assert "余额" in err.message
    assert "充值" in err.suggestion


def test_balance_marker_without_402_is_also_balance():
    err = _classify(400, '{"error": {"message": "账户余额不足，请充值后重试"}}')

    assert err.category == "balance"
    assert "余额" in err.message


def test_balance_category_is_non_retryable():
    from app.image_jobs import _is_non_retryable

    err = _classify(402, '{"error": {"message": "insufficient balance"}}')

    assert _is_non_retryable(err) is True


def test_invalid_api_key_is_auth_and_not_retried():
    from app.image_jobs import _is_non_retryable

    err = _classify(401, '{"error": {"message": "Invalid API key", "code": "invalid_api_key"}}')

    assert err.category == "auth"
    assert _is_non_retryable(err) is True
    assert "鉴权" in err.message


def test_rate_limit_stays_quota_and_retryable_like_before():
    err = _classify(429, '{"error": {"message": "Rate limit reached for requests"}}')

    assert err.category == "quota"
    assert err.status_code == 429


def test_generic_bad_request_still_retried():
    from app.image_jobs import _is_non_retryable

    err = _classify(500, '{"error": {"message": "internal server error"}}')

    assert err.category == "request"
    assert _is_non_retryable(err) is False


def test_account_level_errors_are_detected_by_runner_helper():
    from app.images.jobs.runner import _is_account_level

    assert _is_account_level(_classify(402, '{"error": {"message": "insufficient balance"}}')) is True
    assert _is_account_level(_classify(401, '{"error": {"message": "invalid api key"}}')) is True
    assert _is_account_level(_classify(500, '{"error": {"message": "boom"}}')) is False
    # 429 限流只影响当前镜头，不能把整批任务停掉
    assert _is_account_level(_classify(429, '{"error": {"message": "rate limit reached"}}')) is False
    assert _is_account_level(RuntimeError("boom")) is False
