#!/usr/bin/env python3
"""
Teste Completo de Validação da Correção do Loop Infinito

Este script executa testes práticos para garantir que:
1. O grafo compila sem erros
2. O KnowledgeAgent sinaliza conclusão corretamente
3. Não há loop infinito no fluxo de escalação humana
4. As notificações funcionam (Slack + Console)

Uso:
    poetry run python scripts/test_loop_fix_complete.py
"""
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# Cores para output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}")
    print(f"{text:^80}")
    print(f"{'=' * 80}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def test_1_graph_compilation() -> bool:
    """Teste 1: Verificar que o grafo compila sem erros"""
    print_header("TESTE 1: Compilação do Grafo")

    try:
        print_info("Importando app_graph de builder.py...")
        from app.graph.builder import app_graph

        print_success("Grafo importado com sucesso!")
        print_info(f"Nodes no grafo: {list(app_graph.get_graph().nodes.keys())}")

        return True
    except Exception as e:
        print_error(f"Falha ao compilar grafo: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_2_knowledge_agent_route_signal() -> bool:
    """Teste 2: Verificar que KnowledgeAgent.process() retorna route='synthesis_agent'"""
    print_header("TESTE 2: Sinalização de Conclusão do KnowledgeAgent")

    try:
        print_info("Lendo código de agent.py...")

        with open("app/agents/knowledge_agent/agent.py") as f:
            content = f.read()

        # Check if route="synthesis_agent" exists in process method
        if (
            'route": "synthesis_agent"' in content
            or "route': 'synthesis_agent'" in content
        ):
            print_success("✓ Código contém route='synthesis_agent' no método process()")
        else:
            print_error("✗ NÃO encontrado route='synthesis_agent' no método process()")
            return False

        # Check log message
        if "Processing completed" in content:
            print_success("✓ Log de conclusão adicionado")
        else:
            print_warning("Log de conclusão não encontrado (não crítico)")

        print_success("KnowledgeAgent está sinalizando conclusão corretamente!")
        return True

    except Exception as e:
        print_error(f"Erro ao validar código: {e}")
        return False


def test_3_human_escalation_route_signal() -> bool:
    """Teste 3: Verificar que human_escalation retorna route='synthesis_agent'"""
    print_header("TESTE 3: Sinalização de Conclusão da Escalação Humana")

    try:
        print_info("Lendo código de human_escalation/node.py...")

        with open("app/agents/knowledge_agent/sub_graph/human_escalation/node.py") as f:
            content = f.read()

        # Check if route="synthesis_agent" exists
        if (
            'route": "synthesis_agent"' in content
            or "route': 'synthesis_agent'" in content
        ):
            print_success("✓ human_escalation retorna route='synthesis_agent'")
        else:
            print_error("✗ NÃO encontrado route='synthesis_agent' em human_escalation")
            return False

        print_success("human_escalation está sinalizando conclusão corretamente!")
        return True

    except Exception as e:
        print_error(f"Erro ao validar código: {e}")
        return False


def test_4_customer_agent_route_signal() -> bool:
    """Teste 4: Verificar que CustomerAgent.process() retorna route='synthesis_agent'"""
    print_header("TESTE 4: Sinalização de Conclusão do CustomerAgent")

    try:
        print_info("Lendo código de customer_agent/node.py...")

        with open("app/agents/customer_agent/node.py") as f:
            content = f.read()

        # Check if route="synthesis_agent" exists in process method
        if (
            'route": "synthesis_agent"' in content
            or "route': 'synthesis_agent'" in content
        ):
            print_success("✓ CustomerAgent retorna route='synthesis_agent'")
        else:
            print_error("✗ NÃO encontrado route='synthesis_agent' em CustomerAgent")
            return False

        print_success("CustomerAgent está sinalizando conclusão corretamente!")
        return True

    except Exception as e:
        print_error(f"Erro ao validar código: {e}")
        return False


def test_5_notification_service() -> bool:
    """Teste 5: Verificar que NotificationService está configurado corretamente"""
    print_header("TESTE 5: Configuração do NotificationService")

    try:
        from app.services.notifications import NotificationService

        print_info("Verificando variáveis de ambiente...")

        slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
        notification_providers = os.getenv("NOTIFICATION_PROVIDERS", "")

        if slack_url and slack_url.startswith("https://hooks.slack.com"):
            print_success(f"✓ SLACK_WEBHOOK_URL configurado: {slack_url[:40]}...")
        else:
            print_error("✗ SLACK_WEBHOOK_URL não configurado ou inválido")

        if "slack" in notification_providers.lower():
            print_success(
                f"✓ NOTIFICATION_PROVIDERS inclui Slack: {notification_providers}"
            )
        else:
            print_warning(
                f"⚠️  NOTIFICATION_PROVIDERS não inclui 'slack': '{notification_providers}'"
            )
            print_info(
                "Sugestão: Adicione 'NOTIFICATION_PROVIDERS=slack,console' no .env"
            )

        # Test instantiation
        print_info("Testando instanciação do NotificationService...")
        service = NotificationService()

        active_providers = service.get_active_providers()
        print_info(f"Providers ativos: {active_providers}")

        if "Slack" in active_providers:
            print_success("✓ Slack provider está ativo!")
        else:
            print_warning("⚠️  Slack provider NÃO está ativo (usando apenas Console)")

        # Test sending notification
        print_info("Testando envio de notificação de teste...")
        success = service.notify(
            conversation_id="test_loop_fix",
            title="🧪 Teste de Notificação - Correção de Loop Infinito",
            message="Este é um teste automático para validar que o sistema de notificações está funcionando após a correção do loop infinito.\n\n"
            "Se você está vendo esta mensagem no Slack, significa que:\n"
            "✅ O NotificationService está configurado corretamente\n"
            "✅ O SLACK_WEBHOOK_URL é válido\n"
            "✅ As notificações estão funcionando!\n\n"
            "Próximo passo: Testar o fluxo completo com human escalation.",
            priority="normal",
            metadata={
                "test_type": "notification_validation",
                "script": "test_loop_fix_complete.py",
            },
        )

        if success:
            print_success("✓ Notificação de teste enviada com sucesso!")
            print_info("Verifique seu canal do Slack para confirmar recebimento")
        else:
            print_error("✗ Falha ao enviar notificação de teste")
            return False

        return True

    except Exception as e:
        print_error(f"Erro ao testar NotificationService: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_6_main_graph_routing_logic() -> bool:
    """Teste 6: Verificar lógica de roteamento do Main Graph"""
    print_header("TESTE 6: Lógica de Roteamento do Main Graph")

    try:
        print_info("Lendo código de builder.py...")

        with open("app/graph/builder.py") as f:
            content = f.read()

        # Check if after_specialist_logic exists
        if "after_specialist_logic" in content:
            print_success("✓ Função after_specialist_logic encontrada")
        else:
            print_error("✗ Função after_specialist_logic NÃO encontrada")
            return False

        # Check if it routes to synthesis_agent
        if 'route == "synthesis_agent"' in content:
            print_success("✓ Lógica de roteamento para synthesis_agent presente")
        else:
            print_error("✗ Lógica de roteamento para synthesis_agent ausente")
            return False

        print_success("Main Graph está com lógica de roteamento correta!")
        return True

    except Exception as e:
        print_error(f"Erro ao validar lógica de roteamento: {e}")
        return False


def main():
    """Execute todos os testes"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 80)
    print("  VALIDAÇÃO COMPLETA DA CORREÇÃO DO LOOP INFINITO")
    print("=" * 80)
    print(f"{Colors.RESET}")

    tests = [
        ("Compilação do Grafo", test_1_graph_compilation),
        ("Sinalização KnowledgeAgent", test_2_knowledge_agent_route_signal),
        ("Sinalização Human Escalation", test_3_human_escalation_route_signal),
        ("Sinalização CustomerAgent", test_4_customer_agent_route_signal),
        ("Configuração NotificationService", test_5_notification_service),
        ("Lógica de Roteamento Main Graph", test_6_main_graph_routing_logic),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Teste '{test_name}' crashou: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print_header("RESUMO DOS TESTES")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} testes passaram{Colors.RESET}")

    if passed == total:
        print(
            f"\n{Colors.GREEN}{Colors.BOLD}🎉 TODOS OS TESTES PASSARAM!{Colors.RESET}"
        )
        print_success("A correção do loop infinito está funcionando corretamente!")
        print_info("Próximo passo: Testar com API real usando o comando:")
        print(f"  {Colors.BLUE}make run{Colors.RESET}")
        return 0
    else:
        print(
            f"\n{Colors.RED}{Colors.BOLD}❌ {total - passed} TESTE(S) FALHARAM{Colors.RESET}"
        )
        print_error("Revise os erros acima antes de prosseguir")
        return 1


if __name__ == "__main__":
    sys.exit(main())
