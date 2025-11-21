SHELL := /bin/bash
.PHONY: help install test run mock-chat chat lint format docker-build up ingest clean
.PHONY: setup-pre-commit precommit-all

help:
	@echo "Makefile targets:"
	@echo "  install     - Instala dependências via Poetry"
	@echo "  run         - Roda a API local com uvicorn"
	@echo "  mock-chat   - Chama o CLI local em modo --mock"
	@echo "  chat        - Chama o CLI local (usa chaves do ambiente)"
	@echo "  test        - Executa a suíte de testes (pytest)"
	@echo "  lint        - Checa lint/format (ruff + black)"
	@echo "  format      - Formata o código (ruff + black)"
	@echo "  docker-build- Constrói a imagem Docker local"
	@echo "  up          - Sobe os serviços via docker-compose"
	@echo "  ingest      - Executa o script de ingestão de dados RAG"
	@echo "  clean       - Remove caches locais"

install:

setup-pre-commit:
	poetry run pre-commit install || (echo "pre-commit install failed; run 'poetry run pre-commit install' manually" && exit 1)

precommit-all:
	poetry run pre-commit run --all-files
	poetry install

test:
	poetry run pytest -q

run:
	poetry run uvicorn app.api.main:app --reload

mock-chat:
	poetry run python scripts/chat_local.py -m "Olá, posso testar o grafo localmente?" --mock

chat:
	poetry run python scripts/chat_local.py -m "Como funcionam as taxas da maquininha?"

lint:
	poetry run ruff check . || true
	poetry run black --check . || true

format:
	poetry run ruff format .
	poetry run black .

docker-build:
	docker build -t ai-agent-swarm:local .

up:
	docker-compose up --build

ingest:
	poetry run python scripts/ingest_data.py

clean:
	rm -rf .pytest_cache __pycache__ .mypy_cache .venv build dist
