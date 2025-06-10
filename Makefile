.PHONY: help install-deps db-start db-stop db-clean db-restart server dev db-logs db-backup db-restore clean

help:
	@echo "Available targets:"
	@echo "  install-deps      - Install dependencies using uv"
	@echo "  db-start     - Start PostgreSQL databases"
	@echo "  db-stop      - Stop databases"
	@echo "  db-clean     - Stop databases and remove all data"
	@echo "  db-restart   - Restart databases"
	@echo "  db-logs      - Show database logs"
	@echo "  db-backup    - Create database backup (usage: make db-backup [BACKUP_NAME=name])"
	@echo "  db-restore   - Restore database from backup (usage: make db-restore BACKUP_FILE=path)"
	@echo "  server       - Start the FastAPI server"
	@echo "  dev          - Start server in development mode with auto-reload"
	@echo "  clean        - Clean up containers and volumes"
	@echo "  setup        - Full setup: install deps and start databases"

install-deps:
	uv sync --frozen
	@echo "Dependencies installed successfully"

db-start:
	docker compose up -d postgres-db 
	@echo "Waiting for databases to be ready..."
	@sleep 2
	@echo "Databases started successfully"

db-stop:
	docker compose stop postgres-db 
	@echo "Databases stopped"
	
db-clean:
	docker compose down -v
	docker volume rm study-buddy_postgres-db-volume 2>/dev/null || true
	@echo "Databases stopped and data cleaned"

db-logs:
	docker compose logs -f postgres-db

db-restart: db-stop db-start

BACKUP_NAME ?= backup_$(shell date +%Y%m%d_%H%M%S)
BACKUP_DIR := backups
POSTGRES_CONTAINER := email-agents-db

db-backup:
	@echo "Creating database backup..."
	@mkdir -p $(BACKUP_DIR)
	@if [ -z "$$(docker ps -q -f name=$(POSTGRES_CONTAINER))" ]; then \
		echo "Error: Database container is not running. Please start it with 'make db-start'"; \
		exit 1; \
	fi
	docker exec -e PGPASSWORD=$${POSTGRES_PASSWORD} $(POSTGRES_CONTAINER) pg_dump -U $${POSTGRES_USER} -d $${POSTGRES_DB} > $(BACKUP_DIR)/$(BACKUP_NAME).sql
	@echo "Backup created: $(BACKUP_DIR)/$(BACKUP_NAME).sql"

db-restore:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: Please specify BACKUP_FILE. Usage: make db-restore BACKUP_FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "Error: Backup file $(BACKUP_FILE) does not exist"; \
		exit 1; \
	fi
	@if [ -z "$$(docker ps -q -f name=$(POSTGRES_CONTAINER))" ]; then \
		echo "Error: Database container is not running. Please start it with 'make db-start'"; \
		exit 1; \
	fi
	@echo "Restoring database from $(BACKUP_FILE)..."
	@echo "Warning: This will replace all current data in the database!"
	@read -p "Are you sure you want to continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker exec -i -e PGPASSWORD=$${POSTGRES_PASSWORD} $(POSTGRES_CONTAINER) psql -U $${POSTGRES_USER} -d $${POSTGRES_DB} < $(BACKUP_FILE)
	@echo "Database restored successfully from $(BACKUP_FILE)"

server: db-start
	uv run main.py

dev: db-start
	uv run main.py --reload 

clean:
	docker compose down
	docker system prune -f

setup: install-deps db-start
	@echo "Setup complete - dependencies installed and databases started"