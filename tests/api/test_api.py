from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@patch("app.api.main.app_graph")
def test_chat_endpoint_returns_final_response(mock_app_graph):
    # Mock stream() to return node outputs
    mock_app_graph.stream.return_value = [
        {"router_agent": {"route": "knowledge_agent"}},
        {
            "knowledge_agent": {
                "final_response": "Olá, isso é um teste",
                "route": "synthesis_agent",
                "final_context": [],
            }
        },
        {
            "synthesis_agent": {
                "final_response": "Olá, isso é um teste",
                "route": "knowledge_agent",
                "final_context": [],
            }
        },
    ]

    payload = {
        "question": "Qual é o status?",
        "user_id": "tester",
        "user_name": "Test User",
    }
    r = client.post("/chat", json=payload)
    assert r.status_code == 200
    data = r.json()

    # Validate all response fields (new schema uses "answer" instead of "final_response")
    assert "answer" in data
    assert data["answer"] == "Olá, isso é um teste"
    assert "id" in data
    assert data["id"] is not None  # UUID should be generated
    assert "user_id" in data
    assert data["user_id"] == "tester"
    assert "user_name" in data
    assert data["user_name"] == "Test User"
    assert "timestamp" in data
    assert data["timestamp"] is not None
    assert "agent_used" in data
    assert data["agent_used"] == "knowledge_agent"


@patch("app.api.main.app_graph")
def test_chat_endpoint_handles_tools_called(mock_app_graph):
    """
    Test that API properly extracts tools_called from final_context.

    The graph returns tools_called nested inside final_context evidence items.
    API should extract and flatten them.
    """
    # Mock stream() to return node outputs with tools_called
    mock_app_graph.stream.return_value = [
        {"router_agent": {"route": "knowledge_agent"}},
        {
            "knowledge_agent": {
                "final_response": "Answer based on RAG",
                "route": "synthesis_agent",
                "final_context": [
                    {
                        "source": "knowledge_agent",
                        "tools_called": ["rag_tool", "web_search_tool"],
                        "content": "Retrieved information...",
                    }
                ],
            }
        },
        {
            "synthesis_agent": {
                "final_response": "Answer based on RAG",
                "route": "knowledge_agent",
                "final_context": [
                    {
                        "source": "knowledge_agent",
                        "tools_called": ["rag_tool", "web_search_tool"],
                        "content": "Retrieved information...",
                    }
                ],
            }
        },
    ]

    payload = {"question": "What is Open Banking?", "user_id": "tester"}

    r = client.post("/chat", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert data["answer"] == "Answer based on RAG"
    assert data["tools_called"] == ["rag_tool", "web_search_tool"]
    assert data["agent_used"] == "knowledge_agent"
