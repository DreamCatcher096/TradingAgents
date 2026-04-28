import os
import unittest
from unittest.mock import patch

from tradingagents.graph.trading_graph import create_llm_by_provider
from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek


class TestDeepSeekAdapter(unittest.TestCase):
    def test_create_llm_by_provider_rejects_empty_env_key(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "DeepSeek API key not found"):
                create_llm_by_provider(
                    provider="deepseek",
                    model="deepseek-chat",
                    backend_url="https://api.deepseek.com",
                )

    def test_round_trips_reasoning_content_for_assistant_tool_calls(self):
        llm = ChatDeepSeek(api_key="sk-test-valid-key", model="deepseek-chat")

        result = llm._create_chat_result(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "dummy_tool",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                            "reasoning_content": "reasoning trace",
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            }
        )

        message = result.generations[0].message

        self.assertEqual(
            message.additional_kwargs.get("reasoning_content"), "reasoning trace"
        )

        payload = llm._get_request_payload([message])

        self.assertEqual(
            payload["messages"][0].get("reasoning_content"), "reasoning trace"
        )


if __name__ == "__main__":
    unittest.main()
