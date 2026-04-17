import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Stubs for heavy dependencies used by agent_utils.py and its imports
if "langchain_core.messages" not in sys.modules:
    messages_module = types.ModuleType("langchain_core.messages")

    class _Message:
        def __init__(self, content=None, id=None):
            self.content = content
            self.id = id

    messages_module.HumanMessage = _Message
    messages_module.RemoveMessage = _Message
    sys.modules["langchain_core.messages"] = messages_module

if "langchain_core.tools" not in sys.modules:
    tools_module = types.ModuleType("langchain_core.tools")

    def _tool(fn):
        return fn

    tools_module.tool = _tool
    sys.modules["langchain_core.tools"] = tools_module

# Pre-stub utility submodules so agent_utils can import them
_stubbed_tool_funcs = {}


def _stub_module(name, **attributes):
    if name not in sys.modules:
        module = types.ModuleType(name)
        for key, value in attributes.items():
            setattr(module, key, value)
        sys.modules[name] = module


_stub_module(
    "tradingagents.agents.utils.core_stock_tools",
    get_stock_data=Mock(),
    get_YFin_data=Mock(),
    get_YFin_data_online=Mock(),
)
_stub_module(
    "tradingagents.agents.utils.technical_indicators_tools",
    get_indicators=Mock(),
)
_stub_module(
    "tradingagents.agents.utils.fundamental_data_tools",
    get_fundamentals=Mock(),
    get_balance_sheet=Mock(),
    get_cashflow=Mock(),
    get_income_statement=Mock(),
)
_stub_module(
    "tradingagents.agents.utils.news_data_tools",
    get_news=Mock(),
    get_global_news=Mock(),
    get_insider_transactions=Mock(),
)

# Save original china_router module (if already imported) and replace with stub
_original_china_router_module = sys.modules.get("tradingagents.dataflows.china_router")
china_router_stub = types.ModuleType("tradingagents.dataflows.china_router")


class _FakeChinaRouter:
    def __init__(self, provider_order=None):
        self.provider_order = provider_order


china_router_stub.ChinaDataRouter = _FakeChinaRouter
sys.modules["tradingagents.dataflows.china_router"] = china_router_stub

# Import stock_utils normally (it has no heavy deps)

# Load agent_utils directly to avoid triggering tradingagents.agents package imports
agent_utils_path = (
    Path(__file__).resolve().parents[1]
    / "tradingagents"
    / "agents"
    / "utils"
    / "agent_utils.py"
)
agent_utils_spec = importlib.util.spec_from_file_location(
    "test_agent_utils", agent_utils_path
)
agent_utils = importlib.util.module_from_spec(agent_utils_spec)
agent_utils_spec.loader.exec_module(agent_utils)
Toolkit = agent_utils.Toolkit


class ToolkitTests(unittest.TestCase):
    def test_market_data_unified_routes_a_shares_to_china_router(self):
        toolkit = Toolkit()
        mock_router = Mock()
        toolkit.china_router = mock_router
        mock_router.get_stock_data.return_value = "mock china data"
        result = toolkit.get_stock_market_data_unified(
            "600519.SH", "2025-01-01", "2025-04-15"
        )

        self.assertEqual(result, "mock china data")
        mock_router.get_stock_data.assert_called_once_with(
            "600519.SH", "2025-01-01", "2025-04-15"
        )

    def test_fundamentals_unified_routes_a_shares_to_china_router(self):
        toolkit = Toolkit()
        mock_router = Mock()
        toolkit.china_router = mock_router
        mock_router.get_fundamentals.return_value = {"pe": 20}
        result = toolkit.get_stock_fundamentals_unified("600519.SH")

        self.assertEqual(result, {"pe": 20})
        mock_router.get_fundamentals.assert_called_once_with("600519.SH")

    def test_news_unified_routes_a_shares_to_china_router(self):
        toolkit = Toolkit()
        mock_router = Mock()
        toolkit.china_router = mock_router
        mock_router.get_news.return_value = [{"title": "t"}]
        result = toolkit.get_stock_news_unified("600519.SH", max_news=5)

        # UnifiedNewsAnalyzer formats the result as a string
        self.assertIsInstance(result, str)
        self.assertIn("AKShare/东方财富", result)
        mock_router.get_news.assert_called_once_with("600519.SH", limit=5)

    def test_market_data_unified_falls_back_to_offline_yfinance_for_us_symbol(self):
        toolkit = Toolkit()
        with patch.object(agent_utils, "get_stock_data") as mock_get:
            mock_get.invoke.return_value = "offline yf data"
            result = toolkit.get_stock_market_data_unified(
                "AAPL", "2025-01-01", "2025-04-15"
            )

        self.assertEqual(result, "offline yf data")
        mock_get.invoke.assert_called_once()


# Restore original china_router module so other test modules aren't affected
if _original_china_router_module is not None:
    sys.modules["tradingagents.dataflows.china_router"] = _original_china_router_module
else:
    sys.modules.pop("tradingagents.dataflows.china_router", None)

if __name__ == "__main__":
    unittest.main()
