"""Tests for provider failover. Providers are faked with httpx.MockTransport,
and requests go through the real AsyncOpenAI client, so the exceptions the
agent endpoint catches (RateLimitError etc.) are the ones checked here."""
import json
from email.utils import formatdate

import httpx
import openai
import pytest
from openai import AsyncOpenAI

from backend.ai_failover import (
    DEFAULT_COOLDOWN,
    ERROR_COOLDOWN,
    MAX_COOLDOWN,
    FailoverTransport,
    Provider,
    load_providers,
)

GROQ = Provider("groq", "https://api.groq.com/openai/v1", "gsk-key", "openai/gpt-oss-120b")
GEMINI = Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "gem-key", "gemini-flash-latest")
CEREBRAS = Provider("cerebras", "https://api.cerebras.ai/v1", "csk-key", "gpt-oss-120b")
PROVIDERS = [GROQ, GEMINI, CEREBRAS]
HOSTS = {p.name: httpx.URL(p.base_url).host for p in PROVIDERS}


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


class FakeProviders:
    """Answers per host from a script: a status code, a (status, headers) pair,
    an exception to raise, or 200 when nothing is scripted."""

    def __init__(self):
        self.script: dict[str, list] = {}
        self.calls: list[httpx.Request] = []

    def queue(self, provider: Provider, *outcomes):
        self.script.setdefault(HOSTS[provider.name], []).extend(outcomes)

    def called(self) -> list[str]:
        by_host = {host: name for name, host in HOSTS.items()}
        return [by_host[r.url.host] for r in self.calls]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        queue = self.script.get(request.url.host, [])
        outcome = queue.pop(0) if queue else 200
        if isinstance(outcome, Exception):
            raise outcome
        status, headers, message = (outcome + ("",))[:3] if isinstance(outcome, tuple) else (outcome, {}, "")
        if status == 200:
            body = json.loads(request.content)
            return httpx.Response(200, json={
                "id": "chatcmpl-1", "object": "chat.completion", "created": 0,
                "model": body["model"],
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": f"from {request.url.host}"}}],
            })
        return httpx.Response(status, headers=headers, json={"error": {"message": message or f"error {status}"}})


@pytest.fixture
def fake():
    return FakeProviders()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def transport(fake, clock):
    return FailoverTransport(PROVIDERS, inner=httpx.MockTransport(fake.handler), clock=clock)


def _client(transport):
    return AsyncOpenAI(
        base_url=PROVIDERS[0].base_url,
        api_key="client-key-never-sent",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=transport),
    )


async def _chat(transport, **extra):
    return await _client(transport).chat.completions.create(
        model="whatever-the-sdk-sends",
        messages=[{"role": "user", "content": "check stock of rice"}],
        **extra,
    )


# ── Normal path ──────────────────────────────────────────────────────────────

async def test_uses_first_provider_when_healthy(fake, transport):
    result = await _chat(transport)
    assert fake.called() == ["groq"]
    assert result.model == "openai/gpt-oss-120b"


async def test_request_rewritten_for_each_provider(fake, transport):
    fake.queue(GROQ, 429)
    await _chat(transport)
    groq_req, gemini_req = fake.calls
    assert str(groq_req.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert str(gemini_req.url) == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert groq_req.headers["authorization"] == "Bearer gsk-key"
    assert gemini_req.headers["authorization"] == "Bearer gem-key"
    assert json.loads(groq_req.content)["model"] == "openai/gpt-oss-120b"
    assert json.loads(gemini_req.content)["model"] == "gemini-flash-latest"
    # The conversation is resent unchanged
    assert json.loads(gemini_req.content)["messages"] == [{"role": "user", "content": "check stock of rice"}]


async def test_client_key_is_never_sent(fake, transport):
    await _chat(transport)
    assert "client-key-never-sent" not in fake.calls[0].headers["authorization"]


async def test_chat_body_cleaned_for_providers(fake, transport):
    tools = [{"type": "function", "function": {
        "name": "transfer_to_inventory", "parameters": {"type": "object", "properties": {}, "required": []}}}]
    await _chat(transport, tools=tools, reasoning_effort="low", verbosity="low")
    body = json.loads(fake.calls[0].content)
    assert "reasoning_effort" not in body and "verbosity" not in body
    assert "required" not in body["tools"][0]["function"]["parameters"]


def _tool_call_history(signature=None):
    call = {"id": "call_1", "type": "function",
            "function": {"name": "check_stock", "arguments": '{"product_id": 5}'}}
    if signature:
        call["extra_content"] = {"google": {"thought_signature": signature}}
    return [{"role": "user", "content": "stock of product 5?"},
            {"role": "assistant", "content": None, "tool_calls": [call]},
            {"role": "tool", "tool_call_id": "call_1", "content": "42 units"}]


async def test_gemini_gets_placeholder_signature_on_tool_calls(fake, transport):
    fake.queue(GROQ, 429)
    await _client(transport).chat.completions.create(model="x", messages=_tool_call_history())
    groq_body, gemini_body = (json.loads(r.content) for r in fake.calls)
    gemini_call = gemini_body["messages"][1]["tool_calls"][0]
    assert gemini_call["extra_content"]["google"]["thought_signature"] == "skip_thought_signature_validator"
    # Other providers get the conversation unchanged
    assert "extra_content" not in groq_body["messages"][1]["tool_calls"][0]


async def test_gemini_keeps_a_real_signature(fake):
    transport = FailoverTransport([GEMINI], inner=httpx.MockTransport(fake.handler))
    client = AsyncOpenAI(base_url=GEMINI.base_url, api_key="k", max_retries=0,
                         http_client=httpx.AsyncClient(transport=transport))
    await client.chat.completions.create(model="x", messages=_tool_call_history(signature="real-sig"))
    call = json.loads(fake.calls[0].content)["messages"][1]["tool_calls"][0]
    assert call["extra_content"]["google"]["thought_signature"] == "real-sig"


# ── Failover ─────────────────────────────────────────────────────────────────

async def test_rate_limit_moves_to_next_provider(fake, transport):
    fake.queue(GROQ, 429)
    result = await _chat(transport)
    assert fake.called() == ["groq", "gemini"]
    assert result.choices[0].message.content == f"from {HOSTS['gemini']}"


async def test_skips_two_limited_providers(fake, transport):
    fake.queue(GROQ, 429)
    fake.queue(GEMINI, 429)
    result = await _chat(transport)
    assert fake.called() == ["groq", "gemini", "cerebras"]
    assert result.model == "gpt-oss-120b"


@pytest.mark.parametrize("status", [408, 413, 500, 502, 503, 504])
async def test_server_errors_and_too_large_move_to_next(fake, transport, status):
    fake.queue(GROQ, status)
    await _chat(transport)
    assert fake.called() == ["groq", "gemini"]


@pytest.mark.parametrize("error", [
    httpx.ConnectError("connection refused"),
    httpx.ReadTimeout("timed out"),
])
async def test_network_errors_move_to_next(fake, transport, clock, error):
    fake.queue(GROQ, error)
    await _chat(transport)
    assert fake.called() == ["groq", "gemini"]
    assert transport.cooldown_until["groq"] == clock.now + ERROR_COOLDOWN


# ── No failover: errors another provider can't fix ──────────────────────────

@pytest.mark.parametrize("status, error", [
    (400, openai.BadRequestError),
    (401, openai.AuthenticationError),
    (404, openai.NotFoundError),
])
async def test_client_errors_are_not_retried_elsewhere(fake, transport, status, error):
    fake.queue(GROQ, status)
    with pytest.raises(error):
        await _chat(transport)
    assert fake.called() == ["groq"]
    assert "groq" not in transport.cooldown_until


# ── Cooldown ─────────────────────────────────────────────────────────────────

async def test_limited_provider_skipped_until_retry_after(fake, transport, clock):
    fake.queue(GROQ, (429, {"retry-after": "20"}))
    await _chat(transport)                      # groq 429 -> gemini
    assert fake.called() == ["groq", "gemini"]

    clock.now += 19
    await _chat(transport)                      # groq still cooling: straight to gemini
    assert fake.called()[2:] == ["gemini"]

    clock.now += 2
    await _chat(transport)                      # cooldown over: groq again
    assert fake.called()[3:] == ["groq"]


async def test_default_cooldown_without_retry_after(fake, transport, clock):
    fake.queue(GROQ, 429)
    await _chat(transport)
    assert transport.cooldown_until["groq"] == clock.now + DEFAULT_COOLDOWN


async def test_retry_after_http_date(fake, transport, clock):
    fake.queue(GROQ, (429, {"retry-after": formatdate(clock.now + 45, usegmt=True)}))
    await _chat(transport)
    assert transport.cooldown_until["groq"] == pytest.approx(clock.now + 45, abs=1)


async def test_long_retry_after_is_capped(fake, transport, clock):
    # e.g. a daily quota: re-check after MAX_COOLDOWN instead of waiting a day
    fake.queue(GROQ, (429, {"retry-after": "86400"}))
    await _chat(transport)
    assert transport.cooldown_until["groq"] == clock.now + MAX_COOLDOWN


async def test_cooldowns_are_per_provider(fake, transport, clock):
    fake.queue(GROQ, (429, {"retry-after": "60"}))
    fake.queue(GEMINI, (429, {"retry-after": "10"}))
    await _chat(transport)                      # groq, gemini limited -> cerebras
    clock.now += 11
    await _chat(transport)                      # gemini back, groq still cooling
    assert fake.called()[3:] == ["gemini"]


# ── Out of credit ────────────────────────────────────────────────────────────

async def test_no_balance_402_moves_on_and_pauses_long(fake, transport, clock):
    # DeepSeek with no balance answers 402 "Insufficient Balance"
    fake.queue(GROQ, (402, {}, "Insufficient Balance"))
    await _chat(transport)
    assert fake.called() == ["groq", "gemini"]
    assert transport.cooldown_until["groq"] == clock.now + MAX_COOLDOWN


async def test_insufficient_quota_429_pauses_long(fake, transport, clock):
    # OpenAI with no credit answers 429 insufficient_quota, without Retry-After
    fake.queue(GROQ, (429, {}, "You exceeded your current quota. insufficient_quota"))
    await _chat(transport)
    assert fake.called() == ["groq", "gemini"]
    assert transport.cooldown_until["groq"] == clock.now + MAX_COOLDOWN


async def test_ordinary_rate_limit_keeps_short_cooldown(fake, transport, clock):
    fake.queue(GROQ, (429, {"retry-after": "7"}, "Rate limit reached for tokens per minute"))
    await _chat(transport)
    assert transport.cooldown_until["groq"] == clock.now + 7


@pytest.mark.parametrize("message", [
    # Real per-minute 429 texts: both mention billing only as an upgrade hint
    "Rate limit reached for model `openai/gpt-oss-120b` on tokens per minute (TPM): Limit 8000, "
    "Used 6500, Requested 2600. Please try again in 8.25s. Need more tokens? Upgrade to Dev Tier "
    "today at https://console.groq.com/settings/billing",
    "You exceeded your current quota, please check your plan and billing details.",
])
async def test_per_minute_limits_mentioning_billing_keep_short_cooldown(fake, transport, clock, message):
    fake.queue(GROQ, (429, {}, message))
    await _chat(transport)
    assert transport.cooldown_until["groq"] == clock.now + DEFAULT_COOLDOWN


# ── Everything limited ───────────────────────────────────────────────────────

async def test_all_limited_raises_rate_limit_error(fake, transport):
    for p in PROVIDERS:
        fake.queue(p, 429)
    with pytest.raises(openai.RateLimitError):
        await _chat(transport)
    assert fake.called() == ["groq", "gemini", "cerebras"]


async def test_all_down_raises_server_error(fake, transport):
    for p in PROVIDERS:
        fake.queue(p, 503)
    with pytest.raises(openai.InternalServerError):
        await _chat(transport)


async def test_all_unreachable_raises_connection_error(fake, transport):
    for p in PROVIDERS:
        fake.queue(p, httpx.ConnectError("refused"))
    with pytest.raises(openai.APIConnectionError):
        await _chat(transport)


async def test_all_cooling_down_answers_429_without_calling_anyone(fake, transport, clock):
    fake.queue(GROQ, (429, {"retry-after": "30"}))
    fake.queue(GEMINI, (429, {"retry-after": "12"}))
    fake.queue(CEREBRAS, (429, {"retry-after": "50"}))
    with pytest.raises(openai.RateLimitError):
        await _chat(transport)
    calls_before = len(fake.calls)

    with pytest.raises(openai.RateLimitError) as exc:
        await _chat(transport)
    assert len(fake.calls) == calls_before                  # nobody was called
    assert exc.value.response.headers["retry-after"] == "12"  # soonest provider


async def test_single_provider_setup_behaves_like_before(fake, clock):
    gateway = Provider("omniroute", "http://localhost:20128/v1", "omni-key", "retail-agents")
    transport = FailoverTransport([gateway], inner=httpx.MockTransport(fake.handler), clock=clock)
    client = AsyncOpenAI(base_url=gateway.base_url, api_key=gateway.api_key, max_retries=0,
                         http_client=httpx.AsyncClient(transport=transport))
    await client.chat.completions.create(model="x", messages=[{"role": "user", "content": "hi"}])
    req = fake.calls[0]
    assert str(req.url) == "http://localhost:20128/v1/chat/completions"
    assert json.loads(req.content)["model"] == "retail-agents"
    assert req.headers["authorization"] == "Bearer omni-key"


# ── Configuration ────────────────────────────────────────────────────────────

def test_load_numbered_providers_in_order():
    env = {
        "AI_PROVIDER_1_URL": "https://api.groq.com/openai/v1/", "AI_PROVIDER_1_KEY": "k1",
        "AI_PROVIDER_1_MODEL": "openai/gpt-oss-120b",
        "AI_PROVIDER_2_URL": "https://api.cerebras.ai/v1", "AI_PROVIDER_2_KEY": "k2",
        "AI_PROVIDER_2_MODEL": "gpt-oss-120b", "AI_PROVIDER_2_NAME": "cerebras",
        "AI_BASE_URL": "http://ignored:20128/v1",
    }
    providers = load_providers(env)
    assert [p.name for p in providers] == ["api.groq.com", "cerebras"]
    assert providers[0].base_url == "https://api.groq.com/openai/v1"   # trailing slash removed
    assert providers[1].model == "gpt-oss-120b"


def test_numbering_stops_at_first_gap():
    env = {
        "AI_PROVIDER_1_URL": "https://a/v1", "AI_PROVIDER_1_KEY": "k", "AI_PROVIDER_1_MODEL": "m",
        "AI_PROVIDER_3_URL": "https://c/v1", "AI_PROVIDER_3_KEY": "k", "AI_PROVIDER_3_MODEL": "m",
    }
    assert len(load_providers(env)) == 1


def test_missing_key_or_model_is_an_error():
    with pytest.raises(ValueError, match="AI_PROVIDER_1_KEY"):
        load_providers({"AI_PROVIDER_1_URL": "https://a/v1", "AI_PROVIDER_1_MODEL": "m"})


def test_falls_back_to_single_gateway_settings():
    providers = load_providers({
        "AI_BASE_URL": "http://localhost:20128/v1", "AI_API_KEY": "omni", "AI_MODEL": "retail-agents",
    })
    assert providers == [Provider("localhost", "http://localhost:20128/v1", "omni", "retail-agents")]


def test_no_settings_at_all_still_starts():
    [provider] = load_providers({})
    assert provider.api_key == "missing-key"
