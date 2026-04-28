#!/usr/bin/env python3
"""Reproduce the Kimi 400 error in a non-interactive graph run."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from cli.stats_handler import StatsCallbackHandler


def main():
    # load .env if present
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v)

    # Monkey-patch to debug payload
    from tradingagents.llm_clients.openai_client import KimiChatOpenAI

    orig_get_payload = KimiChatOpenAI._get_request_payload

    def debug_get_payload(self, input_, *, stop=None, **kwargs):
        payload = orig_get_payload(self, input_, stop=stop, **kwargs)
        print("[DEBUG] _get_request_payload called")
        for i, m in enumerate(payload.get("messages", [])):
            if m.get("role") == "assistant" and "tool_calls" in m:
                print(f"[DEBUG] assistant msg {i}: has reasoning_content={'reasoning_content' in m}")
        return payload

    KimiChatOpenAI._get_request_payload = debug_get_payload

    config = DEFAULT_CONFIG.copy()
    config.update(
        {
            "llm_provider": "kimi",
            "backend_url": "https://api.kimi.com/coding/v1",
            "quick_think_llm": "kimi-for-coding",
            "deep_think_llm": "kimi-for-coding",
            "output_language": "English",
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
        }
    )

    stats_handler = StatsCallbackHandler()
    graph = TradingAgentsGraph(
        ["market"],  # Only Market Analyst to isolate
        config=config,
        debug=True,
        callbacks=[stats_handler],
    )

    init_state = graph.propagator.create_initial_state("AAPL", "2025-01-02")
    args = graph.propagator.get_graph_args(callbacks=[stats_handler])

    print("Starting graph stream with Kimi...")
    for chunk in graph.graph.stream(init_state, **args):
        print("Chunk keys:", list(chunk.keys()))
        for msg in chunk.get("messages", []):
            print("Message:", type(msg).__name__, getattr(msg, "role", None))

    print("Done.")


if __name__ == "__main__":
    main()
