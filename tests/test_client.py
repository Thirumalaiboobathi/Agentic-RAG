"""
test_client.py
--------------
Minimal WebSocket client to test the multi-agent server locally.

Usage:
    python test_client.py "How many orders were placed yesterday?"
    python test_client.py "What is OTB's SLA policy?"
    python test_client.py "What are the latest developments in AI agents?"

Connects to ws://localhost:8000/ws/agent, sends the query, and prints
every progress event as it streams back.
"""

import asyncio
import json
import sys

import websockets


async def run(query: str):
    uri = "ws://localhost:8000/ws/agent"
    async with websockets.connect(uri) as ws:
        # Send the query
        await ws.send(json.dumps({"session_id": "test-session", "query": query}))
        print(f"\n>>> Query: {query}\n")
        print("-" * 60)

        # Receive streamed events until turn_complete
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "agent_selected":
                print(f"[ROUTE]    {msg['agent']:10} | {msg['message']}")
            elif event == "agent_progress":
                print(f"[PROGRESS] {msg['agent']:10} | {msg['message']}")
            elif event == "agent_complete":
                print("-" * 60)
                print(f"\n=== FINAL RESPONSE ===\n{msg['data']['response']}\n")
            elif event == "eval_captured":
                print(f"[EVAL]     trace_id = {msg['data']['trace_id']}")
            elif event == "guardrail_blocked":
                print(f"[BLOCKED]  {msg['message']}")
            elif event == "error":
                print(f"[ERROR]    {msg['message']}")
            elif event == "turn_complete":
                print(f"[DONE]     turn complete (trace: {msg.get('trace_id', '')[:8]})")
                break


if __name__ == "__main__":
    # How GenAI differs from Traditional AI 
    # What is in the science paper about photosynthesis from internal document

    query = sys.argv[1] if len(sys.argv) > 1 else "What orders were placed from past one week? Show me the order details."
    asyncio.run(run(query))
