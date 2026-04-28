#!/usr/bin/env python3
"""MVP standalone test for Kimi Coding API integration.

Ref: https://yangzh.cn/posts/posts/kimi-code-api-unofficial-guide.html/
Key points:
- User-Agent must be "KimiCLI/1.6"
- API key format must be "sk-kimi-xxx" (OAuth Access Token)
- /models may succeed while /chat/completions fails if UA is missing
- Use streaming to improve perceived latency
- HTTP Keep-Alive is enabled by default via httpx

Usage:
    export KIMI_API_KEY=sk-kimi-xxxx
    python scripts/test_kimi_mvp.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from tradingagents.llm_clients.openai_client import OpenAIClient, KimiChatOpenAI


def check_api_key():
    key = os.environ.get("KIMI_API_KEY", "")
    if not key:
        print("  [SKIP] KIMI_API_KEY not set in environment")
        return None
    if not key.startswith("sk-kimi-"):
        print(f"  [WARN] API key looks like a Developer key ({key[:7]}...).")
        print("         Kimi Code requires an OAuth Access Token starting with 'sk-kimi-'.")
    else:
        print(f"  [OK] API key format looks correct ({key[:12]}...)")
    return key


def test_client_config():
    print("\n1. Testing OpenAIClient configuration...")
    client = OpenAIClient("kimi-for-coding", provider="kimi")
    llm = client.get_llm()

    assert isinstance(llm, KimiChatOpenAI), f"Expected KimiChatOpenAI, got {type(llm)}"
    assert llm.model == "kimi-for-coding"
    assert llm.openai_api_base == "https://api.kimi.com/coding/v1"

    default_headers = getattr(llm, "default_headers", {}) or {}
    ua = default_headers.get("User-Agent")
    assert ua == "KimiCLI/1.6", f"User-Agent mismatch: {ua}"
    print(f"  [OK] model={llm.model}")
    print(f"  [OK] base_url={llm.openai_api_base}")
    print(f"  [OK] User-Agent={ua}")

    # Verify keep-alive limits are configured
    http_client = getattr(llm, "http_client", None)
    if http_client:
        limits = getattr(http_client, "limits", None)
        if limits:
            print(f"  [OK] Keep-Alive limits: max_keepalive={limits.max_keepalive_connections}, max_connections={limits.max_connections}")
        else:
            print("  [WARN] No explicit connection limits set")
    else:
        print("  [WARN] No http_client attached")
    return llm


def test_models_endpoint(api_key: str):
    print("\n2. Testing /models endpoint (token-only validation)...")
    url = "https://api.kimi.com/coding/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "KimiCLI/1.6",
    }
    try:
        r = httpx.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            print(f"  [OK] /models returned 200")
            data = r.json()
            models = [m.get("id", "") for m in data.get("data", [])]
            if "kimi-for-coding" in models:
                print("  [OK] 'kimi-for-coding' found in model list")
            else:
                print(f"  [WARN] 'kimi-for-coding' not in model list: {models[:5]}...")
        else:
            print(f"  [FAIL] /models returned {r.status_code}: {r.text[:200]}")
    except Exception as exc:
        print(f"  [FAIL] /models request failed: {exc}")


def test_chat_non_streaming(llm):
    print("\n3. Testing /chat/completions (non-streaming)...")
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
        return "Pong" in content
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        return False


def test_chat_streaming(llm):
    print("\n4. Testing /chat/completions (streaming)...")
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
    print("MVP Kimi Coding API Test")
    print("=" * 60)

    api_key = check_api_key()
    llm = test_client_config()

    results = []
    if api_key:
        test_models_endpoint(api_key)
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
