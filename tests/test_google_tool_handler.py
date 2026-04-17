import unittest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler


class FakeGoogleLLM:
    """模拟 Google Gemini LLM"""

    def __init__(self, final_content="Google final report"):
        self.final_content = final_content

    def invoke(self, messages):
        return MagicMock(content=self.final_content)

    def __class_getitem__(cls, item):
        return cls

    @classmethod
    def __class__(cls):
        class FakeClass:
            __name__ = "ChatGoogleOpenAI"

        return FakeClass()


class FakeTool:
    name = "get_stock_fundamentals_unified"

    def invoke(self, args):
        return {"pe": 15.2, "pb": 2.1, "roe": 18.5}


class GoogleToolHandlerTests(unittest.TestCase):
    def _make_google_llm(self):
        llm = FakeGoogleLLM()
        # 让 is_google_model 识别为 Google 模型
        llm.__class__ = type("ChatGoogleOpenAI", (), {"__name__": "ChatGoogleOpenAI"})
        return llm

    def test_is_google_model_detects_google_subclass(self):
        llm = self._make_google_llm()
        self.assertTrue(GoogleToolCallHandler.is_google_model(llm))

    def test_handle_google_tool_calls_executes_tools_and_generates_report(self):
        llm = self._make_google_llm()
        tool = FakeTool()
        result = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_stock_fundamentals_unified",
                    "args": {"symbol": "AAPL"},
                    "id": "call_1",
                }
            ],
        )

        report, messages = GoogleToolCallHandler.handle_google_tool_calls(
            result=result,
            llm=llm,
            tools=[tool],
            state={"messages": []},
            analysis_prompt_template="Generate a report",
            analyst_name="Fundamentals Analyst",
        )

        self.assertEqual(report, "Google final report")
        self.assertEqual(len(messages), 3)  # AIMessage + ToolMessage + final AIMessage

    def test_handle_google_tool_calls_skips_invalid_tool_calls(self):
        llm = self._make_google_llm()
        tool = FakeTool()
        result = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_stock_fundamentals_unified",
                    "args": {"symbol": "AAPL"},
                    "id": "call_1",
                }
            ],
        )
        # 手动注入一个无效 tool_call 以验证跳过逻辑
        result.tool_calls = [
            {
                "name": "get_stock_fundamentals_unified",
                "args": {"symbol": "AAPL"},
                "id": "call_1",
            },
            {
                # invalid - missing required fields
                "args": {"symbol": "TSLA"},
            },
        ]

        report, messages = GoogleToolCallHandler.handle_google_tool_calls(
            result=result,
            llm=llm,
            tools=[tool],
            state={"messages": []},
            analysis_prompt_template="Generate a report",
            analyst_name="Fundamentals Analyst",
        )

        self.assertEqual(report, "Google final report")
        # Should only have 1 ToolMessage because invalid call is skipped
        tool_messages = [m for m in messages if getattr(m, "type", None) == "tool"]
        self.assertEqual(len(tool_messages), 1)

    def test_handle_google_tool_calls_no_tools_returns_content_directly(self):
        """当没有 tool_calls 时，直接返回 content"""
        llm = self._make_google_llm()
        result = AIMessage(content="No tools needed", tool_calls=[])

        report, messages = GoogleToolCallHandler.handle_google_tool_calls(
            result=result,
            llm=llm,
            tools=[FakeTool()],
            state={"messages": []},
            analysis_prompt_template="Generate a report",
            analyst_name="Market Analyst",
        )

        self.assertEqual(report, "No tools needed")
        self.assertEqual(messages, [result])

    def test_fix_tool_call_recovers_function_format(self):
        """测试 _fix_tool_call 能从 LangChain function 格式恢复"""
        broken_call = {
            "function": {
                "name": "get_stock_data",
                "arguments": '{"symbol": "NVDA"}',
            }
        }
        fixed = GoogleToolCallHandler._fix_tool_call(broken_call, 0, "Market Analyst")
        self.assertIsNotNone(fixed)
        self.assertEqual(fixed["name"], "get_stock_data")
        self.assertEqual(fixed["args"], {"symbol": "NVDA"})
        self.assertTrue(fixed["id"].startswith("call_"))

    def test_non_google_model_skips_special_handling(self):
        class FakeOpenAILLM:
            pass

        llm = FakeOpenAILLM()
        result = AIMessage(content="OpenAI result", tool_calls=[])
        report, messages = GoogleToolCallHandler.handle_google_tool_calls(
            result=result,
            llm=llm,
            tools=[],
            state={},
            analysis_prompt_template="",
            analyst_name="Analyst",
        )
        self.assertEqual(report, "OpenAI result")
        self.assertEqual(messages, [result])


if __name__ == "__main__":
    unittest.main()
