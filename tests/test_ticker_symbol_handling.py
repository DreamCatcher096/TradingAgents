import unittest
import sys
import types
import importlib.util
from pathlib import Path


if "questionary" not in sys.modules:
    sys.modules["questionary"] = types.SimpleNamespace(
        text=lambda *args, **kwargs: None,
        checkbox=lambda *args, **kwargs: None,
        select=lambda *args, **kwargs: None,
        Style=lambda *args, **kwargs: None,
        Choice=lambda *args, **kwargs: None,
    )

if "tradingagents.llm_clients" not in sys.modules:
    llm_clients_module = types.ModuleType("tradingagents.llm_clients")
    model_catalog_module = types.ModuleType("tradingagents.llm_clients.model_catalog")
    model_catalog_module.get_model_options = lambda *args, **kwargs: []
    llm_clients_module.model_catalog = model_catalog_module
    sys.modules["tradingagents.llm_clients"] = llm_clients_module
    sys.modules["tradingagents.llm_clients.model_catalog"] = model_catalog_module

if "langchain_core.messages" not in sys.modules:
    messages_module = types.ModuleType("langchain_core.messages")

    class _Message:
        def __init__(self, content=None, id=None):
            self.content = content
            self.id = id

    messages_module.HumanMessage = _Message
    messages_module.RemoveMessage = _Message
    sys.modules["langchain_core.messages"] = messages_module


def _stub_module(name, **attributes):
    if name not in sys.modules:
        module = types.ModuleType(name)
        for key, value in attributes.items():
            setattr(module, key, value)
        sys.modules[name] = module


_stub_module(
    "tradingagents.agents.utils.core_stock_tools",
    get_stock_data=object(),
)
_stub_module(
    "tradingagents.agents.utils.technical_indicators_tools",
    get_indicators=object(),
)
_stub_module(
    "tradingagents.agents.utils.fundamental_data_tools",
    get_fundamentals=object(),
    get_balance_sheet=object(),
    get_cashflow=object(),
    get_income_statement=object(),
)
_stub_module(
    "tradingagents.agents.utils.news_data_tools",
    get_news=object(),
    get_insider_transactions=object(),
    get_global_news=object(),
)

import pytest

from cli.utils import normalize_ticker_symbol

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
build_instrument_context = agent_utils.build_instrument_context


@pytest.mark.unit
class TickerSymbolHandlingTests(unittest.TestCase):
    def test_normalize_ticker_symbol_preserves_exchange_suffix(self):
        self.assertEqual(normalize_ticker_symbol(" cnc.to "), "CNC.TO")

    def test_normalize_ticker_symbol_autocompletes_a_share_symbols(self):
        self.assertEqual(normalize_ticker_symbol(" 600519 "), "600519.SH")
        self.assertEqual(normalize_ticker_symbol("600519.ss"), "600519.SH")
        self.assertEqual(normalize_ticker_symbol("000001"), "000001.SZ")

    def test_build_instrument_context_mentions_exact_symbol(self):
        context = build_instrument_context("7203.T")
        self.assertIn("7203.T", context)
        self.assertIn("exchange suffix", context)

    def test_build_instrument_context_mentions_market_metadata_for_a_shares(self):
        context = build_instrument_context("600519.SH")
        self.assertIn("China A", context)
        self.assertIn("Shanghai Stock Exchange", context)
        self.assertIn("600519.SH", context)


if __name__ == "__main__":
    unittest.main()
