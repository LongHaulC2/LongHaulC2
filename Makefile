SHELL := /bin/bash

.DEFAULT_GOAL := help

# deploy options
PREFIX ?= /opt
DEPLOY_DIR = $(PREFIX)/longhaulc2
SVC_USER = longhaul
DOCKER_DIR := setup/docker_images
WORKSPACE_DIR = /var/lib/longhaulc2
KEEP_DATA ?= 0
GEN_PASSWORDS ?= 0


# dev vars
DIR_OF_THIS_SCRIPT := $(shell pwd)
DEV_VENV := $(DIR_OF_THIS_SCRIPT)/venv
DEV_VENV_PATH ?= /venv

# Dependencies
APT_PACKAGES = python3 python3-pip python3-virtualenv docker.io docker-compose-v2 redis-tools postgresql-client clang-format
SYSTEMD_SERVICES = longhaulc2-server longhaulc2-web

# Minimal packages for hosted runnersm tldr, they already have docker installed
GH_RUNNER_PACKAGES = python3-virtualenv docker-compose-v2 redis-tools postgresql-client clang-format

# python shennanigans
# where the pip deps lock file is stored, this is in the longhaulc2 dir at pull
LOCK_FILE := $(DIR_OF_THIS_SCRIPT)/requirements.lock

# Docker Container Names
MYSQL_CONTAINER = C2_mysql
REDIS_CONTAINER = C2_redis-stack
NEO4J_CONTAINER = C2_neo4j-stack

# creds
MYSQL_HOST ?= localhost
MYSQL_PORT ?= 3306
MYSQL_ROOT_PASSWORD ?= P@ssw0rd1!
MYSQL_ROOT_USER ?= root
REDIS_HOST ?= localhost
REDIS_PORT ?= 6379
REDIS_USER ?= default
REDIS_PASSWORD ?= P@ssw0rd1!
NEO4J_HOST ?= localhost
NEO4J_WEB_PORT ?= 7474
NEO4J_DB_PORT ?= 7687
NEO4J_USER ?= neo4j
NEO4J_PASSWORD ?= P@ssw0rd1!
JWT_SECRET_KEY ?= P@ssw0rd1!
INIT_API_USER ?= longhaul
INIT_API_PASS ?= P@ssw0rd1!

# Certs
CERT_DIR := /etc/ssl/certs/
CERT_FILE := $(CERT_DIR)/longhaulc2_api_cert.pem
KEY_FILE := $(CERT_DIR)/longhaulc2_api_key.pem
UI_CERT_FILE := $(CERT_DIR)/longhaulc2_ui_cert.pem
UI_KEY_FILE := $(CERT_DIR)/longhaulc2_ui_key.pem
DAYS := 365

# ======================================
# Gum Helpers
# ======================================

GUM_BORDER = gum style --bold --border rounded --border-foreground "\#a16ae8" --padding "0 2"
GUM_BORDER_SUCCESS = gum style --bold --border double --border-foreground "\#10b981" --padding "0 2"
GUM_BORDER_DANGER = gum style --bold --border rounded --border-foreground "\#ef4444" --padding "0 2"
GUM_SPIN = gum spin --show-error --spinner dot --spinner.foreground "\#10b981"

# ======================================
# Helpers
# ======================================

## check_root: Verify running as root
.PHONY: check_root
check_root:
	@if [ "$$(id -u)" -ne 0 ]; then \
		gum style --bold --border rounded --border-foreground "#ef4444" --padding "0 2" \
			"Error: This target must be run with superuser privileges (e.g. sudo make $$@)"; \
		exit 1; \
	fi

## install_gum: Install gum (Charm.sh) CLI
.PHONY: install_gum
install_gum:
	@echo "Installing gum (Charm.sh)..."
	@sudo mkdir -p /etc/apt/keyrings
	@curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/charm.gpg
	@echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list >/dev/null
	@sudo apt update -qq && sudo apt install gum -y -qq
	@gum style --bold --border rounded --border-foreground "#a16ae8" --padding "0 2" "gum installed successfully"

## clean_for_release: Remove dev artifacts for release packaging
.PHONY: clean_for_release
clean_for_release:
	@$(GUM_BORDER) "Cleaning project for release"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Removing dev artifacts..." -- \
		bash -c '\
			sudo rm -rf ./.claude && \
			sudo rm -rf ./.hypothesis && \
			sudo rm -rf ./.nicegui && \
			sudo rm -rf ./.pytest_cache && \
			sudo rm -rf ./.ruff_cache && \
			sudo rm -rf ./.venv && \
			sudo rm -rf ./.vscode && \
			sudo rm -rf ./development && \
			sudo rm -rf ./CLAUDE.md'
	@gum log --level info "Release cleanup complete"


# ======================================
# Production Deployment
# ======================================

## deploy: Full production deployment (requires root)
.PHONY: deploy
deploy: check_root install_gum
	@$(GUM_BORDER) "Starting LongHaulC2 Enterprise Deployment..."

	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Updating apt packages..." -- \
		sudo apt-get update -y -qq
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Installing dependencies..." -- \
		sudo apt-get install -y -qq $(APT_PACKAGES)

	# immediately setup cert stuff to make sure it exists
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Setting up certificate prerequisites..." -- \
		$(MAKE) cert_prereqs

	@gum log --level info "Dependencies installed, continuing with deployment..."

	@$(GUM_BORDER) "Creating longhaul user"
	@id -u $(SVC_USER) >/dev/null 2>&1 || useradd --system --no-create-home --shell /bin/false $(SVC_USER)
	@sudo getent group docker || groupadd docker
	@sudo usermod -aG docker $(SVC_USER)

	@$(GUM_BORDER) "Creating .env"
	@if [ -f .env ]; then \
		gum log --level info ".env already exists — keeping existing credentials"; \
	else \
		$(MAKE) create_env GEN_PASSWORDS=1; \
	fi

	@$(GUM_BORDER) "Creating directories"
	@mkdir -p $(DEPLOY_DIR)/server
	@mkdir -p $(DEPLOY_DIR)/client
	@mkdir -p $(DEPLOY_DIR)/server/venv
	@mkdir -p $(DEPLOY_DIR)/client/venv
	@mkdir -p $(WORKSPACE_DIR)
	@mkdir -p $(WORKSPACE_DIR)/implant_templates
	@cp -r ./implant_templates/. $(WORKSPACE_DIR)/implant_templates
	@mkdir -p /var/log/longhaulc2
	@cp -r ./client/user/. $(WORKSPACE_DIR)

	@$(GUM_BORDER) "Copying files"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Copying server files..." -- \
		bash -c 'cp -r server/* $(DEPLOY_DIR)/server/ && cp -r client/* $(DEPLOY_DIR)/client/ && cp -r .env $(DEPLOY_DIR)/'

	@$(GUM_BORDER) "Creating virtualenv"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Creating server virtualenv..." -- \
		virtualenv $(DEPLOY_DIR)/server/venv/
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Installing server dependencies..." -- \
		$(DEPLOY_DIR)/server/venv/bin/pip install -r $(LOCK_FILE) -q
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Creating client virtualenv..." -- \
		virtualenv $(DEPLOY_DIR)/client/venv/
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Installing client dependencies..." -- \
		$(DEPLOY_DIR)/client/venv/bin/pip install -r $(LOCK_FILE) -q

	@$(GUM_BORDER) "Setting permissions"
	@chown -R root:$(SVC_USER) $(DEPLOY_DIR)
	@chmod -R 750 $(DEPLOY_DIR)
	@chown -R $(SVC_USER):$(SVC_USER) /var/lib/longhaulc2
	@chown -R $(SVC_USER):$(SVC_USER) /var/log/longhaulc2
	@sudo chown -R longhaul:longhaul /opt/longhaulc2/

	@$(GUM_BORDER) "Creating certificates"
	@$(MAKE) certs

	@$(GUM_BORDER) "Setting up services"
	@sed -e 's|@DEPLOY_DIR@|$(DEPLOY_DIR)|g' ./setup/longhaulc2-server.service.in > /etc/systemd/system/longhaulc2-server.service
	@sed -e 's|@DEPLOY_DIR@|$(DEPLOY_DIR)|g' ./setup/longhaulc2-web.service.in > /etc/systemd/system/longhaulc2-web.service
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Reloading systemd..." -- \
		systemctl daemon-reload
	@systemctl enable longhaulc2-server
	@systemctl enable longhaulc2-web

	@$(GUM_BORDER) "Setting up docker containers"
	@$(MAKE) start_docker_images
	@$(MAKE) create_docker_images

	@$(MAKE) print_all_install_locations
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Starting services..." -- \
		bash -c 'sudo systemctl start longhaulc2-server && sudo systemctl start longhaulc2-web'

	@$(GUM_BORDER_SUCCESS) "Deployment complete."
	@echo ""
	@gum style --bold --border rounded --border-foreground "#a16ae8" --padding "1 2" \
		"Initial operator credentials:" \
		"" \
		"  Username: $$(grep '^INIT_API_USER=' .env | cut -d= -f2)" \
		"  Password: $$(grep '^INIT_API_PASS=' .env | cut -d= -f2)" \
		"" \
		"  Save these credentials — they will not be shown again." \
		"  All service passwords are stored in .env"

## undeploy: Uninstall production deployment (requires root)
.PHONY: undeploy
undeploy: check_root
	@gum confirm "Are you sure you want to uninstall LongHaulC2?" || exit 1

	@$(GUM_BORDER_DANGER) "Starting LongHaulC2 Enterprise Uninstall..."

	@$(GUM_BORDER) "Stopping and removing systemd services"
	-@systemctl stop $(word 1, $(SYSTEMD_SERVICES)) $(word 2, $(SYSTEMD_SERVICES))
	-@systemctl disable $(word 1, $(SYSTEMD_SERVICES)) $(word 2, $(SYSTEMD_SERVICES))
	@rm -f /etc/systemd/system/$(word 1, $(SYSTEMD_SERVICES)).service
	@rm -f /etc/systemd/system/$(word 2, $(SYSTEMD_SERVICES)).service
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Reloading systemd..." -- \
		systemctl daemon-reload

	@$(MAKE) clean-certs

	@$(GUM_BORDER) "Stopping and removing Docker containers"
ifeq ($(KEEP_DATA),1)
	@gum log --level warn "KEEP_DATA=1 — preserving Docker volumes and workspace data"
	-@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Stopping docker containers..." -- \
		docker compose down
else
	-@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Stopping docker containers and removing volumes..." -- \
		docker compose down -v
endif

	@$(GUM_BORDER) "Removing installed directories and files"
	@rm -rf $(DEPLOY_DIR)
ifneq ($(KEEP_DATA),1)
	@rm -rf /var/lib/longhaulc2
	@rm -f .env
endif
	@rm -rf /var/log/longhaulc2
	@rm -f install_reference

	@$(GUM_BORDER) "Removing system user"
	-@userdel $(SVC_USER)

	@$(GUM_BORDER_SUCCESS) "Uninstall complete!"
	@gum log --level warn "APT packages ($(APT_PACKAGES)) and Docker base images were NOT removed to prevent breaking other tools on your system."

## redeploy: Undeploy then deploy (preserves data)
.PHONY: redeploy
redeploy:
	@$(MAKE) undeploy KEEP_DATA=1
	@$(MAKE) deploy
	@$(GUM_BORDER_SUCCESS) "Re-Deploying LongHaulC2 Complete (data preserved)"

# ======================================
# Development Install
# ======================================

## dev_install: Set up local development environment
.PHONY: dev_install
dev_install: install_gum
	@$(GUM_BORDER) "Starting LongHaulC2 Development Install..."

	@$(GUM_BORDER) "Installing required dependencies"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Updating apt packages..." -- \
		sudo apt-get update -qq
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Installing dependencies..." -- \
		sudo apt-get install $(APT_PACKAGES) -y -qq

	@$(GUM_BORDER) "Creating virtualenv @ $(DEV_VENV_PATH)"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Creating virtualenv..." -- \
		virtualenv $(DEV_VENV)

	# If CI testing, don't use the lock. let the resolver find the package version it needs for that specific env.
ifdef CI
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Installing Python dependencies (CI)..." -- \
		$(DEV_VENV)/bin/pip install -e ".[server,web,dev]" -q
else
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Installing Python dependencies..." -- \
		$(DEV_VENV)/bin/pip install -e ".[server,web,dev]" -c $(LOCK_FILE) -q
endif

	@$(GUM_BORDER) "Creating .env"
	@$(MAKE) create_env

	@$(GUM_BORDER) "Creating workspace dirs"
	@sudo mkdir -p $(WORKSPACE_DIR)
	@sudo mkdir -p $(WORKSPACE_DIR)/implant_templates
	@sudo chown -R $(USER):$(USER) $(WORKSPACE_DIR)
	@cp -r ./client/user/. $(WORKSPACE_DIR)
	@cp -r ./implant_templates/. $(WORKSPACE_DIR)/implant_templates

	@$(GUM_BORDER) "Creating log dirs"
	@sudo mkdir -p /var/log/longhaulc2/
	@sudo mkdir -p /var/log/longhaulc2/web/
	@sudo mkdir -p /var/log/longhaulc2/server/
	@sudo chmod -R 777 /var/log/longhaulc2

	@$(GUM_BORDER) "Setting up docker containers"
	@sudo getent group docker || groupadd docker
	@$(MAKE) start_docker_images
	@$(MAKE) create_docker_images

	@$(GUM_BORDER_SUCCESS) "Development env setup & ready to go"
	@gum log --level info "Activate the venv with 'source $(DEV_VENV_PATH)/bin/activate'"

## dev_uninstall: Remove local development environment
.PHONY: dev_uninstall
dev_uninstall:
	@$(GUM_BORDER_DANGER) "Uninstalling Development Environment..."

	@$(GUM_BORDER) "Stopping & removing docker containers"
	-@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Stopping docker containers..." -- \
		docker compose down

	@$(GUM_BORDER) "Removing virtualenv and configurations"
	@rm -rf $(DEV_VENV_PATH)
	-@rm -f .env
	@sudo rm -rf /var/lib/longhaulc2
	@sudo rm -rf /var/log/longhaulc2
	@gum log --level info "Development environment removed"

## dev_reinstall: Nuke and rebuild dev environment
.PHONY: dev_reinstall
dev_reinstall: dev_uninstall dev_install
	@$(GUM_BORDER_SUCCESS) "Everything Reset!"

# ======================================
# Docker Utilities
# ======================================

## create_docker_images: Build local docker images from setup/docker_images/
.PHONY: create_docker_images
create_docker_images:
	@sudo getent group docker >/dev/null || sudo groupadd docker
	@sudo usermod -aG docker "$(USER)"
	@gum log --level info "Log out and back in (or run: newgrp docker) for changes to take effect."

	@$(GUM_BORDER) "Creating local docker images"
	@for d in $(DOCKER_DIR)/*; do \
		if [ -d "$$d" ]; then \
			img_name=$$(basename $$d); \
			gum style --bold --border rounded --border-foreground "#a16ae8" --padding "0 2" "Building $$img_name from $$d"; \
			gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Building $$img_name..." -- \
				sudo docker build --pull --no-cache -t $$img_name:latest $$d; \
		fi \
	done

## start_docker_images: Start service containers via docker compose
.PHONY: start_docker_images
start_docker_images:
	@$(GUM_BORDER) "Starting docker containers via compose..."
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Starting containers..." -- \
		docker compose up -d

## stop_docker_images: Stop service containers
.PHONY: stop_docker_images
stop_docker_images:
	@$(GUM_BORDER) "Stopping docker containers..."
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Stopping containers..." -- \
		docker compose down

## pull_docker_images: Pull latest docker compose images
.PHONY: pull_docker_images
pull_docker_images:
	@$(GUM_BORDER) "Pulling docker images..."
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Pulling images..." -- \
		docker compose pull

# ======================================
# Certs
# ======================================
.PHONY cert_prereqs: cert_prereqs
cert_prereqs:
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Reinstalling CA certificates..." -- \
		sudo apt-get install -y -qq --reinstall ca-certificates
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Updating CA certificates..." -- \
		sudo update-ca-certificates

## certs: Generate self-signed TLS certificates
.PHONY: certs
certs:
	@$(GUM_BORDER) "Creating Certificates"
	@mkdir -p $(CERT_DIR)
	@if [ ! -f $(CERT_FILE) ]; then \
		gum log --level info "Generating API self-signed certificates..."; \
		gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Generating API certificates..." -- \
			openssl req -x509 -newkey rsa:4096 -nodes \
				-keyout $(KEY_FILE) \
				-out $(CERT_FILE) \
				-days $(DAYS) \
				-subj "/C=US/ST=State/L=City/O=LongHaulC2/CN=localhost"; \
		chmod 600 $(KEY_FILE); \
		chmod 644 $(CERT_FILE); \
		sudo chown $(SVC_USER):$(SVC_USER) $(CERT_FILE); \
		sudo chown $(SVC_USER):$(SVC_USER) $(KEY_FILE); \
		sudo chmod 644 $(CERT_FILE); \
		sudo chmod 600 $(KEY_FILE); \
		gum log --level info "API certificates generated successfully in $(CERT_DIR)/"; \
	else \
		gum log --level info "API certificates already exist. Skipping generation to prevent overwrite."; \
	fi
	@if [ ! -f $(UI_CERT_FILE) ]; then \
		gum log --level info "Generating UI self-signed certificates..."; \
		gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Generating UI certificates..." -- \
			openssl req -x509 -newkey rsa:4096 -nodes \
				-keyout $(UI_KEY_FILE) \
				-out $(UI_CERT_FILE) \
				-days $(DAYS) \
				-subj "/C=US/ST=State/L=City/O=LongHaulC2/CN=localhost"; \
		chmod 600 $(UI_KEY_FILE); \
		chmod 644 $(UI_CERT_FILE); \
		sudo chown $(SVC_USER):$(SVC_USER) $(UI_CERT_FILE); \
		sudo chown $(SVC_USER):$(SVC_USER) $(UI_KEY_FILE); \
		sudo chmod 644 $(UI_CERT_FILE); \
		sudo chmod 600 $(UI_KEY_FILE); \
		gum log --level info "UI certificates generated successfully in $(CERT_DIR)/"; \
	else \
		gum log --level info "UI certificates already exist. Skipping generation to prevent overwrite."; \
	fi

## clean-certs: Remove all TLS certificates
.PHONY: clean-certs
clean-certs:
	@gum log --level info "Removing certificates..."
	@rm -rf $(CERT_DIR)
	@gum log --level info "Certificates removed."

# ======================================
# General Utilities
# ======================================

## create_env: Generate .env with credentials
.PHONY: create_env
create_env:
	@$(GUM_BORDER) "Generating .env"
	@gen_pass() { LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32; }; \
	if [ "$(GEN_PASSWORDS)" = "1" ]; then \
		MYSQL_ROOT_PASSWORD=$$(gen_pass); \
		REDIS_PASSWORD=$$(gen_pass); \
		NEO4J_PASSWORD=$$(gen_pass); \
		JWT_SECRET_KEY=$$(gen_pass); \
		INIT_API_PASS=$$(gen_pass); \
	else \
		MYSQL_ROOT_PASSWORD="$(MYSQL_ROOT_PASSWORD)"; \
		REDIS_PASSWORD="$(REDIS_PASSWORD)"; \
		NEO4J_PASSWORD="$(NEO4J_PASSWORD)"; \
		JWT_SECRET_KEY="$(JWT_SECRET_KEY)"; \
		INIT_API_PASS="$(INIT_API_PASS)"; \
	fi; \
	NICEGUI_SECRET=$$(LC_ALL=C tr -dc 'A-Za-z0-9-_' < /dev/urandom | head -c 43); \
	echo "MYSQL_HOST=$(MYSQL_HOST)" > .env; \
	echo "MYSQL_PORT=$(MYSQL_PORT)" >> .env; \
	echo "MYSQL_ROOT_USER=$(MYSQL_ROOT_USER)" >> .env; \
	echo "MYSQL_ROOT_PASSWORD=$$MYSQL_ROOT_PASSWORD" >> .env; \
	echo "MYSQL_DATABASE=c2_db" >> .env; \
	echo "REDIS_HOST=$(REDIS_HOST)" >> .env; \
	echo "REDIS_PORT=$(REDIS_PORT)" >> .env; \
	echo "REDIS_USER=$(REDIS_USER)" >> .env; \
	echo "REDIS_PASSWORD=$$REDIS_PASSWORD" >> .env; \
	echo "NEO4J_HOST=$(NEO4J_HOST)" >> .env; \
	echo "NEO4J_WEB_PORT=$(NEO4J_WEB_PORT)" >> .env; \
	echo "NEO4J_DB_PORT=$(NEO4J_DB_PORT)" >> .env; \
	echo "NEO4J_USER=$(NEO4J_USER)" >> .env; \
	echo "NEO4J_PASSWORD=$$NEO4J_PASSWORD" >> .env; \
	echo "NICEGUI_STORAGE_SECRET=$$NICEGUI_SECRET" >> .env; \
	echo "MYSQL_CONTAINER=$(MYSQL_CONTAINER)" >> .env; \
	echo "REDIS_CONTAINER=$(REDIS_CONTAINER)" >> .env; \
	echo "NEO4J_CONTAINER=$(NEO4J_CONTAINER)" >> .env; \
	echo "WORKSPACE_DIR=$(WORKSPACE_DIR)" >> .env; \
	echo "JWT_SECRET_KEY=$$JWT_SECRET_KEY" >> .env; \
	echo "API_CERT_KEY=$(KEY_FILE)" >> .env; \
	echo "API_CERT_FILE=$(CERT_FILE)" >> .env; \
	echo "UI_CERT_KEY=$(UI_KEY_FILE)" >> .env; \
	echo "UI_CERT_FILE=$(UI_CERT_FILE)" >> .env; \
	echo "INIT_API_USER=$(INIT_API_USER)" >> .env; \
	echo "INIT_API_PASS=$$INIT_API_PASS" >> .env
	@gum log --level info ".env created"


.PHONY: print_all_install_locations
print_all_install_locations:
	@echo "I can't stand it when projects don't tell me what they messed with on my system." > install_reference
	@echo "Here's everything this script touched:" >> install_reference
	@echo "" >> install_reference
	@echo "Installed APT Packages:" >> install_reference
	@echo "$(APT_PACKAGES)" >> install_reference
	@echo "" >> install_reference
	@echo "Install Directory:" >> install_reference
	@echo "$(DEPLOY_DIR)" >> install_reference
	@echo "" >> install_reference
	@echo "System User Created:" >> install_reference
	@echo "$(SVC_USER)" >> install_reference
	@echo "" >> install_reference
	@echo "Systemd Services Created:" >> install_reference
	@echo "/etc/systemd/system/$(word 1, $(SYSTEMD_SERVICES)).service" >> install_reference
	@echo "/etc/systemd/system/$(word 2, $(SYSTEMD_SERVICES)).service" >> install_reference
	@echo "" >> install_reference
	@echo "Containers Downloaded & Running:" >> install_reference
	@echo "mysql:latest -> running as $(MYSQL_CONTAINER)" >> install_reference
	@echo "redis-stack:latest -> running as $(REDIS_CONTAINER)" >> install_reference
	@echo "neo4j:latest -> running as $(NEO4J_CONTAINER)" >> install_reference
	@echo "Workspace Directory" >> install_reference
	@echo "All workspace files (i.e., implant templates) are at $(WORKSPACE_DIR)" >> install_reference
	@echo "" >> install_reference

## prep_for_push: Lint, freeze, and validate before git push
.PHONY: prep_for_push
prep_for_push:
	@$(GUM_BORDER) "Preparing for push"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Running pre-commit hooks..." -- \
		pre-commit run --all-files
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Freezing requirements..." -- \
		$(MAKE) freeze
	@$(MAKE) clean_python

	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Validating pyproject.toml..." -- \
		python -m pip install --dry-run -e ".[server,web]"

	@rm -rf $(DIR_OF_THIS_SCRIPT)/.venv
	@$(GUM_BORDER_SUCCESS) "LongHaulC2 prep successful. Go ahead and push."

## clean_python: Remove __pycache__, .egg-info, and .pyc files
.PHONY: clean_python
clean_python:
	# Clean up Python junk
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# don't run, this calls it form sudo due to this being ran as sudo.
# fix later, but for now manual pip freeze is easier.
# .PHONY: freeze
# freeze: clean_python
# 	# freeze requirements excluding editable
# 	pip freeze --exclude-editable > requirements.lock


## no_fail_test: Run tests, continue on failure
.PHONY: no_fail_test
no_fail_test:
	@$(GUM_BORDER) "Running tests (no-fail mode)"

	-PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
			--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
			$(DIR_OF_THIS_SCRIPT)/tests/server/api_schematesis.py


	-PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py

## test: Run test suite (auto-creates venv if missing)
.PHONY: test
test:
	@if [ ! -d "$(DEV_VENV)" ]; then \
		gum log --level warn "Environment not found. Creating venv at $(DEV_VENV)..."; \
		virtualenv $(DEV_VENV); \
		$(DEV_VENV)/bin/pip install --upgrade pip; \
		if [ -f "$(LOCK_FILE)" ]; then \
			gum log --level info "Installing dependencies from $(LOCK_FILE)..."; \
			$(DEV_VENV)/bin/pip install -r $(LOCK_FILE); \
		else \
			gum log --level warn "$(LOCK_FILE) not found. Skipping dependency install."; \
		fi \
	fi

# 	# *the* testing call to use on push
# 	# fails on failed test

# 	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
# 			--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
# 			$(DIR_OF_THIS_SCRIPT)/tests/server/api_schematesis.py


# 	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
# 		--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
# 		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py

# just doing full scope test at the moment
#  	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
#  		--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
#  		$(DIR_OF_THIS_SCRIPT)/tests/full_scope/setup_implant.py::test_setup_implant
#		$(DIR_OF_THIS_SCRIPT)/venv/bin/python -m pytest -v -s $(DIR_OF_THIS_SCRIPT)/tests/integration_test/deploy_implant.py::test_setup_implant

## integration_test: Run integration tests (requires live implant)
.PHONY: integration_test
integration_test:
	@if [ ! -d "$(DEV_VENV)" ]; then \
		gum log --level warn "Environment not found. Creating venv at $(DEV_VENV)..."; \
		virtualenv $(DEV_VENV); \
		$(DEV_VENV)/bin/pip install --upgrade pip; \
		if [ -f "$(LOCK_FILE)" ]; then \
			gum log --level info "Installing dependencies from $(LOCK_FILE)..."; \
			$(DEV_VENV)/bin/pip install -r $(LOCK_FILE); \
		else \
			gum log --level warn "$(LOCK_FILE) not found. Skipping dependency install."; \
		fi \
	fi

	$(DIR_OF_THIS_SCRIPT)/venv/bin/python -m pytest -v -s $(DIR_OF_THIS_SCRIPT)/tests/integration_test/run_implant_tasks.py::test_run_implant_tasks

# ---------------------------------------------------------------------------
# Local test targets (no implant required — just a running server + Docker DBs)
# ---------------------------------------------------------------------------

## server_tests: Run API server tests (requires running server + DBs)
.PHONY: server_tests
server_tests:
	@$(GUM_BORDER) "Running server tests"
	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_auth.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_health.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_implants.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_listeners.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_filestore.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_build.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_chat.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_users.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_graph.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_profiles.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_audit.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_transforms.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_unauth.py

## web_tests: Run UI smoke tests
.PHONY: web_tests
web_tests:
	@$(GUM_BORDER) "Running web tests"
	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py

## test_implant_responses: Validate implant responses (requires live implant)
.PHONY: test_implant_responses
test_implant_responses:
	@$(GUM_BORDER) "Running implant response tests"
	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		$(DIR_OF_THIS_SCRIPT)/tests/integration_test/test_implant_responses.py

## local_tests: Run all non-implant tests (server + web)
.PHONY: local_tests
local_tests: server_tests web_tests
	@$(GUM_BORDER_SUCCESS) "All local tests complete"

# ======================================
# Help
# ======================================

## help: Show this help message
.PHONY: help
help:
	@echo ""
	@gum style --bold --border rounded --border-foreground "#a16ae8" --padding "1 2" \
		"LongHaulC2 — Makefile targets"
	@echo ""
	@gum style --bold --foreground "#a16ae8" "  Deployment"
	@grep -E '^## ' $(MAKEFILE_LIST) | grep -E '(deploy|undeploy|redeploy):' | sed 's/## /    /'
	@echo ""
	@gum style --bold --foreground "#a16ae8" "  Development"
	@grep -E '^## ' $(MAKEFILE_LIST) | grep -E '(dev_install|dev_uninstall|dev_reinstall|create_env|prep_for_push|clean_python|clean_for_release):' | sed 's/## /    /'
	@echo ""
	@gum style --bold --foreground "#a16ae8" "  Docker"
	@grep -E '^## ' $(MAKEFILE_LIST) | grep -E '(create_docker_images|start_docker_images|stop_docker_images|pull_docker_images):' | sed 's/## /    /'
	@echo ""
	@gum style --bold --foreground "#a16ae8" "  Certificates"
	@grep -E '^## ' $(MAKEFILE_LIST) | grep -E '(certs|clean-certs|cert_prereqs):' | sed 's/## /    /'
	@echo ""
	@gum style --bold --foreground "#a16ae8" "  Testing"
	@grep -E '^## ' $(MAKEFILE_LIST) | grep -E '(test|no_fail_test|integration_test|server_tests|web_tests|test_implant_responses|local_tests):' | sed 's/## /    /'
	@echo ""
	@gum style --bold --foreground "#a16ae8" "  Utilities"
	@grep -E '^## ' $(MAKEFILE_LIST) | grep -E '(check_root|install_gum|help):' | sed 's/## /    /'
	@echo ""
