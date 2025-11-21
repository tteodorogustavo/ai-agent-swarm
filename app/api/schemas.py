import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class NodeExecution(BaseModel):
    """Representa a execução detalhada de um node no graph."""

    node_name: str = Field(..., description="Nome do node executado")
    timestamp: str = Field(..., description="Momento da execução")
    state_updates: Dict[str, Any] = Field(
        default_factory=dict, description="Atualizações de estado feitas pelo node"
    )


class ChatDebugResponse(BaseModel):
    """Resposta detalhada do chat com informações de debug sobre execução interna."""

    # Metadata
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="ID único desta resposta"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp da resposta em formato ISO 8601",
    )

    # User context
    user_id: Optional[str] = Field(None, description="ID do usuário que fez a pergunta")
    user_name: Optional[str] = Field(None, description="Nome do usuário (se fornecido)")
    session_id: Optional[str] = Field(None, description="ID da sessão (se fornecido)")

    # Response content
    answer: str = Field(..., description="Resposta final gerada pelo agente")

    # Processing metadata
    agent_used: Optional[str] = Field(
        None, description="Agente principal que processou a pergunta"
    )
    tools_called: Optional[List[str]] = Field(
        default=None, description="Ferramentas utilizadas durante o processamento"
    )
    execution_steps: Optional[List[str]] = Field(
        default=None, description="Nodes executados (ordem)"
    )

    # Debug information
    detailed_execution: List[NodeExecution] = Field(
        default_factory=list,
        description="Execução detalhada de cada node com state updates",
    )
    initial_state: Dict[str, Any] = Field(
        default_factory=dict, description="Estado inicial antes da execução"
    )
    final_state: Dict[str, Any] = Field(
        default_factory=dict, description="Estado final após toda execução"
    )


class Message(BaseModel):
    """Representa uma mensagem no histórico de conversação."""

    role: str = Field(..., description="Role da mensagem: 'human' ou 'ai'")
    content: str = Field(..., description="Conteúdo da mensagem")


class ChatRequest(BaseModel):
    question: str = Field(..., description="Pergunta atual do usuário")
    user_id: Optional[str] = Field(None, description="ID único do usuário")
    user_name: Optional[str] = Field(None, description="Nome do usuário (opcional)")
    messages: Optional[List[Message]] = Field(
        default=None,
        description="Histórico de mensagens anteriores para manter contexto (opcional)",
    )
    session_id: Optional[str] = Field(
        None, description="ID da sessão para rastreamento de conversas (opcional)"
    )


class ChatResponse(BaseModel):
    """Resposta do chat estruturada e organizada."""

    # Metadata
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="ID único desta resposta"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp da resposta em formato ISO 8601",
    )

    # User context
    user_id: Optional[str] = Field(None, description="ID do usuário que fez a pergunta")
    user_name: Optional[str] = Field(None, description="Nome do usuário (se fornecido)")
    session_id: Optional[str] = Field(None, description="ID da sessão (se fornecido)")

    # Response content
    answer: str = Field(..., description="Resposta final gerada pelo agente")

    # Processing metadata
    agent_used: Optional[str] = Field(
        None,
        description="Agente principal que processou a pergunta (knowledge/customer)",
    )
    tools_called: Optional[List[str]] = Field(
        default=None, description="Ferramentas utilizadas durante o processamento"
    )
    execution_steps: Optional[List[str]] = Field(
        default=None,
        description="Nodes executados durante o processamento (ordem de execução)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-11-21T10:30:00Z",
                "user_id": "user_123",
                "user_name": "João Silva",
                "session_id": "session_456",
                "answer": "Seu saldo atual é de R$ 2.450,00. Você ainda tem R$ 550,00 disponíveis do seu limite diário.",
                "agent_used": "customer_agent",
                "tools_called": ["get_account_balance", "get_current_datetime"],
            }
        }
    )
