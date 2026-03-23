# Tudio V2 - Makefile
# Orchestrates backend (Python) and frontend (Vue/Vite) tasks.

PYTHON := .venv/bin/python
NPM := npm
PORT := 8000
PID_FILE := tudio_pid.txt

.PHONY: help install test test-unit test-int test-e2e build start stop clean

help:
	@echo "Tudio V2 - Command Center"
	@echo "Usage:"
	@echo "  make install      Install all dependencies"
	@echo "  make test         Run all tests (unit + integration + e2e)"
	@echo "  make test-unit    Run backend and frontend unit tests"
	@echo "  make test-int     Run backend integration tests"
	@echo "  make test-e2e     Run Playwright E2E tests"
	@echo "  make build        Build the frontend"
	@echo "  make start        Start the server (Foreground + Logs)"
	@echo "  make start-bg     Start the server in Background"
	@echo "  make stop         Stop the background server"
	@echo "  make clean        Clean build artifacts and caches"

install:
	@echo "Installing backend dependencies..."
	$(PYTHON) -m pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && $(NPM) install

test: test-unit test-int test-e2e

test-unit:
	@echo "Running Backend Unit Tests..."
	PYTHONPATH=. $(PYTHON) -m pytest backend/tests/unit --cov=backend --cov-report=term-missing --cov-fail-under=70
	@echo "Running Frontend Unit Tests..."
	cd frontend && $(NPM) run test:unit

test-int:
	@echo "Running Backend Integration Tests..."
	PYTHONPATH=. $(PYTHON) -m pytest backend/tests/integration --cov=backend --cov-append --cov-report=term-missing --cov-fail-under=80

test-e2e:
	@echo "Running E2E Tests (Playwright)..."
	cd frontend && npx playwright test --workers=1

build:
	@echo "Building Frontend..."
	cd frontend && rm -rf dist && $(NPM) run build

start:
	@echo "Starting Uvicorn Server on port $(PORT) (Foreground)..."
	@export BYPASS_RATE_LIMIT=True && \
	$(PYTHON) -m uvicorn backend.main:app --host 0.0.0.0 --port $(PORT) --reload

start-bg:
	@echo "Starting Uvicorn Server on port $(PORT) (Background)..."
	@if [ -f "$(PID_FILE)" ]; then \
		OLD_PID=$$(cat $(PID_FILE)); \
		if ps -p $$OLD_PID > /dev/null; then \
			echo "ALREADY RUNNING (PID $$OLD_PID)"; exit 1; \
		else \
			rm $(PID_FILE); \
		fi; \
	fi
	@export BYPASS_RATE_LIMIT=True && \
	nohup $(PYTHON) -m uvicorn backend.main:app --host 0.0.0.0 --port $(PORT) --reload > storage/logs/server.out 2>&1 & \
	echo $$! > $(PID_FILE)
	@echo "Started in background with PID $$(cat $(PID_FILE))"
	@echo "Docs: http://localhost:$(PORT)/doc"

stop:
	@if [ -f "$(PID_FILE)" ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null; then \
			echo "Stopping PID $$PID via PID file..."; \
			kill $$PID && rm $(PID_FILE) || echo "Failed to kill process $$PID."; \
		else \
			echo "Stale PID file found. Cleaning up..."; \
			rm $(PID_FILE); \
		fi; \
	fi
	@echo "Checking for remaining processes on port $(PORT)..."
	@PORT_PIDS=$$(lsof -ti :$(PORT) 2>/dev/null); \
	if [ -n "$$PORT_PIDS" ]; then \
		echo "Found rogue processes on port $(PORT): $$PORT_PIDS. Killing them aggressively..."; \
		kill -9 $$PORT_PIDS || echo "Failed to kill processes on port $(PORT)."; \
	else \
		echo "Port $(PORT) is clear."; \
	fi

clean:
	rm -rf frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
