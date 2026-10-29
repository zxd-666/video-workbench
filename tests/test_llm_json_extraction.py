import json

import pytest

from app.providers.llm.adapter import client
from app.providers.llm.adapter.client import _extract_json, _strip_reasoning
from app.providers.llm.adapter.constants import LLMConfig, LLMError


class FakeResponse:
    def __init__(self, lines, content_type="text/event-stream"):
        self._lines = [line.encode("utf-8") for line in lines]
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self._lines)

    def read(self):
        return b"".join(self._lines)


def test_strip_reasoning_removes_think_block():
    text = "<think>先想一下 {不是 JSON}</think>\n{\"title\": \"新项目\"}"
    assert _strip_reasoning(text) == '{"title": "新项目"}'


def test_extract_json_ignores_reasoning_braces():
    text = (
        "<think>需要输出 {\"title\": ...} 这样的结构，先规划 10 个分镜。</think>\n"
        '```json\n{"title": "新项目", "shots": [{"index": 1, "voiceover": "今天体验的人生副本是：新项目"}]}\n```'
    )
    data = _extract_json(text)
    assert data["title"] == "新项目"
    assert len(data["shots"]) == 1


def test_extract_json_handles_text_around_json():
    text = '好的，结果如下：\n{"topic": "外卖员", "intro": "在县城送外卖"}\n希望有帮助。'
    data = _extract_json(text)
    assert data["topic"] == "外卖员"


def test_extract_json_truncated_reasoning_raises():
    text = "<think>We need output strict JSON only, but the model was cut off"
    with pytest.raises(json.JSONDecodeError):
        _extract_json(text)


def test_chat_text_halves_max_tokens_when_provider_rejects(monkeypatch):
    seen = []

    def fake_chat(endpoint, body, headers):
        seen.append(body["max_tokens"])
        if body["max_tokens"] > 4096:
            raise LLMError("LLM HTTP 400（https://x/v1/chat/completions，模型 m）：max_tokens must be <= 8192")
        return "正文", "stop"

    monkeypatch.setenv("LLM_MAX_TOKENS", "16384")
    monkeypatch.setattr(client, "_chat_once", fake_chat)

    cfg = LLMConfig(provider="openai", base_url="https://x/v1", model="m", api_key="k", temperature=0.8)
    assert client._chat_text("system", "user", cfg) == "正文"
    assert seen == [16384, 8192, 4096]


def test_chat_text_reports_truncated_output(monkeypatch):
    seen = []

    def fake_chat(endpoint, body, headers):
        seen.append(body["max_tokens"])
        return "<think>想太多", "length"

    monkeypatch.setenv("LLM_MAX_TOKENS", "16384")
    monkeypatch.setattr(client, "_chat_once", fake_chat)

    cfg = LLMConfig(provider="openai", base_url="https://x/v1", model="reasoner", api_key="k", temperature=0.8)
    with pytest.raises(LLMError, match="max_tokens=32768"):
        client._chat_text("system", "user", cfg)
    # 先按 16384 失败，翻倍到 32768 再试一次后放弃
    assert seen == [16384, 32768]


def test_chat_text_stops_when_provider_caps_max_tokens(monkeypatch):
    seen = []

    def fake_chat(endpoint, body, headers):
        seen.append(body["max_tokens"])
        if body["max_tokens"] > 16384:
            raise LLMError("LLM HTTP 400（https://x/v1/chat/completions，模型 m）：max_tokens too large")
        return "<think>想太多", "length"

    monkeypatch.setenv("LLM_MAX_TOKENS", "16384")
    monkeypatch.setattr(client, "_chat_once", fake_chat)

    cfg = LLMConfig(provider="openai", base_url="https://x/v1", model="reasoner", api_key="k", temperature=0.8)
    with pytest.raises(LLMError, match="max_tokens=16384"):
        client._chat_text("system", "user", cfg)
    assert seen == [16384, 32768]


def test_chat_text_asks_model_not_to_write_reasoning(monkeypatch):
    captured = {}

    def fake_chat(endpoint, body, headers):
        captured.update(body)
        return "正文", "stop"

    monkeypatch.setattr(client, "_chat_once", fake_chat)
    cfg = LLMConfig(provider="openai", base_url="https://x/v1", model="m", api_key="k", temperature=0.8)
    client._chat_text("system", "user", cfg)

    assert "不要输出你的分析" in captured["messages"][0]["content"]
    assert captured["max_tokens"] > 0


def test_stream_chat_accumulates_sse_deltas(monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"reasoning_content":"想一想"},"finish_reason":null}]}\n',
        'data: {"choices":[{"delta":{"content":"今天体验"},"finish_reason":null}]}\n',
        'data: {"choices":[{"delta":{"content":"的人生副本"},"finish_reason":"stop"}]}\n',
        "data: [DONE]\n",
    ]
    monkeypatch.setattr(
        client.urllib.request, "urlopen", lambda req, timeout=None: FakeResponse(lines)
    )
    content, finish = client._stream_chat("https://x/v1/chat/completions", {"model": "m"}, {}, 300)
    assert content == "今天体验的人生副本"
    assert finish == "stop"


def test_stream_chat_accepts_plain_json_response(monkeypatch):
    body = json.dumps({"choices": [{"message": {"content": "正文"}, "finish_reason": "stop"}]})
    monkeypatch.setattr(
        client.urllib.request,
        "urlopen",
        lambda req, timeout=None: FakeResponse([body], "application/json"),
    )
    content, finish = client._stream_chat("https://x/v1/chat/completions", {"model": "m"}, {}, 300)
    assert content == "正文"
    assert finish == "stop"


def test_chat_once_falls_back_when_stream_is_rejected(monkeypatch):
    calls = []

    def fake_stream(endpoint, body, headers, timeout):
        calls.append("stream")
        raise LLMError("LLM HTTP 400（https://x/v1/chat/completions，模型 m）：stream is not supported")

    def fake_json(endpoint, body, headers, timeout):
        calls.append("json")
        return "正文", "stop"

    monkeypatch.setattr(client, "_stream_chat", fake_stream)
    monkeypatch.setattr(client, "_json_chat", fake_json)

    assert client._chat_once("https://x/v1/chat/completions", {"model": "m"}, {}) == ("正文", "stop")
    assert calls == ["stream", "json"]


def _minimax_cfg(model: str) -> LLMConfig:
    return LLMConfig(
        provider="openai",
        base_url="https://api.minimaxi.com/v1",
        model=model,
        api_key="k",
        temperature=0.8,
    )


def test_thinking_disabled_for_minimax_m3(monkeypatch):
    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.setattr(client, "_THINKING_UNSUPPORTED", set())
    assert client._thinking_params(_minimax_cfg("MiniMax-M3")) == {
        "thinking": {"type": "disabled"},
        "reasoning_split": True,
    }


def test_thinking_skipped_for_flash_model(monkeypatch):
    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.setattr(client, "_THINKING_UNSUPPORTED", set())
    # Flash 强制思考，传 thinking.disabled 会 400，所以不传
    assert client._thinking_params(_minimax_cfg("MiniMax-M3.1-Flash")) == {}


def test_thinking_skipped_for_non_minimax(monkeypatch):
    monkeypatch.delenv("LLM_THINKING", raising=False)
    cfg = LLMConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key="k",
        temperature=0.8,
    )
    assert client._thinking_params(cfg) == {}


def test_thinking_skipped_when_set_to_auto(monkeypatch):
    monkeypatch.setenv("LLM_THINKING", "auto")
    monkeypatch.setattr(client, "_THINKING_UNSUPPORTED", set())
    assert client._thinking_params(_minimax_cfg("MiniMax-M3")) == {}


def test_chat_text_drops_thinking_params_when_provider_rejects(monkeypatch):
    bodies = []
    unsupported = set()

    def fake_chat(endpoint, body, headers):
        bodies.append(dict(body))
        if "thinking" in body:
            raise LLMError("LLM HTTP 400（https://api.minimaxi.com/v1/chat/completions，模型 MiniMax-M3）：thinking is not supported")
        return "正文", "stop"

    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.setattr(client, "_THINKING_UNSUPPORTED", unsupported)
    monkeypatch.setattr(client, "_chat_once", fake_chat)

    assert client._chat_text("system", "user", _minimax_cfg("MiniMax-M3")) == "正文"
    assert len(bodies) == 2
    assert "thinking" in bodies[0]
    assert "thinking" not in bodies[1] and "reasoning_split" not in bodies[1]
    # 记住这个型号，后续请求不再带参数
    assert "MiniMax-M3" in unsupported
    assert client._thinking_params(_minimax_cfg("MiniMax-M3")) == {}


def _unknown_model_error(model: str) -> LLMError:
    return LLMError(
        f"LLM HTTP 400（https://api.minimaxi.com/v1/chat/completions，模型 {model}）："
        f'{{"type":"error","error":{{"message":"invalid params, unknown model \'{model.lower()}\' (2013)"}}}}'
    )


def test_chat_text_falls_back_to_known_minimax_model(monkeypatch):
    seen = []

    def fake_chat(endpoint, body, headers):
        seen.append(body["model"])
        if body["model"] != "MiniMax-M3":
            raise _unknown_model_error(body["model"])
        return "正文", "stop"

    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.setattr(client, "_THINKING_UNSUPPORTED", set())
    monkeypatch.setattr(client, "_chat_once", fake_chat)

    assert client._chat_text("system", "user", _minimax_cfg("minimax-m3.1")) == "正文"
    assert seen == ["minimax-m3.1", "MiniMax-M3"]


def test_chat_text_explains_unknown_model(monkeypatch):
    models = []

    def fake_chat(endpoint, body, headers):
        models.append(body["model"])
        raise _unknown_model_error(body["model"])

    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.setattr(client, "_THINKING_UNSUPPORTED", set())
    monkeypatch.setattr(client, "_chat_once", fake_chat)

    with pytest.raises(LLMError) as info:
        client._chat_text("system", "user", _minimax_cfg("MiniMax-M3.1"))
    # 依次试过两个官方型号后放弃，且不重复尝试
    assert models == ["MiniMax-M3.1", "MiniMax-M3", "MiniMax-M3.1-Flash"]
    message = str(info.value)
    assert "MiniMax-M3.1-Flash" in message
    assert "不存在" in message
