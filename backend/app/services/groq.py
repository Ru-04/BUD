import httpx
from pydantic import BaseModel

from app.config import groq_config
from app.schemas import Analysis


class ProviderError(Exception):
    def __init__(self, code: str, message: str, status: int = 502):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


class GroqProvider:
    def __init__(self, transport=None):
        self.transport = transport

    async def complete(self, messages: list[dict], *, json_mode=False, schema: type[BaseModel] = Analysis) -> str:
        key, model = groq_config()
        if not key or not model or model.startswith("SELECT_"):
            raise ProviderError("NOT_CONFIGURED", "Set the backend Groq key and chat model before chatting.", 503)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0 if json_mode else 0.5,
            # Trimmed from 1024/1600: GPT-OSS reasoning tokens also count against this budget, so this
            # still leaves headroom over observed real usage while easing pressure on small TPM tiers.
            "max_completion_tokens": 768 if json_mode else 1000,
        }
        if model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
            payload["reasoning_effort"] = "low"
        if json_mode:
            payload["response_format"] = (
                {"type": "json_schema", "json_schema": {
                    "name": schema.__name__.lower(), "strict": True, "schema": schema.model_json_schema(),
                }} if model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
                else {"type": "json_object"}
            )
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5), transport=self.transport) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"}, json=payload,
                )
        except httpx.TimeoutException:
            raise ProviderError("PROVIDER_TIMEOUT", "BUD's provider took too long. Please try again.", 504) from None
        except httpx.RequestError:
            raise ProviderError("PROVIDER_UNAVAILABLE", "BUD could not reach its provider. Please try again.", 502) from None
        if response.status_code == 429:
            raise ProviderError("PROVIDER_RATE_LIMIT", "The provider is busy or its quota is reached. Try again later.", 429)
        if response.status_code in (401, 403):
            raise ProviderError("PROVIDER_AUTH", "The backend Groq credentials need checking.", 503)
        if json_mode and response.status_code == 400:
            try:
                code = response.json().get("error", {}).get("code")
            except (ValueError, AttributeError):
                code = None
            if code == "json_validate_failed":
                raise ProviderError("ANALYZER_INVALID", "The analyzer could not produce valid JSON.")
        if response.status_code >= 400:
            # Never expose the provider response: it may echo request content or configuration.
            raise ProviderError("PROVIDER_ERROR", "The provider rejected the request. Check the backend model configuration.")
        try:
            choice = response.json()["choices"][0]
            content = choice["message"]["content"]
            if json_mode and choice.get("finish_reason") == "length":
                raise ProviderError("ANALYZER_INVALID", "The analyzer returned incomplete JSON.")
            if choice.get("finish_reason") != "stop" or not isinstance(content, str) or not content.strip() or len(content) > 4000:
                raise ValueError()
            return content.strip()
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderError("PROVIDER_INVALID_RESPONSE", "The provider returned an incomplete response. Please try again.") from None


def get_provider():
    return GroqProvider()
