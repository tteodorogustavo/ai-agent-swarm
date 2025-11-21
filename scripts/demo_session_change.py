#!/usr/bin/env python3
"""
Demo Interativo: Mudança de Session ID e Perda de Contexto

Este script permite que você controle manualmente quando mudar o session_id
para ver exatamente como o contexto é perdido.

Usage:
    LANGCHAIN_TRACING_V2=false poetry run python scripts/demo_session_change.py
"""
import sys
from uuid import uuid4

import requests


API_URL = "http://localhost:8000/chat"
USER_ID = "demo_user"

# Estado da conversa
session_id = str(uuid4())
messages = []


def print_header(title):
    """Imprime um cabeçalho formatado."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_status():
    """Mostra o estado atual da sessão."""
    print(f"🆔 Session ID: {session_id[:12]}...")
    print(f"📜 Histórico: {len(messages)} mensagens")


def send_message(question, send_history=True):
    """Envia mensagem para a API."""
    global messages

    history = messages if send_history else []

    payload = {
        "question": question,
        "user_id": USER_ID,
        "session_id": session_id,
        "messages": history,
    }

    print("\n📤 Enviando:")
    print(f'   Pergunta: "{question}"')
    print(f"   Session ID: {session_id[:12]}...")
    print(f"   Histórico enviado: {len(history)} mensagens")

    if not send_history and messages:
        print(
            f"   ⚠️  ATENÇÃO: Histórico local tem {len(messages)} msgs, mas enviando 0!"
        )

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        final_response = result.get("answer", "")

        print("\n📥 Resposta da API:")
        print(f"   {final_response}\n")

        # Atualizar histórico local
        messages.append({"role": "human", "content": question})
        messages.append({"role": "ai", "content": final_response})

        return result

    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: API não está rodando!")
        print("   Execute: poetry run uvicorn app.api.main:app --reload\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}\n")
        return None


def reset_session():
    """Cria nova sessão (novo ID + limpa histórico)."""
    global session_id, messages

    old_id = session_id[:12]
    session_id = str(uuid4())
    old_history_size = len(messages)
    messages = []

    print(f"\n{'🔄 '*40}")
    print("  🆕 NOVA SESSÃO CRIADA")
    print(f"{'🔄 '*40}")
    print(f"   Session ID antiga: {old_id}...")
    print(f"   Session ID nova: {session_id[:12]}...")
    print(f"   Histórico: {old_history_size} → 0 mensagens (LIMPO)")
    print(f"{'🔄 '*40}\n")


def main():
    """Demo interativo."""
    print_header("🚀 DEMO: Session ID e Contexto Multi-Turn")

    print("Este demo mostra como o session_id e messages funcionam.\n")
    print("📌 IMPORTANTE:")
    print("   - API é STATELESS (não guarda nada)")
    print("   - Cliente deve enviar messages a cada mensagem")
    print("   - session_id é apenas um marcador (não guarda dados)")
    print("   - Mudar session_id = começar conversa nova (histórico limpo)\n")

    input("Pressione ENTER para começar...")

    # ========== PARTE 1: Conversa Normal ==========
    print_header("PARTE 1: Conversa Normal (COM contexto)")
    print_status()

    print("\n1️⃣ Vamos fazer a primeira pergunta:")
    send_message("Quais são as taxas da maquininha?")

    input("\nPressione ENTER para fazer follow-up (COM contexto)...")

    print_status()
    print("\n2️⃣ Agora vamos fazer uma pergunta de follow-up:")
    print("   Esta pergunta SÓ faz sentido se a API tiver o contexto anterior!\n")
    send_message("De quando são essas taxas que você me enviou?")

    print("\n✅ Resultado: A API respondeu corretamente porque:")
    print("   - Enviamos messages com a pergunta anterior")
    print("   - Router analisou o contexto e roteou para knowledge_agent")
    print("   - session_id foi mantido (mesmo ID)")

    input("\nPressione ENTER para RESETAR a sessão...")

    # ========== PARTE 2: Nova Sessão (Contexto Perdido) ==========
    reset_session()

    print_header("PARTE 2: Nova Sessão (SEM contexto)")
    print("Agora vamos fazer a MESMA pergunta de follow-up,")
    print("mas como session_id mudou, o histórico foi limpo.\n")

    print_status()

    input("Pressione ENTER para enviar a pergunta SEM contexto...")

    print("\n3️⃣ Fazendo a MESMA pergunta, mas agora sem contexto:")
    send_message("De quando são essas taxas que você me enviou?")

    print("\n❌ Resultado: A API NÃO conseguiu responder adequadamente porque:")
    print("   - messages está vazio (nova sessão)")
    print('   - Router não tem contexto sobre "essas taxas"')
    print("   - Pergunta não faz sentido isoladamente")
    print("   - API retorna fallback genérico")

    # ========== PARTE 3: Teste Manual ==========
    print_header("PARTE 3: Teste Interativo")
    print("Agora você controla! Digite suas perguntas.")
    print("Comandos especiais:")
    print("   'reset' - Cria nova sessão (limpa histórico)")
    print("   'status' - Mostra estado atual")
    print("   'history' - Mostra histórico completo")
    print("   'quit' - Sair\n")

    while True:
        print_status()
        question = input("\n💬 Sua pergunta: ").strip()

        if not question:
            continue

        if question.lower() == "quit":
            print("\n👋 Até logo!")
            break

        if question.lower() == "reset":
            reset_session()
            continue

        if question.lower() == "status":
            print(f"\n🆔 Session ID completo: {session_id}")
            print(f"📜 Histórico: {len(messages)} mensagens")
            for i, msg in enumerate(messages, 1):
                role_emoji = "👤" if msg["role"] == "human" else "🤖"
                content = (
                    msg["content"][:60] + "..."
                    if len(msg["content"]) > 60
                    else msg["content"]
                )
                print(f"   {i}. {role_emoji} {content}")
            continue

        if question.lower() == "history":
            import json

            print("\n📜 Histórico completo:")
            print(json.dumps(messages, indent=2, ensure_ascii=False))
            continue

        send_message(question)

    # Resumo final
    print_header("📊 RESUMO DO DEMO")
    print("O que aprendemos:")
    print("✅ messages é ESSENCIAL para contexto")
    print("✅ session_id é apenas um marcador (não guarda dados)")
    print("✅ Cliente deve gerenciar histórico localmente")
    print("✅ Mudar session_id = começar conversa nova")
    print("✅ API é stateless - não guarda nada entre requisições\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelado. Até logo!")
        sys.exit(0)
