"""
LLM abstraction layer — provider-agnostic interface.
Swap Gemini for OpenAI or Anthropic without changing agent code.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import logger


@dataclass
class LLMResponse:
    content: str
    tokens_in: int
    tokens_out: int
    model: str
    raw: Any = None


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str | None = None, **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def chat(self, messages: list[dict], system: str | None = None, **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        pass


# ── Gemini Provider ───────────────────────────────────────────────────────────

class GeminiProvider(LLMProvider):
    def __init__(self, model: str | None = None, fast_model: str | None = None):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name = model or settings.GEMINI_MODEL
        self.fast_model_name = fast_model or settings.GEMINI_FAST_MODEL

    async def complete(self, prompt: str, system: str | None = None, **kwargs) -> LLMResponse:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system,
        )
        response = await model.generate_content_async(prompt)
        return LLMResponse(
            content=response.text,
            tokens_in=response.usage_metadata.prompt_token_count,
            tokens_out=response.usage_metadata.candidates_token_count,
            model=self.model_name,
            raw=response,
        )

    async def chat(self, messages: list[dict], system: str | None = None, **kwargs) -> LLMResponse:
        """
        messages: [{"role": "user"/"model", "parts": ["..."]}]
        """
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system,
        )
        history = messages[:-1]
        last = messages[-1]["parts"][0] if messages else ""
        chat = model.start_chat(history=history)
        response = await chat.send_message_async(last)
        return LLMResponse(
            content=response.text,
            tokens_in=response.usage_metadata.prompt_token_count,
            tokens_out=response.usage_metadata.candidates_token_count,
            model=self.model_name,
            raw=response,
        )

    async def embed(self, text: str) -> list[float]:
        result = genai.embed_content(
            model=settings.EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]


# ── Router ─────────────────────────────────────────────────────────────────────

class LLMRouter:
    """Routes LLM calls to the correct provider. Extendable."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._default: str = "gemini"

    def register(self, name: str, provider: LLMProvider):
        self._providers[name] = provider
        logger.info(f"🤖 LLM provider registered: {name}")

    def get(self, name: str | None = None) -> LLMProvider:
        name = name or self._default
        if name not in self._providers:
            raise ValueError(f"LLM provider '{name}' not registered")
        return self._providers[name]

    async def complete(self, prompt: str, provider: str | None = None, **kwargs) -> LLMResponse:
        return await self.get(provider).complete(prompt, **kwargs)

    async def embed(self, text: str, provider: str | None = None) -> list[float]:
        return await self.get(provider).embed(text)


# ── Singleton ─────────────────────────────────────────────────────────────────

llm_router = LLMRouter()
llm_router.register("gemini", GeminiProvider())
