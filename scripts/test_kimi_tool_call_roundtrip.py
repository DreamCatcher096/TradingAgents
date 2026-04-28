#!/usr/bin/env python3
"""Direct test: send a conversation with assistant tool_calls but no reasoning_content."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from tradingagents.llm_clients.openai_client import OpenAIClient

# load .env
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

# Monkey-patch openai client to see the actual request body
import json

orig_post = llm.client._post


def debug_post(self, path, *, cast_to, body, **kwargs):
    print("[DEBUG] Actual HTTP body sent to", path)
    print(json.dumps(body, indent=2, ensure_ascii=False))
    return orig_post(path, cast_to=cast_to, body=body, **kwargs)


llm.client._post = debug_post.__get__(llm.client, type(llm.client))

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is 2+2? Use the dummy tool."),
    AIMessage(
        content="",
        tool_calls=[
            {
                "id": "call_123",
                "name": "dummy",
                "args": {},
            }
        ],
    ),
    ToolMessage(content="4", tool_call_id="call_123"),
]

print("Sending conversation with assistant tool_calls...")
try:
    result = llm.invoke(messages)
    print("Success:", result.content)
except Exception as e:
    print("Error:", e)
