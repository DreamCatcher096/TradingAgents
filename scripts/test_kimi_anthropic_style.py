#!/usr/bin/env python3
"""Standalone test: Kimi via Anthropic-style (Messages API) client.

Some providers support both OpenAI (/v1/chat/completions) and Anthropic
(/v1/messages) formats. This script tests whether Kimi Code API works
better with Anthropic-style requests.

Usage:
    export KIMI_API_KEY=sk-kimi-xxxx
    python scripts/test_kimi_anthropic_style.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage

from tradingagents.llm_clients.anthropic_client import AnthropicClient


def check_api_key():
    key = os.environ.get("KIMI_API_KEY", "")
    if not key:
        print("  [SKIP] KIMI_API_KEY not set in environment")
        return None
    print(f"  [OK] API key present ({key[:12]}...)")
    return key


def test_anthropic_style_client(api_key: str | None):
    print("\n1. Testing AnthropicClient configured for Kimi...")
    kwargs = {"base_url": "https://api.kimi.com/coding/v1"}
    if api_key:
        kwargs["api_key"] = api_key
    client = AnthropicClient("kimi-for-coding", **kwargs)
    llm = client.get_llm()

    print(f"  [OK] model={llm.model}")
    print(f"  [OK] base_url={llm.anthropic_api_url}")
    return llm


def test_chat_non_streaming(llm):
    print("\n2. Testing Anthropic-style /v1/messages (non-streaming)...")
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Say exactly 'Pong' and nothing else."),
    ]
    t0 = time.time()
    try:
        result = llm.invoke(messages)
        latency = time.time() - t0
        content = getattr(result, "content", str(result))
        print(f"  [OK] latency={latency:.2f}s, response={content.strip()!r}")
        return True
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        return False


def test_chat_streaming(llm):
    print("\n3. Testing Anthropic-style /v1/messages (streaming)...")
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Count from 1 to 3."),
    ]
    t0 = time.time()
    chunks = []
    try:
        for chunk in llm.stream(messages):
            text = getattr(chunk, "content", str(chunk))
            if text:
                chunks.append(text)
        latency = time.time() - t0
        full = "".join(chunks)
        print(f"  [OK] latency={latency:.2f}s, streamed={full.strip()!r}")
        return True
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        return False


def main():
    print("=" * 60)
    print("MVP Kimi via Anthropic-style Client Test")
    print("=" * 60)

    api_key = check_api_key()
    llm = test_anthropic_style_client(api_key)

    results = []
    if api_key:
        results.append(("non-streaming", test_chat_non_streaming(llm)))
        results.append(("streaming", test_chat_streaming(llm)))
    else:
        print("\n  Skipping live API tests (no KIMI_API_KEY)")

    print("\n" + "=" * 60)
    if results:
        status = all(r[1] for r in results)
        for name, ok in results:
            print(f"  {name}: {'PASS' if ok else 'FAIL'}")
        print(f"\nOverall: {'PASS' if status else 'FAIL'}")
    else:
        print("Overall: PASS (config only)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
