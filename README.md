## Primeiro passo:
Instalar pyenv e criar um ambiente de desenvolvimento

# Implementação do Agent Swarm - Desafio InfinitePay

Este repositório contém a implementação de um sistema multi-agente (Agent Swarm) projetado para responder a consultas de usuários de forma robusta, escalável e modular. A arquitetura utiliza **LangGraph** para orquestrar o fluxo de trabalho entre agentes especializados.

## 🏛️ Arquitetura e Design

O princípio central deste projeto é a **Separação de Responsabilidades (SoC)**. Em vez de um único agente monolítico que tenta fazer tudo (o que é difícil de manter e escalar), nós criamos uma "linha de montagem" com agentes especialistas.

Nenhum agente "trabalhador" (como o `Knowledge Agent`) fala diretamente com o cliente. Ele apenas coleta dados e entrega um "relatório". Um nó final (`Synthesis Node`) é o único responsável por formular a resposta ao cliente, garantindo consistência de voz e personalidade.

### Fluxo de Trabalho (Workflow)



O fluxo de uma requisição de usuário segue 4 etapas principais:
´´
1.  **API (O "Balcão"):** Um endpoint FastAPI (`/api/v1/chat`) recebe a requisição (`message`, `user_id`). Ele é a "porta de entrada" e é responsável pela validação dos dados de entrada (definidos em `app/api/models.py`).
2.  **Roteamento (O "Gerente"):** O `router` (definido em `app/graph/router.py`) é o primeiro nó do grafo. Ele analisa a intenção do usuário e decide qual "especialista" é necessário para a tarefa (ex: "knowledge" ou "customer").
3.  **Investigação (Os "Especialistas"):** O grafo então encaminha a tarefa para o agente de trabalho apropriado:
    * **`Knowledge Agent`**: Especialista em dados *públicos*. Utiliza um pipeline de **RAG** (alimentado pelos sites da InfinitePay) e uma ferramenta de **Web Search** (Tavily) para responder perguntas sobre produtos, taxas e fatos gerais.
    * **`Customer Agent`**: Especialista em dados *privados*. Utiliza ferramentas customizadas (definidas em `app/tools/customer_tools.py`) para acessar informações simuladas da conta do cliente (status, saldo, transferências).
4.  **Síntese (O "Porta-Voz"):** Ambos os agentes investigadores NÃO formulam a resposta final. Eles apenas coletam dados brutos (seus "relatórios"). Todos os caminhos convergem para o `synthesis_node` (definido em `app/graph/synthesis_node.py`), que é o único responsável por "pintar" a resposta final com a personalidade e o tom de voz da marca.

### Por que esta arquitetura?

* **Manutenibilidade:** Se o tom de voz da marca mudar, você edita *apenas um* arquivo (`synthesis_node.py`), em vez de 3 (ou 30) agentes diferentes.
* **Escalabilidade:** Adicionar um novo agente (ex: um "Agente Financeiro") é fácil: basta criar o agente, suas ferramentas, e ensinar o `router` a encaminhar para ele. O resto do fluxo permanece intocado.
* **Testabilidade:** Cada agente ("Investigador", "Gerente", "Porta-Voz") pode ser testado de forma isolada, garantindo que cada peça da linha de montagem funcione perfeitamente.
* **Controle de Fluxo:** Evitamos a comunicação caótica "Agente-para-Agente" (A2A). O fluxo é hierárquico e controlado pelo grafo, o que previne loops infinitos e facilita o *debug*.

---

## 📁 Estrutura de Pastas

A estrutura do projeto é desenhada para reforçar a Separação de Responsabilidades:

/agent_swarm_project
|
|-- /app                    # O "cérebro": todo o código da aplicação
|   |-- /api                # Endpoints FastAPI (a "porta da frente")
|   |-- /agents             # Agentes "Investigadores" (Workers)
|   |-- /graph              # Lógica do LangGraph (o "Organograma")
|   |-- /services           # Lógica de negócios (ex: RAG)
|   |-- /tools              # Ferramentas para os agentes
|   |-- main.py             # Ponto de entrada do FastAPI (o "Anfitrião")
|
|-- /data                   # A "memória": dados (ex: vector store)
|   |-- /vector_store       # (Ignorado pelo .gitignore)
|
|-- /scripts                # Ferramentas auxiliares (ex: ingestão de dados)
|   |-- ingest_data.py      # Script para alimentar o RAG
|
|-- /tests                  # O "guardião": NOSSOS TESTES
|   |-- /api, /agents, /tools ...
|   |-- conftest.py
|
|-- .env                    # Nossas chaves secretas (API Keys)
|-- .gitignore              # O "porteiro" (ignora .env, data/, etc.)
|-- Dockerfile              # Receita para construir a imagem
|-- docker-compose.yml      # Orquestrador (para rodar fácil com Docker)
|-- pyproject.toml          # (Ou requirements.txt) Nossas dependências
|-- README.md               # O manual de instruções

´´

---

## 🧠 Pipeline de RAG (Retrieval-Augmented Generation)

Para permitir que o `Knowledge Agent` responda sobre os produtos da InfinitePay, implementamos um pipeline de RAG.

### 1. Ingestão de Dados (Offline)

* **Script:** `scripts/ingest_data.py`
* **Função:** Este script é executado *antes* de iniciar a aplicação (seja manualmente ou via Docker) para construir o banco de dados vetorial.
* **Processo:**
    1.  **Carregamento:** Utiliza o `WebBaseLoader` do LangChain para carregar o conteúdo das URLs especificadas no desafio (e.g., `https://www.infinitepay.io/maquininha`, etc.).
    2.  **Fragmentação:** Utiliza o `RecursiveCharacterTextSplitter` para quebrar as páginas em *chunks* (fragmentos) semânticos.
    3.  **Vetorização:** Utiliza `OpenAIEmbeddings` (ou outro) para converter cada *chunk* em um vetor numérico.
    4.  **Armazenamento:** Salva os vetores em um `FAISS` (ou `Chroma`) Vector Store localmente no diretório `data/vector_store/`.

### 2. Recuperação (Online)

* **Função:** Quando o `Knowledge Agent` é ativado, ele não re-lê os sites.
* **Processo:** Ele carrega o `FAISS` Vector Store já construído (de `data/vector_store/`) e o utiliza como uma ferramenta (`create_retriever_tool`). Ele converte a pergunta do usuário em um vetor e busca os *chunks* de texto mais similares para usar como contexto.

---

## 🚀 Configuração e Execução

*(Esta seção será preenchida à medida que o código for desenvolvido. Por enquanto, define o plano.)*

### 1. Configuração do Ambiente

1.  Clone este repositório:
    ```bash
    git clone [URL_DO_REPOSITORIO]
    cd agent_swarm_project
    ```
2.  Crie e popule seu arquivo de segredos (`.env`) a partir do exemplo:
    ```bash
    cp .env.example .env
    # Adicione suas chaves (OPENAI_API_KEY, TAVILY_API_KEY) ao .env
    ```
3.  Instale as dependências (recomendado usar `poetry` ou `pyenv`):
    ```bash
    poetry install
    ```

### 2. Execução (Docker - Recomendado)

Este método cuida de todas as dependências e da ingestão de dados automaticamente.

1.  Certifique-se de que o `.env` está preenchido.
2.  Construa e suba os contêineres:
    ```bash
    docker-compose up --build
    ```
    *(O `docker-compose.yml` será configurado para primeiro rodar o `ingest_data.py` antes de iniciar a API.)*

### 3. Execução (Local - Para Desenvolvimento)

1.  Execute o script de ingestão do RAG (apenas uma vez):
    ```bash
    poetry run python scripts/ingest_data.py
    ```
2.  Inicie o servidor da API com *hot-reload*:
    ```bash
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
3.  A API estará acessível em `http://localhost:8000`.

---

## 🧪 Testes

*(Esta seção será preenchida à medida que o código for desenvolvido. Por enquanto, define o plano.)*

Nossa estratégia de testes espelha a estrutura da aplicação:

* **Testes Unitários:** Focados em `app/tools` e `app/services` (ex: o `rag_service` retorna os documentos corretos?).
* **Testes de Integração:** Focados em `app/agents` (ex: o `knowledge_agent` chama a ferramenta RAG quando perguntado sobre taxas?).
* **Testes End-to-End (E2E):** Focados na API (`app/api`), simulando uma requisição `POST` completa e validando a resposta final.

Para executar todos os testes:

```bash
poetry run pytest