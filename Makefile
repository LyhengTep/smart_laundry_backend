COMPOSE=docker compose
SERVICE=postgres
VENV=./venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
FAST=$(VENV)/bin/fastapi
ALEMBIC=$(VENV)/bin/alembic

PYTEST=$(VENV)/bin/pytest

PYTHONPATH=.

.PHONY: up down restart logs ps clean migrate migrate-db downgrade revision

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) down
	$(COMPOSE) up -d

logs:
	$(COMPOSE) logs -f $(SERVICE)

ps:
	$(COMPOSE) ps

clean:
	$(COMPOSE) down -v

run: 
	$(FAST) dev app/main.py

backup: 
	docker exec -t postgres-db pg_dumpall -U app_user > init/backup.sql

test: 
	$(PYTEST) 

migrate-db:
	$(ALEMBIC) upgrade head

downgrade:
	$(ALEMBIC) downgrade -1

revision:
	$(ALEMBIC) revision --autogenerate -m "$(m)"
