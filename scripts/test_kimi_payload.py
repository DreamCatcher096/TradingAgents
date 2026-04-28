#!/usr/bin/env python3
"""Quick verification that KimiChatOpenAI._get_request_payload is hit."""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.llm_clients.openai_client import OpenAIClient, KimiChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

client = OpenAIClient("kimi-for-coding", provider="kimi")
llm = client.get_llm()
print("LLM type:", type(llm))

# monkey-patch to see if _get_request_payload is called
orig = llm._get_request_payload


def _patched(input_, *, stop=None, **kwargs):
    payload = orig(input_, stop=stop, **kwargs)
    print("[PATCH] _get_request_payload called!")
    print("[PATCH] assistant messages:", [m for m in payload.get("messages", []) if m.get("role") == "assistant"])
    return payload


llm._get_request_payload = _patched

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Say hi."),
]
try:
    result = llm.invoke(messages)
    print("Response:", result.content)
except Exception as e:
    print("Error:", e)
