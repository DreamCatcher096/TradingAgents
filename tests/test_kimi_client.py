import os
import unittest
from unittest.mock import patch

from tradingagents.llm_clients.openai_client import OpenAIClient


class KimiClientTests(unittest.TestCase):
    """Verify OpenAIClient correctly configures Kimi provider."""

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_kimi_base_url_and_api_key(self, mock_chat):
        with patch.dict(os.environ, {"KIMI_API_KEY": "kimi-test-key-789"}):
            client = OpenAIClient("kimi-k2.5", provider="kimi")
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs.get("base_url"), "https://api.kimi.com/coding/v1")
        self.assertEqual(call_kwargs.get("api_key"), "kimi-test-key-789")
        self.assertEqual(call_kwargs.get("model"), "kimi-k2.5")
        # Kimi is third-party; should NOT use responses API
        self.assertNotIn("use_responses_api", call_kwargs)

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_kimi_user_agent_header(self, mock_chat):
        with patch.dict(os.environ, {"KIMI_API_KEY": "kimi-test-key"}):
            client = OpenAIClient("kimi-k2", provider="kimi")
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        http_client = call_kwargs.get("http_client")
        self.assertIsNotNone(http_client)
        self.assertEqual(
            http_client.headers.get("User-Agent"),
            "KimiCLI/1.30.0",
        )

    @patch("tradingagents.llm_clients.openai_client.NormalizedChatOpenAI")
    def test_kimi_preserves_custom_http_client(self, mock_chat):
        import httpx

        custom_client = httpx.Client(headers={"X-Custom": "value"})

        with patch.dict(os.environ, {"KIMI_API_KEY": "kimi-test-key"}):
            client = OpenAIClient("kimi-k2.5", provider="kimi", http_client=custom_client)
            client.get_llm()

        call_kwargs = mock_chat.call_args[1]
        # When a custom http_client is provided, do not override it
        self.assertIs(call_kwargs.get("http_client"), custom_client)


if __name__ == "__main__":
    unittest.main()
