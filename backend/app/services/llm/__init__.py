"""
LLM Service 模組
提供 get_llm_service() factory 函式，根據設定回傳對應的 LLM 服務
"""
from typing import Optional

from app.core.config import settings
from app.services.llm.base import BaseLLMService

_llm_instances: dict[str, BaseLLMService] = {}


def get_llm_service(provider: Optional[str] = None) -> BaseLLMService:
    """
    Factory 函式：根據 provider 回傳對應的 LLM 服務 singleton
    若未指定 provider，使用 settings.LLM_PROVIDER
    """
    provider = (provider or settings.LLM_PROVIDER).lower()

    if provider in _llm_instances:
        return _llm_instances[provider]

    if provider == "gemini":
        from app.services.llm.gemini_service import GeminiService
        _llm_instances[provider] = GeminiService()
    elif provider == "ollama":
        from app.services.llm.ollama_service import OllamaService
        _llm_instances[provider] = OllamaService()
    else:
        raise ValueError(f"不支援的 LLM provider: {provider}，請使用 'gemini' 或 'ollama'")

    return _llm_instances[provider]
