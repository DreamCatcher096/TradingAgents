# TradingAgents/graph/trading_graph.py

import logging
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional

import yfinance as yf

logger = logging.getLogger(__name__)
from langgraph.prebuilt import ToolNode

from tradingagents.llm_clients import create_llm_client

# LLM adapters - with try/except for optional import
try:
    from tradingagents.llm_adapters.dashscope_openai_adapter import ChatDashScopeOpenAI
    from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek
    from tradingagents.llm_adapters.google_openai_adapter import ChatGoogleOpenAI
    from tradingagents.llm_adapters.openai_compatible_base import (
        create_openai_compatible_llm,
    )

    HAS_CN_ADAPTERS = True
except ImportError:
    HAS_CN_ADAPTERS = False

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config

from tradingagents.agents.utils.agent_utils import Toolkit

from .checkpointer import checkpoint_step, clear_checkpoint, get_checkpointer, thread_id
from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor

CN_PROVIDERS = {
    "dashscope",
    "deepseek",
    "zhipu",
    "siliconflow",
    "qianfan",
    "custom_openai",
}


def create_llm_by_provider(
    provider: str,
    model: str,
    backend_url: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    timeout: int = 180,
    api_key: str = None,
):
    provider_lower = provider.lower()

    if HAS_CN_ADAPTERS:
        if provider_lower == "dashscope":
            return ChatDashScopeOpenAI(
                model=model,
                api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
                base_url=backend_url or None,
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=timeout,
            )
        if provider_lower == "deepseek":
            return ChatDeepSeek(
                model=model,
                api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
                base_url=backend_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        if provider_lower == "zhipu":
            return create_openai_compatible_llm(
                provider="zhipu",
                model=model,
                api_key=api_key or os.getenv("ZHIPU_API_KEY"),
                base_url=backend_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        if provider_lower in ("qianfan", "custom_openai"):
            return create_openai_compatible_llm(
                provider=provider_lower,
                model=model,
                base_url=backend_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        if provider_lower == "google":
            return ChatGoogleOpenAI(
                model=model,
                google_api_key=api_key or os.getenv("GOOGLE_API_KEY"),
                base_url=backend_url or None,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

    if provider_lower in ("openai", "siliconflow", "openrouter", "ollama"):
        env_key = {
            "siliconflow": "SILICONFLOW_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
        }.get(provider_lower)
        resolved_key = api_key or (os.getenv(env_key) if env_key else None)
        return ChatOpenAI(
            model=model,
            base_url=backend_url,
            api_key=resolved_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider_lower == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            base_url=backend_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    env_candidates = [
        f"{provider.upper()}_API_KEY",
        f"{provider}_API_KEY",
        "CUSTOM_OPENAI_API_KEY",
    ]
    resolved_key = api_key
    if not resolved_key:
        for env_var in env_candidates:
            resolved_key = os.getenv(env_var)
            if resolved_key:
                break

    return ChatOpenAI(
        model=model,
        base_url=backend_url,
        api_key=resolved_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
        callbacks: Optional[List] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        os.makedirs(self.config["results_dir"], exist_ok=True)

        # Initialize LLMs
        # Support mixed provider mode and CN providers
        quick_provider = (
            self.config.get("quick_think_llm_provider") or self.config["llm_provider"]
        ).lower()
        deep_provider = (
            self.config.get("deep_think_llm_provider") or self.config["llm_provider"]
        ).lower()

        is_mixed_mode = quick_provider != deep_provider
        is_cn_provider = quick_provider in CN_PROVIDERS or deep_provider in CN_PROVIDERS

        if (is_mixed_mode or is_cn_provider) and HAS_CN_ADAPTERS:
            quick_model_config = self.config.get("quick_model_config", {})
            deep_model_config = self.config.get("deep_model_config", {})

            self.quick_thinking_llm = create_llm_by_provider(
                provider=quick_provider,
                model=self.config["quick_think_llm"],
                backend_url=self.config.get("quick_backend_url")
                or self.config.get("backend_url", ""),
                temperature=quick_model_config.get("temperature", 0.7),
                max_tokens=quick_model_config.get("max_tokens", 4000),
                timeout=quick_model_config.get("timeout", 180),
                api_key=self.config.get("quick_api_key"),
            )
            self.deep_thinking_llm = create_llm_by_provider(
                provider=deep_provider,
                model=self.config["deep_think_llm"],
                backend_url=self.config.get("deep_backend_url")
                or self.config.get("backend_url", ""),
                temperature=deep_model_config.get("temperature", 0.7),
                max_tokens=deep_model_config.get("max_tokens", 4000),
                timeout=deep_model_config.get("timeout", 180),
                api_key=self.config.get("deep_api_key"),
            )
        else:
            llm_kwargs = self._get_provider_kwargs()
            if self.callbacks:
                llm_kwargs["callbacks"] = self.callbacks

            deep_client = create_llm_client(
                provider=self.config["llm_provider"],
                model=self.config["deep_think_llm"],
                base_url=self.config.get("backend_url"),
                **llm_kwargs,
            )
            quick_client = create_llm_client(
                provider=self.config["llm_provider"],
                model=self.config["quick_think_llm"],
                base_url=self.config.get("backend_url"),
                **llm_kwargs,
            )
        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()
        
        self.toolkit = Toolkit(config=self.config)
        self.memory_log = TradingMemoryLog(self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config["max_debate_rounds"],
            max_risk_discuss_rounds=self.config["max_risk_discuss_rounds"],
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.conditional_logic,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph: keep the workflow for recompilation with a checkpointer.
        self.workflow = self.graph_setup.setup_graph(selected_analysts)
        self.graph = self.workflow.compile()
        self._checkpointer_ctx = None

    def _get_provider_kwargs(self) -> Dict[str, Any]:
        """Get provider-specific kwargs for LLM client creation."""
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()

        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level

        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

        elif provider == "anthropic":
            effort = self.config.get("anthropic_effort")
            if effort:
                kwargs["effort"] = effort

        return kwargs

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using Toolkit methods."""
        toolkit = self.toolkit
        return {
            "market": ToolNode(
                [
                    toolkit.get_stock_market_data_unified,
                    toolkit.get_indicators_unified,
                ]
            ),
            "social": ToolNode(
                [
                    toolkit.get_stock_sentiment_unified,
                ]
            ),
            "news": ToolNode(
                [
                    toolkit.get_stock_news_unified,
                    toolkit.get_global_news_unified,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    toolkit.get_stock_fundamentals_unified,
                ]
            ),
            "china_market": ToolNode(
                [
                    toolkit.get_stock_market_data_unified,
                ]
            ),
        }

    def _fetch_returns(
        self, ticker: str, trade_date: str, holding_days: int = 5
    ) -> Tuple[Optional[float], Optional[float], Optional[int]]:
        """Fetch raw and alpha return for ticker over holding_days from trade_date.

        Returns (raw_return, alpha_return, actual_holding_days) or
        (None, None, None) if price data is unavailable (too recent, delisted,
        or network error).
        """
        try:
            start = datetime.strptime(trade_date, "%Y-%m-%d")
            end = start + timedelta(days=holding_days + 7)  # buffer for weekends/holidays
            end_str = end.strftime("%Y-%m-%d")

            stock = yf.Ticker(ticker).history(start=trade_date, end=end_str)
            spy = yf.Ticker("SPY").history(start=trade_date, end=end_str)

            if len(stock) < 2 or len(spy) < 2:
                return None, None, None

            actual_days = min(holding_days, len(stock) - 1, len(spy) - 1)
            raw = float(
                (stock["Close"].iloc[actual_days] - stock["Close"].iloc[0])
                / stock["Close"].iloc[0]
            )
            spy_ret = float(
                (spy["Close"].iloc[actual_days] - spy["Close"].iloc[0])
                / spy["Close"].iloc[0]
            )
            alpha = raw - spy_ret
            return raw, alpha, actual_days
        except Exception as e:
            logger.warning(
                "Could not resolve outcome for %s on %s (will retry next run): %s",
                ticker, trade_date, e,
            )
            return None, None, None

    def _resolve_pending_entries(self, ticker: str) -> None:
        """Resolve pending log entries for ticker at the start of a new run.

        Fetches returns for each same-ticker pending entry, generates reflections,
        then writes all updates in a single atomic batch write to avoid redundant I/O.
        Skips entries whose price data is not yet available (too recent or delisted).

        Trade-off: only same-ticker entries are resolved per run.  Entries for
        other tickers accumulate until that ticker is run again.
        """
        pending = [e for e in self.memory_log.get_pending_entries() if e["ticker"] == ticker]
        if not pending:
            return

        updates = []
        for entry in pending:
            raw, alpha, days = self._fetch_returns(ticker, entry["date"])
            if raw is None:
                continue  # price not available yet — try again next run
            reflection = self.reflector.reflect_on_final_decision(
                final_decision=entry.get("decision", ""),
                raw_return=raw,
                alpha_return=alpha,
            )
            updates.append({
                "ticker": ticker,
                "trade_date": entry["date"],
                "raw_return": raw,
                "alpha_return": alpha,
                "holding_days": days,
                "reflection": reflection,
            })

        if updates:
            self.memory_log.batch_update_with_outcomes(updates)

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date.

        When ``checkpoint_enabled`` is set in config, the graph is recompiled
        with a per-ticker SqliteSaver so a crashed run can resume from the last
        successful node on a subsequent invocation with the same ticker+date.
        """
        self.ticker = company_name

        # Resolve any pending memory-log entries for this ticker before the pipeline runs.
        self._resolve_pending_entries(company_name)

        # Recompile with a checkpointer if the user opted in.
        if self.config.get("checkpoint_enabled"):
            self._checkpointer_ctx = get_checkpointer(
                self.config["data_cache_dir"], company_name
            )
            saver = self._checkpointer_ctx.__enter__()
            self.graph = self.workflow.compile(checkpointer=saver)

            step = checkpoint_step(
                self.config["data_cache_dir"], company_name, str(trade_date)
            )
            if step is not None:
                logger.info(
                    "Resuming from step %d for %s on %s", step, company_name, trade_date
                )
            else:
                logger.info("Starting fresh for %s on %s", company_name, trade_date)

        try:
            return self._run_graph(company_name, trade_date)
        finally:
            if self._checkpointer_ctx is not None:
                self._checkpointer_ctx.__exit__(None, None, None)
                self._checkpointer_ctx = None
                self.graph = self.workflow.compile()

    def _run_graph(self, company_name, trade_date):
        """Execute the graph and write the resulting state to disk and memory log."""
        # Initialize state — inject memory log context for PM.
        past_context = self.memory_log.get_past_context(company_name)
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date, past_context=past_context
        )
        args = self.propagator.get_graph_args()

        # Inject thread_id so same ticker+date resumes, different date starts fresh.
        if self.config.get("checkpoint_enabled"):
            tid = thread_id(company_name, str(trade_date))
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = tid

        if self.debug:
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)
            final_state = trace[-1]
        else:
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection.
        self.curr_state = final_state

        # Log state to disk.
        self._log_state(trade_date, final_state)

        # Store decision for deferred reflection on the next same-ticker run.
        self.memory_log.store_decision(
            ticker=company_name,
            trade_date=trade_date,
            final_trade_decision=final_state["final_trade_decision"],
        )

        # Clear checkpoint on successful completion to avoid stale state.
        if self.config.get("checkpoint_enabled"):
            clear_checkpoint(
                self.config["data_cache_dir"], company_name, str(trade_date)
            )

        return final_state, self.process_signal(final_state["final_trade_decision"])

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "china_market_report": final_state.get("china_market_report", ""),
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "aggressive_history": final_state["risk_debate_state"][
                    "aggressive_history"
                ],
                "conservative_history": final_state["risk_debate_state"][
                    "conservative_history"
                ],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = (
            Path(self.config["results_dir"])
            / self.ticker
            / "TradingAgentsStrategy_logs"
        )
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / f"full_states_log_{trade_date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.log_states_dict[str(trade_date)], f, indent=4)

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
