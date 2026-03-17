"""
Gemini LLM Service — 使用 google-genai SDK
單次呼叫，失敗直接回傳錯誤讓前端決定是否重試
"""
import logging
from typing import AsyncGenerator

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.llm.base import BaseLLMService

logger = logging.getLogger(__name__)


class GeminiService(BaseLLMService):
    """Google Gemini LLM 服務"""

    _instance: "GeminiService | None" = None
    _client: genai.Client | None = None

    def __new__(cls) -> "GeminiService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY 未設定，請在 .env 中設定")
            self._client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(api_version="v1beta"),
            )
            # 關閉 SDK 內建的 tenacity 自動重試，讓錯誤直接回傳前端
            self._client._api_client._retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
        return self._client

    def _build_prompt(self, prompt: str, system_prompt: str = "") -> str:
        # 部分模型（如 gemma）不支援 system_instruction，統一合併到 prompt
        return f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        client = self._ensure_client()
        logger.info(f"[Gemini] generate() 呼叫, model={settings.GEMINI_MODEL}, "
                    f"prompt 長度={len(prompt)}, system_prompt 長度={len(system_prompt)}")
        full_prompt = self._build_prompt(prompt, system_prompt)
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            logger.info(f"[Gemini] 回應成功, text 長度={len(response.text)}, "
                        f"usage={response.usage_metadata}")
            return response.text
        except Exception as e:
            logger.error(f"[Gemini] API 呼叫失敗: {type(e).__name__}: {e}")
            raise

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        client = self._ensure_client()
        logger.info(f"[Gemini] stream_generate() 呼叫, model={settings.GEMINI_MODEL}")
        full_prompt = self._build_prompt(prompt, system_prompt)
        try:
            response_stream = client.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"[Gemini] stream API 呼叫失敗: {type(e).__name__}: {e}")
            raise

    async def health_check(self) -> bool:
        try:
            self._ensure_client()
            return True
        except Exception:
            return False
