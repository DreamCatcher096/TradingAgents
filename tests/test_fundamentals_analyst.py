import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


def _make_module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


@contextmanager
def _patched_modules(replacements):
    originals = {name: sys.modules.get(name) for name in replacements}
    try:
        for name, module in replacements.items():
            sys.modules[name] = module
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class _Prompt:
    def partial(self, **_kwargs):
        return self

    def __or__(self, other):
        return other


class _ChatPromptTemplate:
    @staticmethod
    def from_messages(_messages):
        return _Prompt()


class _MessagesPlaceholder:
    def __init__(self, variable_name):
        self.variable_name = variable_name


class _Tool:
    def __init__(self, name, result=None):
        self.name = name
        self._result = result if result is not None else {"tool": name}
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return {"name": self.name, "args": args, "result": self._result}


class _Result:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _BoundLLM:
    def __init__(self, llm):
        self._llm = llm

    def invoke(self, messages):
        self._llm.invocations.append(messages)
        return self._llm.result


class _FakeLLM:
    def __init__(self, result=None):
        self.result = result or _Result(
            tool_calls=[
                {
                    "name": "get_stock_fundamentals_unified",
                    "args": {"symbol": "600519.SH"},
                    "id": "call-1",
                }
            ]
        )
        self.bound_tools = None
        self.invocations = []

    def bind_tools(self, tools):
        self.bound_tools = tools
        return _BoundLLM(self)


def _load_fundamentals_module(google_handler=object, market_info=None):
    if market_info is None:
        market_info = {"is_china": False}

    replacements = {
        "langchain_core.prompts": _make_module(
            "langchain_core.prompts",
            ChatPromptTemplate=_ChatPromptTemplate,
            MessagesPlaceholder=_MessagesPlaceholder,
        ),
        "tradingagents.agents.utils.agent_utils": _make_module(
            "tradingagents.agents.utils.agent_utils",
            build_instrument_context=lambda ticker: f"context for {ticker}",
            get_balance_sheet=_Tool("get_balance_sheet"),
            get_cashflow=_Tool("get_cashflow"),
            get_fundamentals=_Tool("get_fundamentals"),
            get_income_statement=_Tool("get_income_statement"),
            get_insider_transactions=_Tool("get_insider_transactions"),
            get_language_instruction=lambda: "",
        ),
        "tradingagents.dataflows.config": _make_module(
            "tradingagents.dataflows.config", get_config=lambda: {}
        ),
        "tradingagents.agents.utils.google_tool_handler": _make_module(
            "tradingagents.agents.utils.google_tool_handler",
            GoogleToolCallHandler=google_handler,
        ),
        "tradingagents.utils.stock_utils": _make_module(
            "tradingagents.utils.stock_utils",
            StockUtils=SimpleNamespace(get_market_info=lambda _ticker: market_info),
        ),
        "tradingagents.dataflows.china_router": _make_module(
            "tradingagents.dataflows.china_router",
            ChinaDataRouter=lambda: SimpleNamespace(providers=[]),
        ),
    }

    module_path = (
        Path(__file__).resolve().parents[1]
        / "tradingagents"
        / "agents"
        / "analysts"
        / "fundamentals_analyst.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_fundamentals_analyst_module", module_path
    )
    module = importlib.util.module_from_spec(spec)
    with _patched_modules(replacements):
        spec.loader.exec_module(module)
    return module


class _StateGraph:
    def __init__(self, _state_type):
        self.nodes = {}

    def add_node(self, name, node):
        self.nodes[name] = node

    def add_edge(self, *_args, **_kwargs):
        return None

    def add_conditional_edges(self, *_args, **_kwargs):
        return None

    def compile(self):
        return self


def _load_graph_setup_module(factory_calls):
    graph_package = _make_module("tradingagents.graph")
    graph_package.__path__ = [
        str(Path(__file__).resolve().parents[1] / "tradingagents" / "graph")
    ]

    agents_module = _make_module(
        "tradingagents.agents",
        create_msg_delete=lambda: "delete-node",
        create_market_analyst=lambda llm, **_kwargs: "market-node",
        create_social_media_analyst=lambda llm, **_kwargs: "social-node",
        create_news_analyst=lambda llm, **_kwargs: "news-node",
        create_bull_researcher=lambda llm, memory: "bull-node",
        create_bear_researcher=lambda llm, memory: "bear-node",
        create_research_manager=lambda llm, memory: "research-manager",
        create_trader=lambda llm, memory: "trader-node",
        create_aggressive_debator=lambda llm: "aggressive-node",
        create_neutral_debator=lambda llm: "neutral-node",
        create_conservative_debator=lambda llm: "conservative-node",
        create_portfolio_manager=lambda llm, memory: "portfolio-manager",
    )

    def _create_fundamentals_analyst(llm, toolkit=None):
        factory_calls["fundamentals"] = {"llm": llm, "toolkit": toolkit}
        return "fundamentals-node"

    agents_module.create_fundamentals_analyst = _create_fundamentals_analyst

    agents_analysts_module = _make_module(
        "tradingagents.agents.analysts",
        create_china_market_analyst=lambda llm, toolkit=None: "china-market-node",
    )

    replacements = {
        "langgraph.graph": _make_module(
            "langgraph.graph", END="END", START="START", StateGraph=_StateGraph
        ),
        "langgraph.prebuilt": _make_module("langgraph.prebuilt", ToolNode=object),
        "tradingagents.agents.utils.agent_states": _make_module(
            "tradingagents.agents.utils.agent_states", AgentState=object
        ),
        "tradingagents.graph.conditional_logic": _make_module(
            "tradingagents.graph.conditional_logic", ConditionalLogic=object
        ),
        "tradingagents.graph": graph_package,
        "tradingagents.agents": agents_module,
        "tradingagents.agents.analysts": agents_analysts_module,
        "tradingagents.agents.analysts.china_market_analyst": _make_module(
            "tradingagents.agents.analysts.china_market_analyst",
            create_china_market_analyst=lambda llm, toolkit=None: "china-market-node",
        ),
    }

    module_path = (
        Path(__file__).resolve().parents[1] / "tradingagents" / "graph" / "setup.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tradingagents.graph.test_setup_module", module_path
    )
    module = importlib.util.module_from_spec(spec)
    with _patched_modules(replacements):
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        sys.modules.pop(spec.name, None)
    return module


class _ToolNode:
    def __init__(self, tools):
        self.tools = tools


def _load_trading_graph_module():
    graph_package = _make_module("tradingagents.graph")
    graph_package.__path__ = [
        str(Path(__file__).resolve().parents[1] / "tradingagents" / "graph")
    ]

    replacements = {
        "langgraph.prebuilt": _make_module("langgraph.prebuilt", ToolNode=_ToolNode),
        "langchain_openai": _make_module("langchain_openai", ChatOpenAI=object),
        "tradingagents.llm_clients": _make_module(
            "tradingagents.llm_clients", create_llm_client=lambda **_kwargs: None
        ),
        "tradingagents.llm_adapters": _make_module(
            "tradingagents.llm_adapters",
            ChatDashScopeOpenAI=object,
            ChatGoogleOpenAI=object,
            ChatDeepSeek=object,
            HAS_CN_ADAPTERS=False,
        ),
        "tradingagents.agents": _make_module("tradingagents.agents"),
        "tradingagents.default_config": _make_module(
            "tradingagents.default_config", DEFAULT_CONFIG={}
        ),
        "tradingagents.agents.utils.memory": _make_module(
            "tradingagents.agents.utils.memory",
            FinancialSituationMemory=lambda *_args, **_kwargs: None,
        ),
        "tradingagents.agents.utils.agent_states": _make_module(
            "tradingagents.agents.utils.agent_states",
            AgentState=object,
            InvestDebateState=object,
            RiskDebateState=object,
        ),
        "tradingagents.dataflows.config": _make_module(
            "tradingagents.dataflows.config", set_config=lambda _config: None
        ),
        "tradingagents.agents.utils.agent_utils": _make_module(
            "tradingagents.agents.utils.agent_utils",
            Toolkit=lambda config=None: None,
            get_stock_data=_Tool("get_stock_data"),
            get_indicators=_Tool("get_indicators"),
            get_fundamentals=_Tool("get_fundamentals"),
            get_balance_sheet=_Tool("get_balance_sheet"),
            get_cashflow=_Tool("get_cashflow"),
            get_income_statement=_Tool("get_income_statement"),
            get_news=_Tool("get_news"),
            get_insider_transactions=_Tool("get_insider_transactions"),
            get_global_news=_Tool("get_global_news"),
        ),
        "tradingagents.graph.conditional_logic": _make_module(
            "tradingagents.graph.conditional_logic", ConditionalLogic=object
        ),
        "tradingagents.graph.setup": _make_module(
            "tradingagents.graph.setup", GraphSetup=object
        ),
        "tradingagents.graph.propagation": _make_module(
            "tradingagents.graph.propagation", Propagator=object
        ),
        "tradingagents.graph.reflection": _make_module(
            "tradingagents.graph.reflection", Reflector=object
        ),
        "tradingagents.graph.signal_processing": _make_module(
            "tradingagents.graph.signal_processing", SignalProcessor=object
        ),
        "tradingagents.graph": graph_package,
    }

    module_path = (
        Path(__file__).resolve().parents[1]
        / "tradingagents"
        / "graph"
        / "trading_graph.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tradingagents.graph.test_trading_graph_module", module_path
    )
    module = importlib.util.module_from_spec(spec)
    with _patched_modules(replacements):
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        sys.modules.pop(spec.name, None)
    return module


class FundamentalsAnalystTests(unittest.TestCase):
    def test_uses_unified_fundamentals_tool_when_toolkit_is_provided(self):
        module = _load_fundamentals_module()
        llm = _FakeLLM()
        unified_tool = _Tool("get_stock_fundamentals_unified")
        toolkit = SimpleNamespace(get_stock_fundamentals_unified=unified_tool)

        node = module.create_fundamentals_analyst(llm, toolkit=toolkit)
        result = node(
            {
                "trade_date": "2025-04-15",
                "company_of_interest": "600519.SH",
                "messages": [],
            }
        )

        self.assertEqual(llm.bound_tools, [unified_tool])
        self.assertEqual(result["messages"][0].tool_calls[0]["name"], unified_tool.name)

    def test_forces_one_unified_fetch_when_llm_skips_tool_calls(self):
        module = _load_fundamentals_module()
        llm = _FakeLLM(result=_Result(content="analysis without tools", tool_calls=[]))
        unified_tool = _Tool(
            "get_stock_fundamentals_unified", result="fallback fundamentals"
        )
        toolkit = SimpleNamespace(get_stock_fundamentals_unified=unified_tool)

        node = module.create_fundamentals_analyst(llm, toolkit=toolkit)
        result = node(
            {
                "trade_date": "2025-04-15",
                "company_of_interest": "600519.SH",
                "messages": [],
            }
        )

        self.assertEqual(
            unified_tool.calls,
            [{"symbol": "600519.SH", "curr_date": "2025-04-15"}],
        )
        self.assertIn("fallback fundamentals", result["fundamentals_report"])

    def test_graph_setup_passes_shared_toolkit_into_fundamentals_analyst(self):
        factory_calls = {}
        module = _load_graph_setup_module(factory_calls)
        toolkit = object()
        conditional_logic = SimpleNamespace(
            should_continue_fundamentals=lambda *_args, **_kwargs: "tools_fundamentals",
            should_continue_debate=lambda *_args, **_kwargs: "Research Manager",
            should_continue_risk_analysis=lambda *_args, **_kwargs: "Portfolio Manager",
        )

        graph_setup = module.GraphSetup(
            quick_thinking_llm="quick-llm",
            deep_thinking_llm="deep-llm",
            tool_nodes={"fundamentals": "fundamentals-tools"},
            bull_memory=object(),
            bear_memory=object(),
            trader_memory=object(),
            invest_judge_memory=object(),
            portfolio_manager_memory=object(),
            conditional_logic=conditional_logic,
            toolkit=toolkit,
        )

        graph_setup.setup_graph(selected_analysts=["fundamentals"])

        self.assertIs(factory_calls["fundamentals"]["toolkit"], toolkit)

    def test_trading_graph_uses_unified_tool_for_fundamentals_tool_node(self):
        module = _load_trading_graph_module()
        graph = module.TradingAgentsGraph.__new__(module.TradingAgentsGraph)
        unified_tool = _Tool("get_stock_fundamentals_unified")
        graph.toolkit = SimpleNamespace(
            get_stock_fundamentals_unified=unified_tool,
            get_stock_market_data_unified=_Tool("get_stock_market_data_unified"),
            get_indicators_unified=_Tool("get_indicators_unified"),
            get_stock_sentiment_unified=_Tool("get_stock_sentiment_unified"),
            get_stock_news_unified=_Tool("get_stock_news_unified"),
            get_global_news_unified=_Tool("get_global_news_unified"),
        )

        tool_nodes = graph._create_tool_nodes()

        self.assertEqual(tool_nodes["fundamentals"].tools, [unified_tool])

    def test_google_models_delegate_fundamentals_tool_processing_to_handler(self):
        handler_calls = {}

        class _GoogleToolHandler:
            @staticmethod
            def is_google_model(_llm):
                return True

            @staticmethod
            def create_analysis_prompt(**kwargs):
                handler_calls["prompt_kwargs"] = kwargs
                return "google-analysis-prompt"

            @staticmethod
            def handle_google_tool_calls(**kwargs):
                handler_calls["tool_names"] = [tool.name for tool in kwargs["tools"]]
                handler_calls["analyst_name"] = kwargs["analyst_name"]
                return "google fundamentals report", ["google-message"]

        module = _load_fundamentals_module(
            google_handler=_GoogleToolHandler,
            market_info={"is_china": True},
        )
        llm = _FakeLLM()
        toolkit = SimpleNamespace(
            get_stock_fundamentals_unified=_Tool("get_stock_fundamentals_unified")
        )

        node = module.create_fundamentals_analyst(llm, toolkit=toolkit)
        result = node(
            {
                "trade_date": "2025-04-15",
                "company_of_interest": "600519.SH",
                "messages": [],
            }
        )

        self.assertEqual(result["fundamentals_report"], "google fundamentals report")
        self.assertEqual(
            handler_calls["tool_names"], ["get_stock_fundamentals_unified"]
        )
        self.assertEqual(handler_calls["analyst_name"], "Fundamentals Analyst")

    def test_tracks_fundamentals_tool_call_count_for_tool_driven_responses(self):
        module = _load_fundamentals_module()
        llm = _FakeLLM()
        toolkit = SimpleNamespace(
            get_stock_fundamentals_unified=_Tool("get_stock_fundamentals_unified")
        )

        node = module.create_fundamentals_analyst(llm, toolkit=toolkit)
        result = node(
            {
                "trade_date": "2025-04-15",
                "company_of_interest": "600519.SH",
                "messages": [],
                "fundamentals_tool_call_count": 0,
            }
        )

        self.assertEqual(result["fundamentals_tool_call_count"], 1)


if __name__ == "__main__":
    unittest.main()
