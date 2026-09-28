"""Failover across OpenAI-compatible AI providers, inside the backend.

Every request the Agents SDK makes goes through FailoverTransport. It sends the
request to the first provider that isn't cooling down; if that provider is rate
limited or down, the same request goes to the next one. Chat requests are
stateless (they carry the whole conversation), so any provider can take over,
even in the middle of an agent run.

Configure providers in priority order:
    AI_PROVIDER_1_URL=https://api.groq.com/openai/v1
    AI_PROVIDER_1_KEY=gsk_...
    AI_PROVIDER_1_MODEL=openai/gpt-oss-120b
    AI_PROVIDER_2_URL=...        (and so on)
Without them, AI_BASE_URL / AI_API_KEY / AI_MODEL is used as a single provider
(e.g. an OmniRoute gateway, which does its own failover).
"""
import json
import logging
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Callable, Mapping, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Rate limited (429), request over the per-minute token limit (Groq sends 413),
# or the provider is down: another provider can serve the same request.
FAILOVER_STATUSES = {408, 413, 429, 500, 502, 503, 504}
# Out of credit or quota (DeepSeek sends 402; OpenAI sends 429 with
# insufficient_quota): won't recover within minutes, so pause it for MAX_COOLDOWN.
OUT_OF_CREDIT_STATUS = 402
# Match exact codes only: ordinary per-minute 429s from Groq and Gemini also
# mention "billing" (as an upgrade hint), and must keep their short cooldown.
OUT_OF_CREDIT_CODES = ("insufficient_quota",)
# Anything else (400 bad request, 401 bad key, 404 unknown model) is returned
# as-is: another provider would reject it too, or it's a config error to fix.

DEFAULT_COOLDOWN = 30.0   # seconds, when a provider doesn't send Retry-After
MAX_COOLDOWN = 600.0      # re-check even a long (e.g. daily) limit every 10 minutes
ERROR_COOLDOWN = 30.0     # after a timeout or connection error

# Parameters the Agents SDK may send that most non-OpenAI providers reject.
_UNSUPPORTED_PARAMS = ("verbosity", "reasoning_effort")


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str


def load_providers(env: Mapping[str, str]) -> list[Provider]:
    providers = []
    n = 1
    while env.get(f"AI_PROVIDER_{n}_URL"):
        prefix = f"AI_PROVIDER_{n}_"
        url = env[prefix + "URL"].rstrip("/")
        missing = [k for k in ("KEY", "MODEL") if not env.get(prefix + k)]
        if missing:
            raise ValueError(f"{prefix}URL is set but {', '.join(prefix + k for k in missing)} is missing")
        providers.append(Provider(
            name=env.get(prefix + "NAME") or urlparse(url).hostname or f"provider-{n}",
            base_url=url,
            api_key=env[prefix + "KEY"],
            model=env[prefix + "MODEL"],
        ))
        n += 1
    if providers:
        return providers

    url = env.get("AI_BASE_URL", "http://localhost:20128/v1").rstrip("/")
    return [Provider(
        name=urlparse(url).hostname or "ai-gateway",
        base_url=url,
        api_key=env.get("AI_API_KEY") or "missing-key",
        model=env.get("AI_MODEL", "auto"),
    )]


def _retry_after_seconds(response: httpx.Response, now: float) -> float:
    value = response.headers.get("retry-after")
    if not value:
        return DEFAULT_COOLDOWN
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = parsedate_to_datetime(value).timestamp() - now
        except (TypeError, ValueError):
            return DEFAULT_COOLDOWN
    return min(max(seconds, 1.0), MAX_COOLDOWN)


def _is_out_of_credit(response: httpx.Response) -> bool:
    if response.status_code == OUT_OF_CREDIT_STATUS:
        return True
    body = response.text.lower()
    return response.status_code == 429 and any(code in body for code in OUT_OF_CREDIT_CODES)


# Gemini's thinking models require the "thought signature" they attached to
# each tool call to be sent back. The Agents SDK drops it, and tool calls made
# by another provider never had one, so Gemini would reject the request (400).
# Google documents this placeholder for exactly that case.
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_PLACEHOLDER_SIGNATURE = "skip_thought_signature_validator"


def _add_gemini_signatures(body: dict) -> None:
    for message in body.get("messages") or []:
        for call in message.get("tool_calls") or []:
            google = call.setdefault("extra_content", {}).setdefault("google", {})
            google.setdefault("thought_signature", GEMINI_PLACEHOLDER_SIGNATURE)


def _prepare_chat_body(content: bytes, provider: "Provider") -> bytes:
    body = json.loads(content)
    body["model"] = provider.model
    if urlparse(provider.base_url).hostname == GEMINI_HOST:
        _add_gemini_signatures(body)
    for param in _UNSUPPORTED_PARAMS:
        body.pop(param, None)
    # Handoff tools have no arguments and are sent as
    # {"properties": {}, "required": []}. The empty properties object gets
    # dropped on the way upstream, and Groq then rejects the schema for having
    # "required" without "properties". An empty "required" means nothing, so drop it.
    for tool in body.get("tools") or []:
        params = (tool.get("function") or {}).get("parameters") or {}
        if params.get("required") == []:
            params.pop("required")
    return json.dumps(body).encode()


class FailoverTransport(httpx.AsyncBaseTransport):
    """Sends each request to the first available provider, moving on when one
    is rate limited or down, and skipping it until its cooldown ends."""

    def __init__(
        self,
        providers: list[Provider],
        inner: Optional[httpx.AsyncBaseTransport] = None,
        clock: Callable[[], float] = time.time,
    ):
        if not providers:
            raise ValueError("At least one AI provider is required")
        self.providers = providers
        self._inner = inner or httpx.AsyncHTTPTransport()
        self._clock = clock
        # The OpenAI client is created with the first provider's base URL;
        # the path after it (e.g. "/chat/completions") is kept per provider.
        self._client_base_path = urlparse(providers[0].base_url).path.rstrip("/")
        self.cooldown_until: dict[str, float] = {}

    def _build_request(self, request: httpx.Request, provider: Provider) -> httpx.Request:
        path = request.url.path
        if path.startswith(self._client_base_path):
            path = path[len(self._client_base_path):]
        url = httpx.URL(provider.base_url + path, params=request.url.params)

        content = request.content
        if request.method == "POST" and path.endswith("/chat/completions"):
            content = _prepare_chat_body(content, provider)

        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "authorization", "content-length")
        }
        headers["authorization"] = f"Bearer {provider.api_key}"
        return httpx.Request(request.method, url, headers=headers, content=content)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await request.aread()
        last_response: Optional[httpx.Response] = None
        last_error: Optional[Exception] = None

        for provider in self.providers:
            now = self._clock()
            if self.cooldown_until.get(provider.name, 0) > now:
                continue

            try:
                response = await self._inner.handle_async_request(self._build_request(request, provider))
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                logger.warning("AI provider %s unreachable (%s); trying next", provider.name, exc)
                self.cooldown_until[provider.name] = now + ERROR_COOLDOWN
                last_error = exc
                continue

            if response.status_code not in FAILOVER_STATUSES | {OUT_OF_CREDIT_STATUS}:
                return response

            await response.aread()  # keep the body so it can be returned if every provider fails
            if _is_out_of_credit(response):
                wait = MAX_COOLDOWN
            else:
                wait = _retry_after_seconds(response, now)
            self.cooldown_until[provider.name] = now + wait
            logger.warning(
                "AI provider %s returned %s; cooling down %.0fs and trying next",
                provider.name, response.status_code, wait,
            )
            if last_response is not None:
                await last_response.aclose()
            last_response = response

        if last_response is not None:
            return last_response
        if last_error is not None:
            raise last_error

        # Every provider is cooling down: report a rate limit, with how long
        # until the first one is available again.
        wait = min(self.cooldown_until.values()) - self._clock()
        logger.warning("All AI providers are cooling down; next available in %.0fs", wait)
        return httpx.Response(
            429,
            headers={"retry-after": str(max(1, round(wait)))},
            json={"error": {"message": "All AI providers are rate limited. Try again shortly.",
                            "type": "rate_limit_error", "code": "all_providers_busy"}},
            request=request,
        )

    async def aclose(self):
        await self._inner.aclose()
