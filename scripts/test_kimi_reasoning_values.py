#!/usr/bin/env python3
"""Test different reasoning_content values."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from tradingagents.llm_clients.openai_client import OpenAIClient

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

client = OpenAIClient("kimi-for-coding", provider="kimi")
llm = client.get_llm()

# Patch _post to inject different reasoning_content values
import json

orig_post = llm.client._post


def make_post(reasoning_value):
    def debug_post(self, path, *, cast_to, body, **kwargs):
        if isinstance(body, dict) and "messages" in body:
            for m in body["messages"]:
                if m.get("role") == "assistant" and "tool_calls" in m:
                    m["reasoning_content"] = reasoning_value
        print(f"[TEST] reasoning_content={reasoning_value!r}")
        return orig_post(path, cast_to=cast_to, body=body, **kwargs)

    return debug_post


messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is 2+2?"),
    AIMessage(content="", tool_calls=[{"id": "call_123", "name": "dummy", "args": {}}]),
    ToolMessage(content="4", tool_call_id="call_123"),
]

for val in ["", None, " ", "thinking", {"text": ""}, []]:
    llm.client._post = make_post(val).__get__(llm.client, type(llm.client))
    try:
        result = llm.invoke(messages)
        print(f"[PASS] value={val!r}, response={result.content!r}")
    except Exception as e:
        err = str(e)
        if "reasoning_content is missing" in err:
            print(f"[FAIL] value={val!r} -> still missing")
        else:
            print(f"[FAIL] value={val!r} -> {err[:100]}")
    print()
