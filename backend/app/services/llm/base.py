"""
LLM Service 抽象基類
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLMService(ABC):
    """LLM 服務抽象基類"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """回傳 provider 名稱，例如 'gemini' 或 'ollama'"""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        呼叫 LLM 產生回答

        Args:
            prompt: 使用者 prompt（含 context）
            system_prompt: 系統提示詞
            temperature: 生成溫度
            max_tokens: 最大 token 數

        Returns:
            LLM 生成的文字
        """
        ...

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        串流呼叫 LLM，逐步 yield 文字 chunk

        Args:
            prompt: 使用者 prompt（含 context）
            system_prompt: 系統提示詞
            temperature: 生成溫度
            max_tokens: 最大 token 數

        Yields:
            LLM 生成的文字片段
        """
        ...
        # 使 mypy / IDE 辨識為 async generator
        yield  # type: ignore  # pragma: no cover

    @abstractmethod
    async def health_check(self) -> bool:
        """檢查 LLM 服務是否可用"""
        ...
