# Docker Setup - AI Agent Swarm

## Início Rápido

### 1. Configurar Variáveis de Ambiente

Copie o arquivo de exemplo e preencha as chaves de API:

```bash
cp .env.example .env
```

Edite `.env` e adicione suas chaves:
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
NOTIFICATION_PROVIDERS=console
```

### 2. Executar com Docker Compose

```bash
# Build e iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Verificar status
curl http://localhost:8000/health
```

### 3. Testar a API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são as taxas do InfinitePay?",
    "user_id": "test_user"
  }'
```

## Serviços

### API Service (`api`)
- **Porta**: 8000
- **Healthcheck**: `/health`
- **Endpoint principal**: `POST /chat`
- **Restart**: Automático
- **Volume**: `rag_data:/code/data` (persiste base RAG)

### Ingestion Service (`ingest`)
- **Execução**: One-shot (executa uma vez e para)
- **Função**: Popula o índice FAISS com dados do InfinitePay
- **Volume**: Compartilha `rag_data` com a API
- **Restart**: Não (executa apenas no primeiro `up`)

## Comandos Úteis

### Gerenciamento de Serviços

```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados RAG)
docker-compose down -v

# Rebuild após mudanças no código
docker-compose up -d --build

# Ver logs de um serviço específico
docker-compose logs -f api
docker-compose logs ingest

# Executar comando dentro do container
docker-compose exec api bash
```

### Re-ingerir Dados

Se precisar reprocessar os dados do RAG:

```bash
# Remover volume e recriar
docker-compose down -v
docker-compose up -d

# OU executar ingestão manualmente
docker-compose run --rm ingest python scripts/ingest_data.py
```

### Debug

```bash
# Entrar no container
docker-compose exec api bash

# Verificar se dados foram ingeridos
ls -la /code/data/vector_store/

# Testar endpoint localmente dentro do container
curl http://localhost:8000/health
```

## Arquitetura

```
┌─────────────────────────────────────┐
│   docker-compose.yaml               │
│                                     │
│  ┌──────────┐      ┌─────────────┐ │
│  │  ingest  │─────▶│   rag_data  │ │
│  │ (one-shot)      │   (volume)  │ │
│  └──────────┘      └─────────────┘ │
│                           │         │
│                           ▼         │
│                    ┌──────────┐     │
│                    │   api    │     │
│                    │ (port    │     │
│                    │  8000)   │     │
│                    └──────────┘     │
└─────────────────────────────────────┘
```

**Fluxo de inicialização:**
1. `ingest` executa primeiro e popula `/code/data/vector_store/`
2. `api` aguarda `ingest` finalizar (via `depends_on`)
3. `api` carrega o índice FAISS do volume compartilhado
4. Sistema pronto para receber requisições

## Variáveis de Ambiente Importantes

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `OPENAI_API_KEY` | Sim | Chave da OpenAI para LLM e embeddings |
| `TAVILY_API_KEY` | Sim | Chave Tavily para web search |
| `NOTIFICATION_PROVIDERS` | Não | Provedores de notificação (console, slack) |
| `SLACK_WEBHOOK_URL` | Não | Webhook do Slack (se usar notificações) |
| `ENABLE_TRACING` | Não | Habilitar tracing (true/false) |
| `MOCK_GRAPH` | Não | Modo mock para desenvolvimento |

## Detalhes do Dockerfile

### Multi-stage Build

**Stage 1 (builder):**
- Instala Poetry
- Exporta `requirements.txt` do `poetry.lock`

**Stage 2 (runtime):**
- Instala apenas as dependências via pip
- Copia código fonte
- Imagem final mais leve (~300MB)

### Otimizações

- Multi-stage build (reduz tamanho da imagem)
- `.dockerignore` (exclui testes, docs, caches)
- `--no-cache-dir` (não armazena cache do pip)
- Dependências específicas (libopenblas para FAISS)

## Troubleshooting

### Erro: "Vector store not found"

O serviço `ingest` falhou ou não executou. Verifique:

```bash
# Ver logs do ingest
docker-compose logs ingest

# Re-executar ingestão
docker-compose down -v
docker-compose up -d
```

### Erro: "OpenAI API key not found"

Variável de ambiente não configurada:

```bash
# Verificar se .env existe
cat .env | grep OPENAI_API_KEY

# Recriar containers com novo .env
docker-compose down
docker-compose up -d
```

### Healthcheck falhando

```bash
# Verificar logs da API
docker-compose logs api

# Testar healthcheck manualmente
docker-compose exec api curl -f http://localhost:8000/health
```

## Segurança

- **IMPORTANTE: Nunca commite** o arquivo `.env` com chaves reais
- Use `.env.example` como template
- Em produção, use secrets management (Docker Secrets, Kubernetes Secrets)
- Configure CORS adequadamente em produção (não use `allow_origins=["*"]`)

## Monitoramento

### Healthcheck

O serviço API tem healthcheck automático:
- **Intervalo**: 30s
- **Timeout**: 5s
- **Retries**: 3

```bash
# Ver status do healthcheck
docker-compose ps
```

### Logs

```bash
# Logs em tempo real
docker-compose logs -f

# Últimas 100 linhas
docker-compose logs --tail=100

# Apenas erros
docker-compose logs | grep ERROR
```

## Produção

Para deploy em produção, considere:

1. **Secrets**: Use Docker Secrets ou variáveis de ambiente do orquestrador
2. **Volumes**: Configure backup automático do volume `rag_data`
3. **Recursos**: Defina limits de CPU/memória no docker-compose
4. **Rede**: Configure rede privada entre serviços
5. **Reverse Proxy**: Use nginx/traefik na frente da API
6. **SSL**: Configure certificados TLS

Exemplo com resource limits:

```yaml
services:
  api:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```
