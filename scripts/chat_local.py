#!/usr/bin/env python3
"""
CLI to send a question to the local agent graph or to the API.

Usage:
  python scripts/chat_local.py --message "Qual é a taxa da maquininha?" --user client789
  python scripts/chat_local.py --interactive
  python scripts/chat_local.py --mock  # returns mock response

The script prefers to call the graph in-process (no network) by importing
`app.graph.builder.app_graph`. If that import fails, it falls back to HTTP
against the API (`http://{host}:{port}/chat`).
"""
import argparse
import json
import os
import sys
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def call_graph(message: str, user_id: str, mock: bool = False) -> dict:
    # Build state and invoke app_graph if available
    try:
        from langchain_core.messages import HumanMessage
        from app.graph.builder import app_graph
    except Exception:
        app_graph = None

    state = {
        "messages": [],
        "user_id": user_id,
        "route": "",
        "final_context": [],
        "final_response": "",
    }

    # Add HumanMessage if langchain is present
    try:
        from langchain_core.messages import HumanMessage

        state["messages"].append(HumanMessage(content=message))
    except Exception:
        # fallback to simple dict with .content attribute emulation
        class _M:
            def __init__(self, content):
                self.content = content

        state["messages"].append(_M(message))

    # Mock mode
    if mock or os.environ.get("MOCK_GRAPH", "false").lower() in ("1", "true", "yes"):
        return {"final_response": "[MOCK] resposta de desenvolvimento", "mock": True}

    if app_graph is not None:
        try:
            result = app_graph.invoke(state)
            # Convert LangChain messages to JSON-serializable format
            if "messages" in result:
                result["messages"] = [
                    {"role": getattr(m, "type", "unknown"), "content": m.content}
                    for m in result.get("messages", [])
                ]
            return result
        except Exception as e:
            return {"error": "invoke_failed", "message": str(e)}

    # Fallback: HTTP request to API endpoint
    host = os.environ.get("API_HOST", "localhost")
    port = os.environ.get("API_PORT", "8000")
    url = f"http://{host}:{port}/chat"

    import requests

    payload = {"user_id": user_id, "question": message}
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("API_KEY")
    if api_key:
        headers["X-API-KEY"] = api_key

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": "http_failed", "message": str(e)}


def main(argv: Optional[list] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", "-m", type=str, help="Message to send")
    parser.add_argument("--user", "-u", default="client789", help="user id")
    parser.add_argument(
        "--mock", action="store_true", help="Use mock mode (no LLM calls)"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    args = parser.parse_args(argv)

    if args.interactive:
        print("Enter message (empty line to send, Ctrl-D to exit)")
        try:
            while True:
                msg = input("> ")
                if not msg.strip():
                    continue
                res = call_graph(msg, args.user, mock=args.mock)
                print(json.dumps(res, ensure_ascii=False, indent=2))
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            sys.exit(0)

    if not args.message:
        print("Please provide --message or use --interactive")
        sys.exit(2)

    res = call_graph(args.message, args.user, mock=args.mock)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
