COMPOSE=docker compose
SERVICE=postgres
VENV=./venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
FAST=$(VENV)/bin/fastapi

PYTEST=$(VENV)/bin/pytest

PYTHONPATH=.

.PHONY: up down restart logs ps clean

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

test: 
	$(PYTEST) 

