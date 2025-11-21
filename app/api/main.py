import os
from datetime import datetime
from datetime import timezone

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage

from .schemas import ChatDebugResponse
from .schemas import ChatRequest
from .schemas import ChatResponse
from .schemas import NodeExecution

try:
    from app.graph.builder import app_graph
except Exception:
    app_graph = None


app = FastAPI(title="AI Agent Swarm API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """Send a question to the agent graph and return the final_response."""
    if app_graph is None:
        raise HTTPException(status_code=500, detail="Application graph not available")

    # Build message history from `messages` (if provided)
    messages = []
    if payload.messages:
        for msg in payload.messages:
            if msg.role == "human":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "ai":
                messages.append(AIMessage(content=msg.content))

    # Add current question as the latest human message
    messages.append(HumanMessage(content=payload.question))

    # Prepare state with full conversation context
    state = {
        "messages": messages,
        "user_id": payload.user_id or "anonymous",
        "original_question": payload.question,
        "route": "",
        "router_calls": 0,
        "final_context": [],
        "final_response": "",
    }

    # Support quick local mock mode: if MOCK_GRAPH=true in env, return a fake response
    if os.environ.get("MOCK_GRAPH", "false").lower() in ("1", "true", "yes"):
        return ChatResponse(
            answer="[MOCK] resposta de desenvolvimento",
            user_id=payload.user_id,
            user_name=payload.user_name,
            session_id=payload.session_id,
        )

    try:
        # Use stream() to capture intermediate nodes
        execution_steps = []
        final_state = None

        for output in app_graph.stream(state):
            # Each output is a dict with node_name: state_update
            for node_name, state_update in output.items():
                execution_steps.append(node_name)
                final_state = state_update

        # The final state is the last update
        result = final_state if final_state else {}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Graph invocation failed: {str(e)}"
        )

    if not isinstance(result, dict) or "final_response" not in result:
        raise HTTPException(status_code=500, detail="Invalid graph response")

    # Extrai informações do resultado do graph
    agent_used = result.get("route", None)

    # Extract tools from final_context (evidence box)
    tools_called = []
    for evidence in result.get("final_context", []):
        if isinstance(evidence, dict) and "tools_called" in evidence:
            # evidence["tools_called"] is already a list
            tools_called.extend(evidence["tools_called"])

    return ChatResponse(
        answer=result.get("final_response"),
        user_id=payload.user_id,
        user_name=payload.user_name,
        session_id=payload.session_id,
        agent_used=agent_used,
        tools_called=tools_called if tools_called else None,
        execution_steps=execution_steps if execution_steps else None,
    )


@app.post("/chat/debug", response_model=ChatDebugResponse)
def chat_debug_endpoint(payload: ChatRequest):
    """Send a question to the agent graph and return detailed execution information."""
    if app_graph is None:
        raise HTTPException(status_code=500, detail="Application graph not available")

    # Build message history from `messages` (if provided)
    messages = []
    if payload.messages:
        for msg in payload.messages:
            if msg.role == "human":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "ai":
                messages.append(AIMessage(content=msg.content))

    # Add current question as the latest human message
    messages.append(HumanMessage(content=payload.question))

    # Prepare state with full conversation context
    state = {
        "messages": messages,
        "user_id": payload.user_id or "anonymous",
        "original_question": payload.question,
        "route": "",
        "router_calls": 0,
        "final_context": [],
        "final_response": "",
    }

    # Store initial state for debugging
    initial_state = {
        k: str(v)[:200] if isinstance(v, list) else v for k, v in state.items()
    }

    # Support quick local mock mode
    if os.environ.get("MOCK_GRAPH", "false").lower() in ("1", "true", "yes"):
        return ChatDebugResponse(
            answer="[MOCK] resposta de desenvolvimento",
            user_id=payload.user_id,
            user_name=payload.user_name,
            session_id=payload.session_id,
            initial_state=initial_state,
            final_state={"final_response": "[MOCK] resposta de desenvolvimento"},
        )

    try:
        # Use stream() to capture ALL intermediate nodes and their state updates
        execution_steps = []
        detailed_execution = []
        final_state = None

        for output in app_graph.stream(state):
            # Each output is a dict with node_name: state_update
            for node_name, state_update in output.items():
                execution_steps.append(node_name)

                # Create detailed execution record
                node_execution = NodeExecution(
                    node_name=node_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    state_updates={
                        k: str(v)[:500] if isinstance(v, (list, dict)) else v
                        for k, v in state_update.items()
                        if k not in ["messages"]  # Exclude messages for brevity
                    },
                )
                detailed_execution.append(node_execution)

                final_state = state_update

        # The final state is the last update
        result = final_state if final_state else {}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Graph invocation failed: {str(e)}"
        )

    if not isinstance(result, dict) or "final_response" not in result:
        raise HTTPException(status_code=500, detail="Invalid graph response")

    # Extract information from result
    agent_used = result.get("route", None)

    # Extract tools from final_context
    tools_called = []
    for evidence in result.get("final_context", []):
        if isinstance(evidence, dict) and "tools_called" in evidence:
            tools_called.extend(evidence["tools_called"])

    # Prepare final state for response (truncate large values)
    final_state_clean = {
        k: str(v)[:500] if isinstance(v, (list, dict)) else v
        for k, v in result.items()
        if k not in ["messages"]
    }

    return ChatDebugResponse(
        answer=result.get("final_response"),
        user_id=payload.user_id,
        user_name=payload.user_name,
        session_id=payload.session_id,
        agent_used=agent_used,
        tools_called=tools_called if tools_called else None,
        execution_steps=execution_steps if execution_steps else None,
        detailed_execution=detailed_execution,
        initial_state=initial_state,
        final_state=final_state_clean,
    )
