import os
import logging
from typing import Any, Dict, List, Optional, Union
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
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


class ChatDeepSeek(ChatOpenAI):
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        if api_key is None:
            env_api_key = os.getenv("DEEPSEEK_API_KEY")

            if env_api_key and _is_valid_api_key(env_api_key):
                api_key = env_api_key
                logger.info("[DeepSeek] Using valid API Key from environment")
            elif env_api_key:
                logger.warning(
                    "[DeepSeek] API Key in env is invalid (placeholder?), ignoring"
                )
                api_key = None
            else:
                api_key = None

            if not api_key:
                raise ValueError(
                    "DeepSeek API key not found. "
                    "Set DEEPSEEK_API_KEY environment variable."
                )

        super().__init__(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        self.model_name = model

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            result = super()._generate(messages, stop, run_manager, **kwargs)

            input_tokens = 0
            output_tokens = 0

            if hasattr(result, "llm_output") and result.llm_output:
                token_usage = result.llm_output.get("token_usage", {})
                if token_usage:
                    input_tokens = token_usage.get("prompt_tokens", 0)
                    output_tokens = token_usage.get("completion_tokens", 0)

            if input_tokens == 0 and output_tokens == 0:
                input_tokens = self._estimate_input_tokens(messages)
                output_tokens = self._estimate_output_tokens(result)
                logger.debug(
                    f"[DeepSeek] Estimated tokens: input={input_tokens}, output={output_tokens}"
                )
            else:
                logger.info(
                    f"[DeepSeek] Actual token usage: input={input_tokens}, output={output_tokens}"
                )

            if input_tokens > 0 or output_tokens > 0:
                logger.info(
                    f"Token usage - Provider: deepseek, Model: {self.model_name}, "
                    f"input: {input_tokens}, output: {output_tokens}"
                )

            return result

        except Exception as e:
            logger.error(f"[DeepSeek] Call failed: {e}", exc_info=True)
            raise

    def _estimate_input_tokens(self, messages: List[BaseMessage]) -> int:
        total_chars = 0
        for message in messages:
            if hasattr(message, "content"):
                total_chars += len(str(message.content))
        return max(1, total_chars // 2)

    def _estimate_output_tokens(self, result: ChatResult) -> int:
        total_chars = 0
        for generation in result.generations:
            if hasattr(generation, "message") and hasattr(
                generation.message, "content"
            ):
                total_chars += len(str(generation.message.content))
        return max(1, total_chars // 2)

    def invoke(
        self,
        input: Union[str, List[BaseMessage]],
        config: Optional[Dict] = None,
        **kwargs: Any,
    ) -> AIMessage:
        if isinstance(input, str):
            messages = [HumanMessage(content=input)]
        else:
            messages = input

        result = self._generate(messages, **kwargs)

        if result.generations:
            return result.generations[0].message
        else:
            return AIMessage(content="")


def create_deepseek_llm(
    model: str = "deepseek-chat",
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> ChatDeepSeek:
    return ChatDeepSeek(
        model=model, temperature=temperature, max_tokens=max_tokens, **kwargs
    )


DeepSeekLLM = ChatDeepSeek
