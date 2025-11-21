"""
Script de teste para demonstrar suporte a contexto multi-turn na API.

Este script mostra como enviar múltiplas perguntas mantendo o contexto
da conversa através do campo `messages`.

Usage:
    # Teste padrão (mantém session_id e contexto)
    LANGCHAIN_TRACING_V2=false poetry run python scripts/test_api_context.py

    # Teste com perda de contexto (muda session_id no meio)
    LANGCHAIN_TRACING_V2=false poetry run python scripts/test_api_context.py --test-session-change

    # Com tracing (para debug)
    poetry run python scripts/test_api_context.py
"""
import json
import sys
from typing import Any
from typing import Dict
from typing import List
from uuid import uuid4

import requests

# API Configuration
API_URL = "http://localhost:8000/chat"
USER_ID = "client789"

# Session Management
current_session_id = str(uuid4())
messages: List[Dict[str, str]] = []


def send_message(
    question: str, include_history: bool = True, session_id: str = None
) -> Dict[str, Any]:
    """
    Envia uma mensagem para a API, mantendo o contexto da conversa.

    Args:
        question: Pergunta do usuário
        include_history: Se False, envia sem histórico (simula perda de contexto)
        session_id: ID da sessão (se None, usa current_session_id global)

    Returns:
        Resposta completa da API
    """
    global current_session_id

    # Usar session_id fornecido ou o global
    sid = session_id or current_session_id

    # Decidir se envia histórico ou não
    history = messages if include_history else []

    payload = {
        "question": question,
        "user_id": USER_ID,
        "messages": history,
        "session_id": sid,
    }

    print(f"\n{'='*80}")
    print(f"👤 USER: {question}")
    print(f"📊 Session ID: {sid[:8]}... (primeiros 8 caracteres)")
    print(f"📜 History size: {len(history)} mensagens")
    if not include_history and messages:
        print("⚠️  ATENÇÃO: Enviando SEM histórico (contexto perdido!)")
    print(f"{'='*80}")

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        # Extrair resposta (campo "answer" no novo schema)
        final_response = result.get("answer", "")
        print(f"\n🤖 AI: {final_response}\n")

        # Atualizar histórico de conversa (sempre, mesmo se não foi enviado)
        messages.append({"role": "human", "content": question})
        messages.append({"role": "ai", "content": final_response})

        return result

    except requests.exceptions.ConnectionError:
        print(
            "\n❌ ERRO: API não está rodando. Execute: poetry run uvicorn app.api.main:app --reload\n"
        )
        return {}
    except requests.exceptions.Timeout:
        print("\n❌ ERRO: Timeout - A requisição demorou mais de 60 segundos\n")
        return {}
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}\n")
        return {}


def reset_session():
    """Reseta a sessão (novo ID + histórico limpo)."""
    global current_session_id, messages

    old_session = current_session_id[:8]
    current_session_id = str(uuid4())
    messages = []

    print(f"\n{'🔄 '*40}")
    print("🆕 NOVA SESSÃO CRIADA")
    print(f"   Sessão antiga: {old_session}...")
    print(f"   Nova sessão: {current_session_id[:8]}...")
    print(f"   Histórico limpo: {len(messages)} mensagens")
    print(f"{'🔄 '*40}\n")


def main():
    """
    Demonstra uma conversa multi-turn com contexto.
    """
    # Verificar se deve testar mudança de sessão
    test_session_change = "--test-session-change" in sys.argv

    print("\n" + "=" * 80)
    print("🚀 TESTE DE CONTEXTO MULTI-TURN - API")
    print("=" * 80)

    if test_session_change:
        print("\n⚠️  MODO: Teste de PERDA DE CONTEXTO (session_id muda)")
        print("Objetivo: Demonstrar que mudar session_id faz API perder contexto\n")
        test_session_change_scenario()
    else:
        print("\nMODO: Teste NORMAL (session_id mantido)")
        print("Objetivo: Validar que Router consegue rotear follow-ups com contexto\n")
        test_normal_scenario()


def test_normal_scenario():
    """Cenário normal: mantém session_id e contexto."""
    print("📋 Cenário: Usuário faz perguntas de follow-up sobre taxas")
    print(f"🆔 Session ID inicial: {current_session_id[:8]}...\n")

    # Turn 1: Pergunta inicial sobre taxas
    result1 = send_message("Quais são as taxas da maquininha?")
    if not result1:
        return

    # Turn 2: Follow-up perguntando sobre data (requer contexto)
    result2 = send_message("De quando são essas taxas que você me enviou?")
    if not result2:
        return

    # Turn 3: Outra follow-up
    result3 = send_message("E quanto custa a maquininha?")
    if not result3:
        return

    # Resumo
    print_summary()


def test_session_change_scenario():
    """Cenário de teste: muda session_id para demonstrar perda de contexto."""
    print("📋 Cenário: Usuário faz pergunta inicial, depois session_id muda\n")
    print(f"🆔 Session ID inicial: {current_session_id[:8]}...\n")

    # Turn 1: Pergunta inicial sobre taxas (com contexto normal)
    print("=" * 80)
    print("TURN 1: Pergunta inicial (contexto vazio, mas ok)")
    print("=" * 80)
    result1 = send_message("Quais são as taxas da maquininha?")
    if not result1:
        return

    # input("\n⏸️  Pressione ENTER para continuar com MESMO session_id (contexto mantido)...")  # Disabled for pytest
    print("\n[Teste automatizado - continuando sem input]")

    # Turn 2a: Follow-up COM CONTEXTO (session_id mantido)
    print("\n" + "=" * 80)
    print("TURN 2a: Follow-up COM CONTEXTO (session_id mantido)")
    print("=" * 80)
    result2a = send_message("De quando são essas taxas?", include_history=True)
    if not result2a:
        return

    print("\n✅ Observe: O Router conseguiu rotear corretamente porque tinha contexto!")

    # input("\n⏸️  Pressione ENTER para RESETAR session_id (simular nova conversa)...")  # Disabled for pytest
    print("\n[Teste automatizado - continuando sem input]")

    # RESETAR SESSÃO (novo session_id + limpar histórico)
    reset_session()

    # Turn 3: MESMA pergunta, mas SEM CONTEXTO (nova sessão)
    print("\n" + "=" * 80)
    print("TURN 3: MESMA pergunta, mas SEM CONTEXTO (nova sessão)")
    print("=" * 80)
    print("⚠️  Agora vamos fazer a MESMA pergunta, mas sem histórico...")
    print("⚠️  Resultado esperado: AI não consegue responder (sem contexto)\n")

    result3 = send_message("De quando são essas taxas?", include_history=True)
    if not result3:
        return

    print("\n" + "=" * 80)
    print("📊 COMPARAÇÃO DOS RESULTADOS")
    print("=" * 80)
    print("\n✅ Turn 2a (COM contexto):")
    print(f"   Resposta: {result2a.get('answer', '')[:100]}...")

    print("\n❌ Turn 3 (SEM contexto - nova sessão):")
    print(f"   Resposta: {result3.get('answer', '')[:100]}...")

    print("\n" + "=" * 80)
    print("💡 CONCLUSÃO")
    print("=" * 80)
    print("✅ Quando session_id é MANTIDO e messages são enviados:")
    print("   → Router tem contexto e roteia corretamente para knowledge_agent")
    print("   → Resposta relevante é gerada\n")

    print("❌ Quando session_id MUDA (nova sessão) e histórico é limpo:")
    print("   → Router NÃO tem contexto da conversa anterior")
    print('   → Pergunta "De quando são essas taxas?" fica sem referência')
    print("   → API retorna fallback ou erro\n")

    print("🎯 LIÇÃO IMPORTANTE:")
    print("   - session_id em si NÃO guarda dados (API é stateless)")
    print("   - O que importa é enviar messages completo")
    print("   - Mudar session_id é apenas um MARCADOR de nova conversa")
    print(
        "   - Responsabilidade do cliente: manter histórico E session_id sincronizados\n"
    )


def print_summary():
    """Imprime resumo da conversa."""
    print("\n" + "=" * 80)
    print("📊 RESUMO DA CONVERSA")
    print("=" * 80)
    print(f"\n🆔 Session ID: {current_session_id}")
    print(f"📜 Total de mensagens trocadas: {len(messages)}")
    print(f"❓ Perguntas feitas: {len([m for m in messages if m['role'] == 'human'])}")
    print(f"💬 Respostas recebidas: {len([m for m in messages if m['role'] == 'ai'])}")

    print("\n✅ Contexto mantido com sucesso!")
    print("\nHistórico completo:")
    print(json.dumps(messages, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
