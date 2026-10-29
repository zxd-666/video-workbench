from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode, urlsplit

from .constants import (
    ANTHROPIC_DEFAULT_BASE_URL,
    ANTHROPIC_DEFAULT_MODEL,
    GEMINI_DEFAULT_BASE_URL,
    GEMINI_DEFAULT_MODEL,
    LLMConfig,
    LLMError,
    MISSING_API_KEY_MESSAGE,
)

logger = logging.getLogger("video-workbench")


def _endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/v1/chat/completions") or clean.endswith("/chat/completions"):
        return clean
    if clean.endswith("/v1"):
        return f"{clean}/chat/completions"
    return f"{clean}/v1/chat/completions"


def _anthropic_endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/v1/messages") or clean.endswith("/messages"):
        return clean
    if clean.endswith("/v1"):
        return f"{clean}/messages"
    return f"{clean}/v1/messages"


def _gemini_endpoint(base_url: str, model: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith(":generateContent"):
        return clean
    if "/models/" in clean:
        return clean if clean.endswith(":generateContent") else f"{clean}:generateContent"
    if clean.endswith("/v1beta") or clean.endswith("/v1"):
        return f"{clean}/models/{model}:generateContent"
    return f"{clean}/v1beta/models/{model}:generateContent"


_REASONING_BLOCK_RE = re.compile(
    r"<(think|thinking|reasoning)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
# 模型被截断时可能只留下没闭合的 思考块，删到结尾即可。
_UNCLOSED_REASONING_RE = re.compile(
    r"<(think|thinking|reasoning)\b[^>]*>.*$",
    re.IGNORECASE | re.DOTALL,
)


def _strip_reasoning(text: str) -> str:
    """去掉推理模型输出的 思考块（MiniMax/DeepSeek 等会把思考写进 content）。"""
    cleaned = _REASONING_BLOCK_RE.sub("", text or "")
    cleaned = _UNCLOSED_REASONING_RE.sub("", cleaned)
    return cleaned.strip()


def _preview(text: str, limit: int = 1200) -> str:
    """报错时同时给出开头和结尾：模型常把 JSON 放在长段说明之后。"""
    raw = text or ""
    if len(raw) <= limit:
        return raw
    half = limit // 2
    return f"{raw[:half]}\n…（中间省略 {len(raw) - limit} 字）…\n{raw[-half:]}"


def _extract_json(text: str) -> dict[str, Any]:
    raw = _strip_reasoning(text)
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    # 模型常在 JSON 前后夹带说明文字，逐个 { 尝试解析，取最大的那个对象。
    decoder = json.JSONDecoder()
    best: dict[str, Any] | None = None
    best_size = -1
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw, index)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        size = len(json.dumps(value, ensure_ascii=False))
        if size > best_size:
            best, best_size = value, size
    if best is not None:
        return best
    raise json.JSONDecodeError("No JSON object found", raw, 0)


def _safe_url(url: str) -> str:
    """只保留 host + path，避免把 query 里的 key 写进错误信息或日志。"""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def _llm_timeout() -> int:
    # 长文案生成可能需要几分钟，默认放宽到 300s；可用 LLM_TIMEOUT 调整。
    try:
        return max(10, int(os.getenv("LLM_TIMEOUT", "300")))
    except ValueError:
        return 300


def _llm_max_tokens() -> int:
    # 分镜/文案较长，加上推理模型的思考过程，默认给足 16384；可用 LLM_MAX_TOKENS 调整。
    try:
        return max(512, int(os.getenv("LLM_MAX_TOKENS", "16384")))
    except ValueError:
        return 16384


# 推理模型常把大段思考写进正文，挤占输出额度；这里直接要求它别写。
_NO_REASONING_HINT = "\n\n请直接输出最终结果，不要输出你的分析或思考过程（不要使用 <think> 标签）。"

# 部分型号（如 MiniMax-M3.1-Flash）强制思考，传 thinking.disabled 会直接 400，
# 这里记住已经明确拒绝过的型号，避免每次都白跑一次请求。
_THINKING_UNSUPPORTED: set[str] = set()


def _thinking_disabled_by_default() -> bool:
    # LLM_THINKING=auto 表示不干预，由服务商自己决定
    return os.getenv("LLM_THINKING", "disabled").strip().lower() not in {
        "auto",
        "on",
        "enabled",
        "default",
    }


def _is_minimax(cfg: "LLMConfig") -> bool:
    return "minimax" in (cfg.base_url or "").lower() or (cfg.model or "").lower().startswith("minimax")


def _thinking_params(cfg: "LLMConfig") -> dict[str, Any]:
    """MiniMax 默认关闭思考：M3 等型号支持，Flash 强制思考则跳过。"""
    if not _thinking_disabled_by_default() or not _is_minimax(cfg):
        return {}
    if "flash" in (cfg.model or "").lower() or cfg.model in _THINKING_UNSUPPORTED:
        return {}
    # reasoning_split 让思考内容单独返回，不会混进正文
    return {"thinking": {"type": "disabled"}, "reasoning_split": True}


def _looks_like_token_limit_error(message: str) -> bool:
    lowered = message.lower()
    if "max_tokens" in lowered or "tokens_to_generate" in lowered:
        return True
    return "token" in lowered and any(
        word in lowered for word in ("limit", "exceed", "range", "must be", "not support")
    )


def _looks_like_unknown_model_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in ("unknown model", "model not exist", "model does not exist", "invalid model", "no such model")
    )


def _unknown_model_hint(cfg: LLMConfig, message: str) -> str:
    hint = ""
    if _is_minimax(cfg):
        hint = "（MiniMax 目前可用：MiniMax-M3.1-Flash、MiniMax-M3）"
    return (
        f"{message}\n"
        f"提示：模型名「{cfg.model}」在服务商那边不存在{hint}，"
        "请到「设置」里核对大小写和后缀（例如 -Flash），不要漏写。"
    )


# 模型名写错时依次尝试的 MiniMax 官方型号（MiniMax-M3 可关闭思考，优先）
_MINIMAX_FALLBACK_MODELS = ("MiniMax-M3", "MiniMax-M3.1-Flash")


def _fallback_models(cfg: LLMConfig, tried: set[str]) -> list[str]:
    if not _is_minimax(cfg):
        return []
    current = (cfg.model or "").strip().lower()
    return [
        model
        for model in _MINIMAX_FALLBACK_MODELS
        if model.lower() != current and model.lower() not in tried
    ]


def _http_json(url: str, body: dict[str, Any], headers: dict[str, str], timeout: int | None = None) -> dict[str, Any]:
    timeout = timeout or _llm_timeout()
    model = str(body.get("model") or "?")
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:1000]
        raise LLMError(f"LLM HTTP {exc.code}（{_safe_url(url)}，模型 {model}）：{detail}") from exc
    except Exception as exc:
        raise LLMError(f"LLM 请求失败（{_safe_url(url)}，模型 {model}，超时 {timeout}s）：{exc}") from exc


def _json_chat(url: str, body: dict[str, Any], headers: dict[str, str], timeout: int) -> tuple[str, str | None]:
    data = _http_json(url, body, headers, timeout)
    try:
        choice = (data.get("choices") or [])[0]
        message = choice.get("message") or {}
    except Exception as exc:
        raise LLMError(f"Unexpected LLM response: {str(data)[:1000]}") from exc
    return str(message.get("content") or ""), choice.get("finish_reason")


def _stream_chat(url: str, body: dict[str, Any], headers: dict[str, str], timeout: int) -> tuple[str, str | None]:
    """SSE 流式调用。

    慢模型（推理模型尤其）整段生成可能要几分钟，非流式请求在拿到第一个字节前
    就会触发读超时。改成流式后 timeout 只用来判断“多久没有新数据”，
    模型只要持续输出就能一直收下去。
    """
    model = str(body.get("model") or "?")
    stream_body = {**body, "stream": True}
    req = urllib.request.Request(
        url,
        data=json.dumps(stream_body, ensure_ascii=False).encode("utf-8"),
        headers={**headers, "Accept": "text/event-stream"},
        method="POST",
    )
    parts: list[str] = []
    finish_reason: str | None = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers_obj = getattr(resp, "headers", None) or {}
            content_type = str(headers_obj.get("Content-Type") or "").lower()
            if "text/event-stream" not in content_type:
                # 服务商忽略 stream=true，直接返回整段 JSON
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                try:
                    choice = (data.get("choices") or [])[0]
                    message = choice.get("message") or {}
                except Exception as exc:
                    raise LLMError(f"Unexpected LLM response: {str(data)[:1000]}") from exc
                return str(message.get("content") or ""), choice.get("finish_reason")

            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload in {"[DONE]", "DONE"}:
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                for item in chunk.get("choices") or []:
                    delta = item.get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        parts.append(str(piece))
                    if item.get("finish_reason"):
                        finish_reason = item.get("finish_reason")
    except LLMError:
        raise
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:1000]
        raise LLMError(f"LLM HTTP {exc.code}（{_safe_url(url)}，模型 {model}）：{detail}") from exc
    except Exception as exc:
        raise LLMError(
            f"LLM 请求失败（{_safe_url(url)}，模型 {model}，{timeout}s 内没有返回新数据）：{exc}"
        ) from exc
    return "".join(parts), finish_reason


def _chat_once(endpoint: str, body: dict[str, Any], headers: dict[str, str]) -> tuple[str, str | None]:
    try:
        return _stream_chat(endpoint, body, headers, _llm_timeout())
    except LLMError as exc:
        message = str(exc)
        if "LLM HTTP 400" in message and "stream" in message.lower():
            return _json_chat(endpoint, body, headers, _llm_timeout())
        raise


def _chat_text(system_prompt: str, user_content: str, cfg: LLMConfig) -> str:
    if not cfg.api_key:
        raise LLMError(MISSING_API_KEY_MESSAGE)
    if not cfg.base_url or not cfg.model:
        raise LLMError("请先在「设置」中填写文本接口 Base URL（例如 https://api.openai.com/v1）和模型名")

    max_tokens = _llm_max_tokens()
    endpoint = _endpoint(cfg.base_url)
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body: dict[str, Any] = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [
            {"role": "system", "content": f"{system_prompt}{_NO_REASONING_HINT}"},
            {"role": "user", "content": user_content},
        ],
    }
    thinking_params = _thinking_params(cfg)
    body.update(thinking_params)

    def truncated_error(budget_used: int) -> LLMError:
        return LLMError(
            f"模型输出被截断（模型 {cfg.model}，达到 max_tokens={budget_used} 上限）："
            "推理模型会把额度花在思考上。请在 .env 调大 LLM_MAX_TOKENS 后重启，"
            "或换一个非推理模型（如 DeepSeek-chat、Qwen-plus 等）"
        )

    # 服务商对 max_tokens 上限有硬限制时会返回 400，这里自动减半重试；
    # 反过来，推理模型把额度花光时自动翻倍再试一次（有上限，避免死循环）。
    budget = max_tokens
    ceiling = max(32768, max_tokens)
    truncated_budgets: set[int] = set()
    rejected_budgets: set[int] = set()
    tried_models: set[str] = set()

    while True:
        body["max_tokens"] = budget
        started = time.perf_counter()
        logger.info(
            "LLM 请求 模型=%s max_tokens=%s 关闭思考=%s",
            cfg.model,
            budget,
            "thinking" in body,
        )
        try:
            content, finish_reason = _chat_once(endpoint, body, headers)
        except LLMError as exc:
            message = str(exc)
            lowered = message.lower()
            # 模型名拼错时服务商直接 400，重试没有意义。MiniMax 自动换官方型号再试，
            # 换成官方型号都不行，就把可用型号直接写进报错。
            if "LLM HTTP 400" in message and _looks_like_unknown_model_error(message):
                candidates = _fallback_models(cfg, tried_models)
                if not candidates:
                    raise LLMError(_unknown_model_hint(cfg, message)) from exc
                logger.warning("模型 %s 不存在，自动改用 %s 重试", cfg.model, candidates[0])
                tried_models.add(candidates[0].lower())
                cfg = replace(cfg, model=candidates[0])
                body["model"] = candidates[0]
                # 换型号后思考参数可能要跟着变（Flash 不支持关闭思考）
                for key in ("thinking", "reasoning_split"):
                    body.pop(key, None)
                thinking_params = _thinking_params(cfg)
                body.update(thinking_params)
                continue
            # 个别型号（MiniMax-M3.1-Flash 等）强制思考，传 thinking 参数会直接 400：
            # 去掉参数重试一次，并记住这个型号，下次不再白跑。
            if (
                "LLM HTTP 400" in message
                and thinking_params
                and ("thinking" in lowered or "reasoning_split" in lowered)
            ):
                logger.warning("模型 %s 不支持关闭思考，已去掉 thinking 参数重试", cfg.model)
                _THINKING_UNSUPPORTED.add(cfg.model)
                for key in thinking_params:
                    body.pop(key, None)
                thinking_params = {}
                continue
            token_limit = "LLM HTTP 400" in message and _looks_like_token_limit_error(message)
            if token_limit and budget > 4096:
                smaller = max(4096, budget // 2)
                if smaller in truncated_budgets:
                    raise truncated_error(smaller) from exc
                rejected_budgets.add(budget)
                budget = smaller
                continue
            raise

        elapsed = time.perf_counter() - started
        if finish_reason == "length":
            truncated_budgets.add(budget)
            larger = min(ceiling, budget * 2)
            if larger > budget and larger not in rejected_budgets:
                logger.warning(
                    "LLM 输出达到 max_tokens=%s（模型 %s，耗时 %.1fs），翻倍到 %s 重试",
                    budget,
                    cfg.model,
                    elapsed,
                    larger,
                )
                budget = larger
                continue
            raise truncated_error(budget)
        logger.info(
            "LLM 完成 模型=%s max_tokens=%s finish=%s 耗时 %.1fs 输出 %d 字",
            cfg.model,
            budget,
            finish_reason,
            elapsed,
            len(content or ""),
        )
        break

    text = _strip_reasoning(str(content or ""))
    if not text:
        raise LLMError(
            "模型只返回了思考过程，没有给出正文："
            "请换用非推理模型，或调大 LLM_MAX_TOKENS 后重试"
        )
    return text


def _anthropic_text(system_prompt: str, user_content: str, cfg: LLMConfig) -> str:
    if not cfg.api_key:
        raise LLMError(MISSING_API_KEY_MESSAGE)
    base_url = cfg.base_url or ANTHROPIC_DEFAULT_BASE_URL
    model = cfg.model or ANTHROPIC_DEFAULT_MODEL
    if not base_url or not model:
        raise LLMError("请先在「设置」中填写文本接口 Base URL（例如 https://api.openai.com/v1）和模型名")

    body = {
        "model": model,
        "max_tokens": 4096,
        "temperature": cfg.temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    data = _http_json(
        _anthropic_endpoint(base_url),
        body,
        {
            "x-api-key": cfg.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        content = data.get("content") or []
        texts = [
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "\n".join(part for part in texts if part).strip()
        if not text:
            raise KeyError("empty content")
        return text
    except Exception as exc:
        raise LLMError(f"Unexpected Anthropic response: {str(data)[:1000]}") from exc


def _gemini_text(system_prompt: str, user_content: str, cfg: LLMConfig) -> str:
    if not cfg.api_key:
        raise LLMError(MISSING_API_KEY_MESSAGE)
    base_url = cfg.base_url or GEMINI_DEFAULT_BASE_URL
    model = cfg.model or GEMINI_DEFAULT_MODEL
    if not base_url or not model:
        raise LLMError("请先在「设置」中填写文本接口 Base URL（例如 https://api.openai.com/v1）和模型名")

    endpoint = _gemini_endpoint(base_url, model)
    if "key=" not in endpoint:
        sep = "&" if "?" in endpoint else "?"
        endpoint = f"{endpoint}{sep}{urlencode({'key': cfg.api_key})}"

    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": cfg.temperature},
    }
    data = _http_json(
        endpoint,
        body,
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        candidates = data.get("candidates") or []
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        texts = [str(part.get("text") or "") for part in parts if isinstance(part, dict)]
        text = "\n".join(part for part in texts if part).strip()
        if not text:
            raise KeyError("empty content")
        return text
    except Exception as exc:
        raise LLMError(f"Unexpected Gemini response: {str(data)[:1000]}") from exc


def _provider_text(system_prompt: str, user_content: str, cfg: LLMConfig) -> str:
    provider = (cfg.provider or "openai").lower()
    if provider in {"openai", "openai_compatible", "compatible"}:
        return _chat_text(system_prompt, user_content, cfg)
    if provider in {"anthropic", "claude"}:
        return _anthropic_text(
            system_prompt,
            user_content,
            replace(
                cfg,
                base_url=cfg.base_url or ANTHROPIC_DEFAULT_BASE_URL,
                model=cfg.model or ANTHROPIC_DEFAULT_MODEL,
            ),
        )
    if provider in {"gemini", "google", "google_gemini"}:
        return _gemini_text(
            system_prompt,
            user_content,
            replace(
                cfg,
                base_url=cfg.base_url or GEMINI_DEFAULT_BASE_URL,
                model=cfg.model or GEMINI_DEFAULT_MODEL,
            ),
        )
    raise LLMError(f"Unsupported text provider: {cfg.provider}")


def _openai_text(prompt: str, topic: str, cfg: LLMConfig) -> str:
    return _chat_text(prompt, f"???{topic}", cfg)
