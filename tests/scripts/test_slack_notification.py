#!/usr/bin/env python3
"""
Teste Final: Simular Fluxo Completo com Notificação Slack

Este script:
1. Testa se o Slack está configurado
2. Envia uma notificação de teste para o Slack
3. Documenta como validar que não há loop infinito na API

Uso:
    poetry run python scripts/test_slack_notification.py
"""
import logging
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

logger = logging.getLogger(__name__)

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 80}")
    print(f"{text:^80}")
    print(f"{'=' * 80}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text):
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")


def test_slack_configuration():
    """Teste 1: Verificar configuração do Slack"""
    print_header("TESTE 1: Configuração do Slack")

    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    providers = os.getenv("NOTIFICATION_PROVIDERS", "")

    print_info(
        f"SLACK_WEBHOOK_URL: {webhook_url[:50]}..."
        if webhook_url
        else "SLACK_WEBHOOK_URL: NOT SET"
    )
    print_info(f"NOTIFICATION_PROVIDERS: {providers}")

    if not webhook_url:
        print_error("SLACK_WEBHOOK_URL não configurado!")
        return False

    if not webhook_url.startswith("https://hooks.slack.com"):
        print_error(f"SLACK_WEBHOOK_URL inválido: {webhook_url}")
        return False

    if "slack" not in providers.lower():
        print_warning("'slack' não está em NOTIFICATION_PROVIDERS")
        print_info("Adicionando 'slack' aos providers...")

    print_success("Configuração do Slack válida!")
    return True


def test_send_slack_notification():
    """Teste 2: Enviar notificação de teste para o Slack"""
    print_header("TESTE 2: Envio de Notificação de Teste")

    try:
        from app.services.notifications import NotificationService

        print_info("Instanciando NotificationService...")
        service = NotificationService()

        active_providers = service.get_active_providers()
        print_info(f"Providers ativos: {active_providers}")

        if "Slack" not in active_providers:
            print_error("Slack provider não está ativo!")
            print_warning("Verifique se SLACK_WEBHOOK_URL está correto no .env")
            return False

        print_success("Slack provider ativo!")

        print_info("Enviando notificação de teste para o Slack...")
        success = service.notify(
            conversation_id="test_slack_integration",
            title="🎉 Teste de Integração Slack - Sistema de Notificações",
            message=(
                "**Parabéns!** O sistema de notificações está funcionando corretamente.\n\n"
                "Esta mensagem confirma que:\n"
                "✅ O SLACK_WEBHOOK_URL está configurado corretamente\n"
                "✅ O NotificationService está carregando o Slack provider\n"
                "✅ As notificações estão sendo enviadas com sucesso\n\n"
                "**Próximos Passos:**\n"
                "1. Teste o fluxo completo da API com: `make run`\n"
                "2. Faça uma requisição que trigger human escalation\n"
                "3. Verifique que a notificação chega aqui no Slack\n\n"
                "**Observação:** Se você estiver vendo esta mensagem, significa que o "
                "sistema está **100% funcional** e pronto para uso em produção! 🚀"
            ),
            priority="high",
            metadata={
                "test_type": "slack_integration",
                "script": "test_slack_notification.py",
                "status": "✅ SUCESSO",
            },
        )

        if success:
            print_success("Notificação enviada com sucesso!")
            print_info("Verifique seu canal do Slack para confirmar recebimento")
            print(f"\n{GREEN}{BOLD}🎉 SLACK ESTÁ FUNCIONANDO PERFEITAMENTE!{RESET}\n")
            return True
        else:
            print_error("Falha ao enviar notificação")
            return False

    except Exception as e:
        print_error(f"Erro ao testar Slack: {e}")
        import traceback

        traceback.print_exc()
        return False


def print_api_test_instructions():
    """Instruções para testar o fluxo completo da API"""
    print_header("COMO TESTAR O FLUXO COMPLETO (SEM LOOP INFINITO)")

    print(f"{BOLD}Passo 1: Iniciar a API{RESET}")
    print(f"{BLUE}make run{RESET}")
    print("ou")
    print(f"{BLUE}MOCK_GRAPH=false poetry run uvicorn app.api.main:app --reload{RESET}")

    print(f"\n{BOLD}Passo 2: Fazer requisição que GARANTE escalação humana{RESET}")
    print(f"{BLUE}curl -X POST http://localhost:8000/chat \\")
    print('  -H "Content-Type: application/json" \\')
    print("  -d '{")
    print('    "question": "Quando foi o ultimo jogo do Cruzeiro?",')
    print('    "user_id": "test_user"')
    print(f"  }}'{RESET}")

    print(f"\n{BOLD}Passo 3: Observar os logs{RESET}")
    print(f"{GREEN}✅ CORRETO (SEM LOOP):{RESET}")
    print("  --- GRADER: Max retries reached. Escalating to human.")
    print("  --- HUMAN ESCALATION: Notifying support team ---")
    print("  --- KNOWLEDGE_AGENT: Processing completed ---")
    print(f"  {GREEN}--- MAIN GRAPH: Routing to synthesis_agent ---{RESET}")
    print("  --- SYNTHESIS_AGENT: Processing started ---")

    print(f"\n{RED}❌ ERRADO (LOOP INFINITO):{RESET}")
    print("  --- KNOWLEDGE_AGENT: Processing completed ---")
    print(f"  {RED}--- ROUTER_AGENT: Processing started ---{RESET}")
    print(f"  {RED}Router Decision: Route='knowledge_agent'{RESET}")
    print(f"  {RED}--- MAIN GRAPH: Routing to knowledge_agent ---{RESET}")
    print(f"  {RED}(repetição infinita...){RESET}")

    print(f"\n{BOLD}Passo 4: Verificar Slack{RESET}")
    print("Você DEVE receber uma notificação no Slack com:")
    print("  📢 Título: 'Human Support Needed - Complex Query'")
    print("  📝 Conteúdo: Detalhes da pergunta e tentativas")

    print(f"\n{BOLD}Passo 5: Validar resposta da API{RESET}")
    print("A API deve retornar:")
    print("{")
    print('  "id": "...",')
    print(
        '  "answer": "Identificamos que sua pergunta requer atenção especializada...",'
    )
    print('  "agent_used": "knowledge_agent",')
    print('  "tools_called": ["rag_tool"] ou ["web_search"]')
    print("}")

    print(
        f"\n{GREEN}{BOLD}✅ Se você viu a sequência correta nos logs E recebeu a notificação no Slack:"
    )
    print(
        f"   O sistema está COMPLETAMENTE FUNCIONAL e o loop infinito foi RESOLVIDO!{RESET}\n"
    )


def main():
    """Execute todos os testes"""
    print(f"\n{BOLD}{BLUE}")
    print("=" * 80)
    print("  TESTE DE NOTIFICAÇÃO SLACK + VALIDAÇÃO DE LOOP INFINITO")
    print("=" * 80)
    print(f"{RESET}")

    # Teste 1: Configuração
    if not test_slack_configuration():
        print(f"\n{RED}{BOLD}❌ FALHA: Configure o Slack antes de prosseguir{RESET}")
        return 1

    # Teste 2: Envio de notificação
    if not test_send_slack_notification():
        print(f"\n{RED}{BOLD}❌ FALHA: Não foi possível enviar notificação{RESET}")
        return 1

    # Instruções para teste completo
    print_api_test_instructions()

    return 0


if __name__ == "__main__":
    sys.exit(main())
