import os
import time
import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)


def _is_valid_api_key(key):
    if not key or len(key) <= 10:
        return False
    if key.startswith("your_") or key.startswith("your-"):
        return False
    if key.endswith("_here") or key.endswith("-here"):
        return False
    if "..." in key:
        return False
    return True


class OpenAICompatibleBase(ChatOpenAI):
    def __init__(
        self,
        provider_name: str,
        model: str,
        api_key_env_var: str,
        base_url: str,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        object.__setattr__(self, "_provider_name", provider_name)
        object.__setattr__(self, "_model_name_alias", model)

        if api_key is None:
            env_api_key = os.getenv(api_key_env_var)
            logger.info(
                f"[{provider_name}] Reading {api_key_env_var}: {'found' if env_api_key else 'empty'}"
            )

            if env_api_key and _is_valid_api_key(env_api_key):
                logger.info(
                    f"[{provider_name}] API Key valid, length: {len(env_api_key)}"
                )
                api_key = env_api_key
            elif env_api_key:
                logger.warning(
                    f"[{provider_name}] API Key in env is invalid (placeholder?), ignoring"
                )
                api_key = None
            else:
                logger.warning(f"[{provider_name}] {api_key_env_var} is empty")
                api_key = None

            if not api_key:
                raise ValueError(
                    f"{provider_name} API key not found. "
                    f"Please set {api_key_env_var} environment variable."
                )
        else:
            logger.info(
                f"[{provider_name}] Using provided API Key, length: {len(api_key)}"
            )

        openai_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        try:
            openai_kwargs.update({"api_key": api_key, "base_url": base_url})
        except Exception:
            openai_kwargs.update(
                {"openai_api_key": api_key, "openai_api_base": base_url}
            )

        super().__init__(**openai_kwargs)

        object.__setattr__(self, "_provider_name", provider_name)
        object.__setattr__(self, "_model_name_alias", model)

        logger.info(
            f"{provider_name} adapter initialized: model={model}, base_url={base_url}"
        )

    @property
    def provider_name(self) -> Optional[str]:
        return getattr(self, "_provider_name", None)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        start_time = time.time()
        result = super()._generate(messages, stop, run_manager, **kwargs)
        self._track_token_usage(result, kwargs, start_time)
        return result

    def _track_token_usage(self, result: ChatResult, kwargs: Dict, start_time: float):
        try:
            usage = getattr(result, "usage_metadata", None)
            total_tokens = usage.get("total_tokens") if usage else None
            prompt_tokens = usage.get("input_tokens") if usage else None
            completion_tokens = usage.get("output_tokens") if usage else None

            elapsed = time.time() - start_time
            logger.info(
                f"Token usage - Provider: {getattr(self, 'provider_name', 'unknown')}, "
                f"Model: {getattr(self, 'model_name', 'unknown')}, "
                f"total: {total_tokens}, prompt: {prompt_tokens}, "
                f"completion: {completion_tokens}, elapsed: {elapsed:.2f}s"
            )
        except Exception as e:
            logger.warning(f"Token tracking failed: {e}")


class ChatDeepSeekOpenAI(OpenAICompatibleBase):
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            provider_name="deepseek",
            model=model,
            api_key_env_var="DEEPSEEK_API_KEY",
            base_url="https://api.deepseek.com",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class ChatDashScopeOpenAIUnified(OpenAICompatibleBase):
    def __init__(
        self,
        model: str = "qwen-turbo",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            provider_name="dashscope",
            model=model,
            api_key_env_var="DASHSCOPE_API_KEY",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class ChatQianfanOpenAI(OpenAICompatibleBase):
    def __init__(
        self,
        model: str = "ernie-3.5-8k",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        if not api_key:
            env_api_key = os.getenv("QIANFAN_API_KEY")
            if env_api_key and _is_valid_api_key(env_api_key):
                qianfan_api_key = env_api_key
            else:
                qianfan_api_key = None
        else:
            qianfan_api_key = api_key

        if not qianfan_api_key:
            raise ValueError(
                "Qianfan API key required. "
                "Set QIANFAN_API_KEY environment variable. "
                "Format: bce-v3/ALTAK-xxx/xxx"
            )

        if not qianfan_api_key.startswith("bce-v3/"):
            raise ValueError(
                "QIANFAN_API_KEY format error, expected: bce-v3/ALTAK-xxx/xxx"
            )

        super().__init__(
            provider_name="qianfan",
            model=model,
            api_key_env_var="QIANFAN_API_KEY",
            base_url="https://qianfan.baidubce.com/v2",
            api_key=qianfan_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)

    def _truncate_messages(
        self, messages: List[BaseMessage], max_tokens: int = 4500
    ) -> List[BaseMessage]:
        truncated_messages = []
        total_tokens = 0

        for message in reversed(messages):
            content = (
                str(message.content) if hasattr(message, "content") else str(message)
            )
            message_tokens = self._estimate_tokens(content)

            if total_tokens + message_tokens <= max_tokens:
                truncated_messages.insert(0, message)
                total_tokens += message_tokens
            else:
                if not truncated_messages:
                    remaining_tokens = max_tokens - 100
                    max_chars = remaining_tokens * 2
                    truncated_content = content[:max_chars] + "...(truncated)"

                    if hasattr(message, "content"):
                        message.content = truncated_content
                    truncated_messages.insert(0, message)
                break

        if len(truncated_messages) < len(messages):
            logger.warning(
                f"Qianfan input truncated: {len(messages) - len(truncated_messages)} messages dropped"
            )

        return truncated_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        truncated_messages = self._truncate_messages(messages)
        return super()._generate(truncated_messages, stop, run_manager, **kwargs)


class ChatZhipuOpenAI(OpenAICompatibleBase):
    def __init__(
        self,
        model: str = "glm-4.6",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        if base_url is None:
            env_base_url = os.getenv("ZHIPU_BASE_URL")
            if (
                env_base_url
                and not env_base_url.startswith("your_")
                and not env_base_url.startswith("your-")
            ):
                base_url = env_base_url
            else:
                base_url = "https://open.bigmodel.cn/api/paas/v4"

        super().__init__(
            provider_name="zhipu",
            model=model,
            api_key_env_var="ZHIPU_API_KEY",
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)


class ChatCustomOpenAI(OpenAICompatibleBase):
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        if base_url is None:
            env_base_url = os.getenv("CUSTOM_OPENAI_BASE_URL")
            if (
                env_base_url
                and not env_base_url.startswith("your_")
                and not env_base_url.startswith("your-")
            ):
                base_url = env_base_url
            else:
                base_url = "https://api.openai.com/v1"

        super().__init__(
            provider_name="custom_openai",
            model=model,
            api_key_env_var="CUSTOM_OPENAI_API_KEY",
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


OPENAI_COMPATIBLE_PROVIDERS = {
    "deepseek": {
        "adapter_class": ChatDeepSeekOpenAI,
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": {
            "deepseek-chat": {
                "context_length": 32768,
                "supports_function_calling": True,
            },
            "deepseek-coder": {
                "context_length": 16384,
                "supports_function_calling": True,
            },
        },
    },
    "dashscope": {
        "adapter_class": ChatDashScopeOpenAIUnified,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": {
            "qwen-turbo": {"context_length": 8192, "supports_function_calling": True},
            "qwen-plus": {"context_length": 32768, "supports_function_calling": True},
            "qwen-plus-latest": {
                "context_length": 32768,
                "supports_function_calling": True,
            },
            "qwen-max": {"context_length": 32768, "supports_function_calling": True},
            "qwen-max-latest": {
                "context_length": 32768,
                "supports_function_calling": True,
            },
        },
    },
    "qianfan": {
        "adapter_class": ChatQianfanOpenAI,
        "base_url": "https://qianfan.baidubce.com/v2",
        "api_key_env": "QIANFAN_API_KEY",
        "models": {
            "ernie-3.5-8k": {"context_length": 5120, "supports_function_calling": True},
            "ernie-4.0-turbo-8k": {
                "context_length": 5120,
                "supports_function_calling": True,
            },
            "ERNIE-Speed-8K": {
                "context_length": 5120,
                "supports_function_calling": True,
            },
            "ERNIE-Lite-8K": {
                "context_length": 5120,
                "supports_function_calling": True,
            },
        },
    },
    "zhipu": {
        "adapter_class": ChatZhipuOpenAI,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "models": {
            "glm-4.6": {"context_length": 200000, "supports_function_calling": True},
            "glm-4": {"context_length": 128000, "supports_function_calling": True},
            "glm-4-plus": {"context_length": 128000, "supports_function_calling": True},
            "glm-3-turbo": {
                "context_length": 128000,
                "supports_function_calling": True,
            },
        },
    },
    "custom_openai": {
        "adapter_class": ChatCustomOpenAI,
        "base_url": None,
        "api_key_env": "CUSTOM_OPENAI_API_KEY",
        "models": {
            "gpt-3.5-turbo": {
                "context_length": 16384,
                "supports_function_calling": True,
            },
            "gpt-4": {"context_length": 8192, "supports_function_calling": True},
            "gpt-4-turbo": {
                "context_length": 128000,
                "supports_function_calling": True,
            },
            "gpt-4o": {"context_length": 128000, "supports_function_calling": True},
            "gpt-4o-mini": {
                "context_length": 128000,
                "supports_function_calling": True,
            },
            "claude-3-haiku": {
                "context_length": 200000,
                "supports_function_calling": True,
            },
            "claude-3-sonnet": {
                "context_length": 200000,
                "supports_function_calling": True,
            },
            "claude-3-opus": {
                "context_length": 200000,
                "supports_function_calling": True,
            },
            "claude-3.5-sonnet": {
                "context_length": 200000,
                "supports_function_calling": True,
            },
            "gemini-pro": {"context_length": 32768, "supports_function_calling": True},
            "gemini-1.5-pro": {
                "context_length": 1000000,
                "supports_function_calling": True,
            },
            "llama-3.1-8b": {
                "context_length": 128000,
                "supports_function_calling": True,
            },
            "llama-3.1-70b": {
                "context_length": 128000,
                "supports_function_calling": True,
            },
            "llama-3.1-405b": {
                "context_length": 128000,
                "supports_function_calling": True,
            },
            "custom-model": {
                "context_length": 32768,
                "supports_function_calling": True,
            },
        },
    },
}


def create_openai_compatible_llm(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> OpenAICompatibleBase:
    provider_info = OPENAI_COMPATIBLE_PROVIDERS.get(provider)
    if not provider_info:
        raise ValueError(f"Unsupported OpenAI-compatible provider: {provider}")

    adapter_class = provider_info["adapter_class"]

    if base_url is None:
        base_url = provider_info.get("base_url")

    init_kwargs = dict(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    if provider_info.get("base_url") is None and base_url:
        init_kwargs["base_url"] = base_url

    return adapter_class(**init_kwargs)


def test_openai_compatible_adapters():
    for provider, info in OPENAI_COMPATIBLE_PROVIDERS.items():
        cls = info["adapter_class"]
        try:
            if provider == "custom_openai":
                cls(
                    model="gpt-3.5-turbo",
                    api_key="test",
                    base_url="https://api.openai.com/v1",
                )
            elif provider == "qianfan":
                cls(model="ernie-3.5-8k", api_key="bce-v3/test-key/test-secret")
            else:
                cls(model=list(info["models"].keys())[0], api_key="test")
            logger.info(f"Adapter instantiation OK: {provider}")
        except Exception as e:
            logger.warning(f"Adapter instantiation failed (expected): {provider} - {e}")


if __name__ == "__main__":
    test_openai_compatible_adapters()
