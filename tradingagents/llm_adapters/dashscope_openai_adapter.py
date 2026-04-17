import os
import logging
from typing import Any, Dict, List, Optional, Union, Sequence
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from pydantic import Field, SecretStr

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


class ChatDashScopeOpenAI(ChatOpenAI):
    def __init__(self, **kwargs):
        logger.info("[DashScope] Initializing ChatDashScopeOpenAI")

        api_key_from_kwargs = kwargs.get("api_key")

        if not api_key_from_kwargs:
            env_api_key = os.getenv("DASHSCOPE_API_KEY")
            logger.info(
                f"[DashScope] Reading DASHSCOPE_API_KEY from env: {'found' if env_api_key else 'empty'}"
            )

            if env_api_key and _is_valid_api_key(env_api_key):
                logger.info(f"[DashScope] API Key valid, length: {len(env_api_key)}")
                api_key_from_kwargs = env_api_key
            elif env_api_key:
                logger.warning(
                    "[DashScope] API Key in env is invalid (placeholder?), ignoring"
                )
                api_key_from_kwargs = None
            else:
                logger.warning("[DashScope] DASHSCOPE_API_KEY is empty")
                api_key_from_kwargs = None
        else:
            logger.info("[DashScope] Using API Key from kwargs")

        kwargs.setdefault(
            "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        kwargs["api_key"] = api_key_from_kwargs
        kwargs.setdefault("model", "qwen-turbo")
        kwargs.setdefault("temperature", 0.1)
        kwargs.setdefault("max_tokens", 2000)

        final_api_key = kwargs.get("api_key")
        final_base_url = kwargs.get("base_url")
        logger.info(
            f"[DashScope] API Key: {'present' if final_api_key else 'missing'}, base_url: {final_base_url}"
        )

        if not final_api_key:
            raise ValueError(
                "DashScope API key not found. "
                "Set DASHSCOPE_API_KEY environment variable."
            )

        super().__init__(**kwargs)

        logger.info(
            f"DashScope adapter initialized: model={kwargs.get('model', 'qwen-turbo')}"
        )

        api_base = (
            getattr(self, "base_url", None)
            or getattr(self, "openai_api_base", None)
            or kwargs.get("base_url", "unknown")
        )
        logger.info(f"[DashScope] API Base: {api_base}")

    def _generate(self, *args, **kwargs):
        result = super()._generate(*args, **kwargs)

        try:
            if hasattr(result, "llm_output") and result.llm_output:
                token_usage = result.llm_output.get("token_usage", {})

                input_tokens = token_usage.get("prompt_tokens", 0)
                output_tokens = token_usage.get("completion_tokens", 0)

                if input_tokens > 0 or output_tokens > 0:
                    logger.info(
                        f"Token usage - Provider: dashscope, Model: {self.model_name}, "
                        f"input: {input_tokens}, output: {output_tokens}"
                    )
        except Exception as track_error:
            logger.error(f"Token tracking failed: {track_error}")

        return result


DASHSCOPE_OPENAI_MODELS = {
    "qwen-turbo": {
        "description": "Qwen Turbo - fast response, suitable for daily conversation",
        "context_length": 8192,
        "supports_function_calling": True,
        "recommended_for": ["fast tasks", "daily conversation", "simple analysis"],
    },
    "qwen-plus": {
        "description": "Qwen Plus - balanced performance and cost",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": ["complex analysis", "professional tasks", "deep thinking"],
    },
    "qwen-plus-latest": {
        "description": "Qwen Plus Latest - latest features and performance",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": [
            "latest features",
            "complex analysis",
            "professional tasks",
        ],
    },
    "qwen-max": {
        "description": "Qwen Max - strongest performance for complex tasks",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": [
            "complex reasoning",
            "professional analysis",
            "high quality output",
        ],
    },
    "qwen-max-latest": {
        "description": "Qwen Max Latest - strongest performance and latest features",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": [
            "latest features",
            "complex reasoning",
            "professional analysis",
        ],
    },
    "qwen-long": {
        "description": "Qwen Long - ultra long context for long document processing",
        "context_length": 1000000,
        "supports_function_calling": True,
        "recommended_for": [
            "long document analysis",
            "large data processing",
            "complex context",
        ],
    },
}


def get_available_openai_models() -> Dict[str, Dict[str, Any]]:
    return DASHSCOPE_OPENAI_MODELS


def create_dashscope_openai_llm(
    model: str = "qwen-plus-latest",
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    **kwargs,
) -> ChatDashScopeOpenAI:
    return ChatDashScopeOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def test_dashscope_openai_connection(
    model: str = "qwen-turbo", api_key: Optional[str] = None
) -> bool:
    try:
        logger.info(f"Testing DashScope connection, model: {model}")

        llm = create_dashscope_openai_llm(model=model, api_key=api_key, max_tokens=50)

        response = llm.invoke("Hello, please introduce yourself briefly.")

        if response and hasattr(response, "content") and response.content:
            logger.info("DashScope connection successful")
            return True
        else:
            logger.error("DashScope connection returned empty response")
            return False

    except Exception as e:
        logger.error(f"DashScope connection test failed: {e}")
        return False


def test_dashscope_openai_function_calling(
    model: str = "qwen-plus-latest", api_key: Optional[str] = None
) -> bool:
    try:
        logger.info(f"Testing DashScope Function Calling, model: {model}")

        llm = create_dashscope_openai_llm(model=model, api_key=api_key, max_tokens=200)

        from langchain_core.tools import tool

        @tool
        def test_tool(query: str) -> str:
            return f"Query result: {query}"

        llm_with_tools = llm.bind_tools([test_tool])

        response = llm_with_tools.invoke("Please use test_tool to query 'hello world'")

        logger.info("DashScope Function Calling test completed")

        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Tool calls: {len(response.tool_calls)}")
            return True
        else:
            logger.info(
                f"Response content: {getattr(response, 'content', 'No content')}"
            )
            return True

    except Exception as e:
        logger.error(f"DashScope Function Calling test failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("DashScope OpenAI Compatible Adapter Test")
    logger.info("=" * 50)

    connection_ok = test_dashscope_openai_connection()

    if connection_ok:
        function_calling_ok = test_dashscope_openai_function_calling()
        if function_calling_ok:
            logger.info("All tests passed!")
        else:
            logger.error("Function Calling test failed")
    else:
        logger.error("Connection test failed")
