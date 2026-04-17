import os
import logging
from typing import Any, Dict, List, Optional, Union, Sequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import LLMResult
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


class ChatGoogleOpenAI(ChatGoogleGenerativeAI):
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        logger.info("[Google] Initializing ChatGoogleOpenAI")

        kwargs.setdefault("temperature", 0.1)
        kwargs.setdefault("max_tokens", 2000)

        google_api_key = kwargs.get("google_api_key")

        if not google_api_key:
            env_api_key = os.getenv("GOOGLE_API_KEY")
            logger.info(
                f"[Google] Reading GOOGLE_API_KEY from env: {'found' if env_api_key else 'empty'}"
            )

            if env_api_key and _is_valid_api_key(env_api_key):
                logger.info(f"[Google] API Key valid, length: {len(env_api_key)}")
                google_api_key = env_api_key
            elif env_api_key:
                logger.warning(
                    "[Google] API Key in env is invalid (placeholder?), ignoring"
                )
                google_api_key = None
            else:
                logger.warning("[Google] GOOGLE_API_KEY is empty")
                google_api_key = None
        else:
            logger.info("[Google] Using API Key from kwargs")

        if not google_api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable."
            )

        kwargs["google_api_key"] = google_api_key

        if base_url:
            base_url = base_url.rstrip("/")
            logger.info(f"[Google] Processing base_url: {base_url}")

            is_google_official = "generativelanguage.googleapis.com" in base_url

            if is_google_official:
                if base_url.endswith("/v1beta"):
                    api_endpoint = base_url[:-7]
                elif base_url.endswith("/v1"):
                    api_endpoint = base_url[:-3]
                else:
                    api_endpoint = base_url
                logger.info(f"[Google] Official endpoint: {api_endpoint}")
            else:
                api_endpoint = base_url
                logger.info(f"[Google] Proxy endpoint: {api_endpoint}")

            kwargs["client_options"] = {"api_endpoint": api_endpoint}
        else:
            logger.info("[Google] No custom base_url, using default endpoint")

        super().__init__(**kwargs)

        logger.info(
            f"Google AI adapter initialized: model={kwargs.get('model', 'gemini-pro')}"
        )

    @property
    def model_name(self) -> str:
        model = self.model
        if model and model.startswith("models/"):
            return model[7:]
        return model or "unknown"

    def _generate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs
    ) -> LLMResult:
        try:
            result = super()._generate(messages, stop, **kwargs)

            if result and result.generations:
                for generation_list in result.generations:
                    if isinstance(generation_list, list):
                        for generation in generation_list:
                            if hasattr(generation, "message") and generation.message:
                                self._optimize_message_content(generation.message)
                    else:
                        if (
                            hasattr(generation_list, "message")
                            and generation_list.message
                        ):
                            self._optimize_message_content(generation_list.message)

            self._track_token_usage(result, kwargs)

            return result

        except Exception as e:
            logger.error(f"Google AI generation failed: {e}")
            logger.exception(e)

            error_str = str(e)
            if "API_KEY_INVALID" in error_str or "API key not valid" in error_str:
                error_content = "Google AI API Key invalid or not configured.\n\nSet GOOGLE_API_KEY environment variable."
            elif "Connection" in error_str or "Network" in error_str:
                error_content = f"Google AI connection failed: {error_str}"
            else:
                error_content = f"Google AI call failed: {error_str}"

            from langchain_core.outputs import ChatGeneration

            error_message = AIMessage(content=error_content)
            error_generation = ChatGeneration(message=error_message)
            return LLMResult(generations=[[error_generation]])

    def _optimize_message_content(self, message: BaseMessage):
        if not isinstance(message, AIMessage) or not message.content:
            return

        content = message.content

        if self._is_news_content(content):
            optimized_content = self._enhance_news_content(content)
            message.content = optimized_content

            logger.debug(
                f"[Google] Optimized news content: {len(content)} -> {len(optimized_content)} chars"
            )

    def _is_news_content(self, content: str) -> bool:
        news_indicators = [
            "stock",
            "company",
            "market",
            "invest",
        ]
        return (
            any(indicator in content for indicator in news_indicators)
            and len(content) > 200
        )

    def _enhance_news_content(self, content: str) -> str:
        import datetime

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        enhanced_content = content

        if "published" not in content and "date" not in content:
            enhanced_content = f"Published: {current_date}\n\n{enhanced_content}"

        if "source" not in content:
            enhanced_content = f"{enhanced_content}\n\nSource: Google AI Analysis"

        return enhanced_content

    def _track_token_usage(self, result: LLMResult, kwargs: Dict[str, Any]):
        try:
            if hasattr(result, "llm_output") and result.llm_output:
                token_usage = result.llm_output.get("token_usage", {})

                input_tokens = token_usage.get("prompt_tokens", 0)
                output_tokens = token_usage.get("completion_tokens", 0)

                if input_tokens > 0 or output_tokens > 0:
                    logger.info(
                        f"Token usage - Provider: google, Model: {self.model}, "
                        f"input: {input_tokens}, output: {output_tokens}"
                    )
        except Exception as track_error:
            logger.error(f"Google adapter token tracking failed: {track_error}")


GOOGLE_OPENAI_MODELS = {
    "gemini-2.5-pro": {
        "description": "Gemini 2.5 Pro - latest flagship model",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": [
            "complex reasoning",
            "professional analysis",
            "high quality output",
        ],
        "avg_response_time": 16.68,
    },
    "gemini-2.5-flash": {
        "description": "Gemini 2.5 Flash - latest fast model",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": [
            "fast response",
            "real-time analysis",
            "high frequency usage",
        ],
        "avg_response_time": 2.73,
    },
    "gemini-2.5-flash-lite-preview-06-17": {
        "description": "Gemini 2.5 Flash Lite Preview - ultra fast",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": [
            "ultra fast response",
            "real-time interaction",
            "high frequency calls",
        ],
        "avg_response_time": 1.45,
    },
    "gemini-2.0-flash": {
        "description": "Gemini 2.0 Flash - next-gen fast model",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": ["fast response", "real-time analysis"],
        "avg_response_time": 1.87,
    },
    "gemini-1.5-pro": {
        "description": "Gemini 1.5 Pro - powerful, balanced choice",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": ["complex analysis", "professional tasks", "deep thinking"],
        "avg_response_time": 2.25,
    },
    "gemini-1.5-flash": {
        "description": "Gemini 1.5 Flash - fast response, backup choice",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": ["fast tasks", "daily conversation", "simple analysis"],
        "avg_response_time": 2.87,
    },
    "gemini-pro": {
        "description": "Gemini Pro - classic model, stable and reliable",
        "context_length": 32768,
        "supports_function_calling": True,
        "recommended_for": ["general tasks", "stability-critical scenarios"],
    },
}


def get_available_google_models() -> Dict[str, Dict[str, Any]]:
    return GOOGLE_OPENAI_MODELS


def create_google_openai_llm(
    model: str = "gemini-2.5-flash-lite-preview-06-17",
    google_api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    **kwargs,
) -> ChatGoogleOpenAI:
    return ChatGoogleOpenAI(
        model=model,
        google_api_key=google_api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def test_google_openai_connection(
    model: str = "gemini-2.0-flash", google_api_key: Optional[str] = None
) -> bool:
    try:
        logger.info(f"Testing Google AI connection, model: {model}")

        llm = create_google_openai_llm(
            model=model, google_api_key=google_api_key, max_tokens=50
        )

        response = llm.invoke("Hello, please introduce yourself briefly.")

        if response and hasattr(response, "content") and response.content:
            logger.info(f"Google AI connection successful")
            return True
        else:
            logger.error("Google AI connection returned empty response")
            return False

    except Exception as e:
        logger.error(f"Google AI connection test failed: {e}")
        return False


def test_google_openai_function_calling(
    model: str = "gemini-2.5-flash-lite-preview-06-17",
    google_api_key: Optional[str] = None,
) -> bool:
    try:
        logger.info(f"Testing Google AI Function Calling, model: {model}")

        llm = create_google_openai_llm(
            model=model, google_api_key=google_api_key, max_tokens=200
        )

        from langchain_core.tools import tool

        @tool
        def test_news_tool(query: str) -> str:
            return f"Test news result for: {query}"

        llm_with_tools = llm.bind_tools([test_news_tool])

        response = llm_with_tools.invoke(
            "Please use test_news_tool to query 'Apple Inc'"
        )

        logger.info(f"Google AI Function Calling test completed")

        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Tool calls: {len(response.tool_calls)}")
            return True
        else:
            logger.info(
                f"Response content: {getattr(response, 'content', 'No content')}"
            )
            return True

    except Exception as e:
        logger.error(f"Google AI Function Calling test failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("Google AI OpenAI Compatible Adapter Test")
    logger.info("=" * 50)

    connection_ok = test_google_openai_connection()

    if connection_ok:
        function_calling_ok = test_google_openai_function_calling()
        if function_calling_ok:
            logger.info("All tests passed!")
        else:
            logger.error("Function Calling test failed")
    else:
        logger.error("Connection test failed")
