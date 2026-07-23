SHELL := /bin/bash

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
# Helpers
# ======================================

.PHONY: check_root
check_root:
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "=================================================="; \
		echo "Error: This target must be run with superuser privileges (e.g. sudo make $$@)"; \
		echo "=================================================="; \
		exit 1; \
	fi

.PHONY: clean_for_release
clean_for_release:
	# removing items that are great for dev but bloat the release
	echo "=================================================="; \
	echo "Cleaning project for release " \
	echo "=================================================="; \
	sudo rm -rf ./.claude
	sudo rm -rf ./.claude
	sudo rm -rf ./.hypothesis
	sudo rm -rf ./.nicegui
	sudo rm -rf ./.pytest_cache
	sudo rm -rf ./.ruff_cache
	sudo rm -rf ./.venv
	sudo rm -rf ./.vscode
	sudo rm -rf ./development
	sudo rm -rf ./CLAUDE.md


# ======================================
# Production Deployment
# ======================================

.PHONY: deploy
deploy: check_root
	@echo "=================================================="
	@echo "Starting LongHaulC2 Enterprise Deployment..."
	@echo "=================================================="
	
	sudo apt-get update -y
	
	sudo apt-get install -y $(APT_PACKAGES)

	# immediately setup cert stuff to make sure it exists
	$(MAKE) cert_prereqs

	@echo "Dependencies installed, continuing with deployment..."
	
	@echo "=================================================="
	@echo "Creating longhaul user"
	@echo "=================================================="
	# Create the restricted system user
	@id -u $(SVC_USER) >/dev/null 2>&1 || useradd --system --no-create-home --shell /bin/false $(SVC_USER)
	# create docker group if it doesn't already exist
	sudo getent group docker || groupadd docker
	# add user to docker group
	sudo usermod -aG docker $(SVC_USER)

	@echo "=================================================="
	@echo "Creating .env"
	@echo "=================================================="
	@if [ -f .env ]; then \
		echo ".env already exists — keeping existing credentials"; \
	else \
		$(MAKE) create_env GEN_PASSWORDS=1; \
	fi

	@echo "=================================================="
	@echo "Creating directories"
	@echo "=================================================="
	# Build the FHS directory structure
	mkdir -p $(DEPLOY_DIR)/server
	mkdir -p $(DEPLOY_DIR)/client
	mkdir -p $(DEPLOY_DIR)/server/venv
	mkdir -p $(DEPLOY_DIR)/client/venv
	
	# /var/lib/longhaulc2 for workspace items
	mkdir -p $(WORKSPACE_DIR)
	
	# location for implant templates to live
	mkdir -p $(WORKSPACE_DIR)/implant_templates

	# copy over templates
	cp -r ./implant_templates/. $(WORKSPACE_DIR)/implant_templates

	# log dir
	mkdir -p /var/log/longhaulc2
	
	# copy over user contents into new workspace
	cp -r ./client/user/. $(WORKSPACE_DIR)
	
	@echo "=================================================="
	@echo "Copying files"
	@echo "=================================================="
	cp -r server/* $(DEPLOY_DIR)/server/
	cp -r client/* $(DEPLOY_DIR)/client/
	cp -r .env $(DEPLOY_DIR)/
	


	@echo "=================================================="
	@echo "Creating virtualenv"
	@echo "=================================================="
	# updated to use pip pyproject.toml and freeze
	# Standard install (non-editable) for production stability/isolation
	virtualenv $(DEPLOY_DIR)/server/venv/
	#$(DEPLOY_DIR)/server/venv/bin/pip install "$(DIR_OF_THIS_SCRIPT)[server]" -c $(LOCK_FILE)
	
	$(DEPLOY_DIR)/server/venv/bin/pip install -r $(LOCK_FILE)

	virtualenv $(DEPLOY_DIR)/client/venv/
	$(DEPLOY_DIR)/client/venv/bin/pip install -r $(LOCK_FILE)


	@echo "=================================================="
	@echo "Setting permissions"
	@echo "=================================================="
	# Lock down permissions
	# Code is owned by root, but readable by the service
	chown -R root:$(SVC_USER) $(DEPLOY_DIR)
	chmod -R 750 $(DEPLOY_DIR)
	
	# State, Configs, and Logs MUST be writable by the service
	chown -R $(SVC_USER):$(SVC_USER) /var/lib/longhaulc2
	chown -R $(SVC_USER):$(SVC_USER) /var/log/longhaulc2
	
	# Appdirs must be as well
	sudo chown -R longhaul:longhaul /opt/longhaulc2/

	# create certs

	$(MAKE) certs

	@echo "=================================================="
	@echo "Setting up services"
	@echo "=================================================="
	# Parse systemd templates and install them
	sed -e 's|@DEPLOY_DIR@|$(DEPLOY_DIR)|g' ./setup/longhaulc2-server.service.in > /etc/systemd/system/longhaulc2-server.service
	sed -e 's|@DEPLOY_DIR@|$(DEPLOY_DIR)|g' ./setup/longhaulc2-web.service.in > /etc/systemd/system/longhaulc2-web.service
	
	# Reload and enable systemd
	systemctl daemon-reload
	systemctl enable longhaulc2-server
	systemctl enable longhaulc2-web
	
	@echo "=================================================="
	@echo "Setting up docker containers"
	@echo "=================================================="
	# service containers via compose (doing last, in case this fails, so everything else is setup)
	$(MAKE) start_docker_images
	# cross-compiler image for implant builds
	$(MAKE) create_docker_images

	@echo "=================================================="
	@echo "Complete!"
	@echo "=================================================="
	$(MAKE) print_all_install_locations
	sudo systemctl start longhaulc2-server
	sudo systemctl start longhaulc2-web
	@echo ""
	@echo "=================================================="
	@echo "  Deployment complete."
	@echo "=================================================="
	@echo ""
	@echo "  Initial operator credentials:"
	@echo "    Username: $$(grep '^INIT_API_USER=' .env | cut -d= -f2)"
	@echo "    Password: $$(grep '^INIT_API_PASS=' .env | cut -d= -f2)"
	@echo ""
	@echo "  Save these credentials — they will not be shown again."
	@echo "  All service passwords are stored in .env"
	@echo "=================================================="

.PHONY: undeploy
undeploy: check_root
	@echo "=================================================="
	@echo "Starting LongHaulC2 Enterprise Uninstall..."
	@echo "=================================================="
	
	@echo "=================================================="
	@echo "Stopping and removing systemd services"
	@echo "=================================================="
	-systemctl stop $(word 1, $(SYSTEMD_SERVICES)) $(word 2, $(SYSTEMD_SERVICES))
	-systemctl disable $(word 1, $(SYSTEMD_SERVICES)) $(word 2, $(SYSTEMD_SERVICES))
	rm -f /etc/systemd/system/$(word 1, $(SYSTEMD_SERVICES)).service
	rm -f /etc/systemd/system/$(word 2, $(SYSTEMD_SERVICES)).service
	systemctl daemon-reload
	
	# remove certs
	$(MAKE) clean-certs

	@echo "=================================================="
	@echo "Stopping and removing Docker containers"
	@echo "=================================================="
ifeq ($(KEEP_DATA),1)
	@echo "KEEP_DATA=1 — preserving Docker volumes and workspace data"
	-docker compose down
else
	-docker compose down -v
endif

	@echo "=================================================="
	@echo "Removing installed directories and files"
	@echo "=================================================="
	rm -rf $(DEPLOY_DIR)
ifneq ($(KEEP_DATA),1)
	rm -rf /var/lib/longhaulc2
	rm -f .env
endif
	rm -rf /var/log/longhaulc2
	rm -f install_reference
	
	@echo "=================================================="
	@echo "Removing system user"
	@echo "=================================================="
	-userdel $(SVC_USER)
	
	@echo "=================================================="
	@echo "Uninstall complete!"
	@echo "=================================================="
	@echo "Note: APT packages ($(APT_PACKAGES)) and Docker base images were NOT removed to prevent breaking other tools on your system."

.PHONY: redeploy
redeploy:
	$(MAKE) undeploy KEEP_DATA=1
	$(MAKE) deploy
	@echo "=================================================="
	@echo "Re-Deploying LongHaulC2 Complete (data preserved)"
	@echo "=================================================="

# ======================================
# Development Install
# ======================================

.PHONY: dev_install
dev_install:
	@echo "=================================================="
	@echo "Starting LongHaulC2 Development Install..."
	@echo "=================================================="
	
	@echo "=================================================="
	@echo "Installing required dependencies"
	@echo "=================================================="
	sudo apt-get update
	sudo apt-get install $(APT_PACKAGES) -y
	
	@echo "=================================================="
	@echo "Creating virtualenv @ $(DEV_VENV_PATH)"
	@echo "=================================================="
	virtualenv $(DEV_VENV)
	$(DEV_VENV)/bin/pip install -e ".[server,web,dev]" -c $(LOCK_FILE)
	
	@echo "=================================================="
	@echo "Creating .env"
	@echo "=================================================="
	$(MAKE) create_env
	
	@echo "=================================================="
	@echo "Creating workspace dirs"
	@echo "=================================================="
	sudo mkdir -p $(WORKSPACE_DIR)
	sudo mkdir -p $(WORKSPACE_DIR)/implant_templates
	sudo chown -R $(USER):$(USER) $(WORKSPACE_DIR)
	cp -r ./client/user/. $(WORKSPACE_DIR)
	cp -r ./implant_templates/. $(WORKSPACE_DIR)/implant_templates

	@echo "=================================================="
	@echo "Creating log dirs"
	@echo "=================================================="
	sudo mkdir -p /var/log/longhaulc2/
	sudo mkdir -p /var/log/longhaulc2/web/
	sudo mkdir -p /var/log/longhaulc2/server/
	sudo chmod -R 777 /var/log/longhaulc2

	@echo "=================================================="
	@echo "Setting up docker containers"
	@echo "=================================================="
	# doing this LAST, so everything else gets setup in case these fail
	sudo getent group docker || groupadd docker
	# service containers via compose
	$(MAKE) start_docker_images
	# cross-compiler image for implant builds
	$(MAKE) create_docker_images
	
	@echo "Activate the venv with 'source $(DEV_VENV_PATH)/bin/activate'"
	@echo "Development env setup & ready to go"

.PHONY: dev_uninstall
dev_uninstall:
	@echo "=================================================="
	@echo "Uninstalling Development Environment..."
	@echo "=================================================="
	
	@echo "=================================================="
	@echo "Stopping & removing docker containers"
	@echo "=================================================="
	-docker compose down
	
	@echo "=================================================="
	@echo "Removing virtualenv and configurations"
	@echo "=================================================="
	rm -rf $(DEV_VENV_PATH)
	-rm -f .env
	
	# nuke workspace and log dirs as well
	sudo rm -rf /var/lib/longhaulc2
	sudo rm -rf /var/log/longhaulc2

.PHONY: dev_reinstall
dev_reinstall: dev_uninstall dev_install
	@echo "=================================================="
	@echo "Everything Reset!"
	@echo "=================================================="

# ======================================
# Docker Utilities
# ======================================

.PHONY: create_docker_images
create_docker_images:
	sudo getent group docker >/dev/null || sudo groupadd docker
	sudo usermod -aG docker "$(USER)"
	@echo "Log out and back in (or run: newgrp docker) for changes to take effect."
	
	@echo "=================================================="
	@echo "Creating local docker images"
	@echo "=================================================="
	@for d in $(DOCKER_DIR)/*; do \
		if [ -d "$$d" ]; then \
			img_name=$$(basename $$d); \
			echo "=================================================="; \
			echo "Building $$img_name from $$d"; \
			echo "=================================================="; \
			sudo docker build --pull --no-cache -t $$img_name:latest $$d; \
		fi \
	done

.PHONY: start_docker_images
start_docker_images:
	@echo "=================================================="
	@echo "Starting docker containers via compose..."
	@echo "=================================================="
	docker compose up -d

.PHONY: stop_docker_images
stop_docker_images:
	@echo "=================================================="
	@echo "Stopping docker containers..."
	@echo "=================================================="
	docker compose down

.PHONY: pull_docker_images
pull_docker_images:
	@echo "=================================================="
	@echo "Pulling docker images..."
	@echo "=================================================="
	docker compose pull

# ======================================
# Certs
# ======================================
.PHONY cert_prereqs: cert_prereqs
cert_prereqs:
	# these commands make sure the CA exists first. 
	# TLDR, run FIRST before pip

	sudo apt-get install -y --reinstall ca-certificates
	sudo update-ca-certificates

.PHONY: certs
certs:
	@echo "=================================================="
	@echo "Creating Certificates"
	@echo "=================================================="
	@mkdir -p $(CERT_DIR)
	@if [ ! -f $(CERT_FILE) ]; then \
		echo "Generating API self-signed certificates..."; \
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
		echo "API certificates generated successfully in $(CERT_DIR)/"; \
	else \
		echo "API certificates already exist. Skipping generation to prevent overwrite."; \
	fi
	@if [ ! -f $(UI_CERT_FILE) ]; then \
		echo "Generating UI self-signed certificates..."; \
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
		echo "UI certificates generated successfully in $(CERT_DIR)/"; \
	else \
		echo "UI certificates already exist. Skipping generation to prevent overwrite."; \
	fi

.PHONY: clean-certs
clean-certs:
	@echo "Removing certificates..."
	@rm -rf $(CERT_DIR)
	@echo "Certificates removed."

# ======================================
# General Utilities
# ======================================

.PHONY: create_env
create_env:
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

.PHONY: prep_for_push
prep_for_push:
	# Final Lint/Format Check (Manual trigger of hooks)
	pre-commit run --all-files
	$(MAKE) freeze
	$(MAKE) clean_python
	
	# Validate pyproject.toml
	python -m pip install --dry-run -e ".[server,web]"
	
	# Nuke dev environment
	rm -rf $(DIR_OF_THIS_SCRIPT)/.venv
	@echo "=================================================="
	@echo "LongHaulC2 prep successful. Go ahead and push."
	@echo "=================================================="

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


.PHONY: no_fail_test
no_fail_test: 
	# just calling each test individually due to pathing problems, it's fine. 

	# "-" allows for it to fail, yet continue on. Probably shouldn't use this for the final testing to make sure things work
	# in the GH actions.

	-PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
			--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
			$(DIR_OF_THIS_SCRIPT)/tests/server/api_schematesis.py


	-PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py

.PHONY: test
test: 
	# make sure dev venv exsists first
	@if [ ! -d "$(DEV_VENV)" ]; then \
		echo "Environment not found. Creating venv at $(DEV_VENV)..."; \
		virtualenv $(DEV_VENV); \
		$(DEV_VENV)/bin/pip install --upgrade pip; \
		if [ -f "$(LOCK_FILE)" ]; then \
			echo "Installing dependencies from $(LOCK_FILE)..."; \
			$(DEV_VENV)/bin/pip install -r $(LOCK_FILE); \
		else \
			echo "Warning: $(LOCK_FILE) not found. Skipping dependency install."; \
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

.PHONY: integration_test
integration_test: 
	# make sure dev venv exsists first
	@if [ ! -d "$(DEV_VENV)" ]; then \
		echo "Environment not found. Creating venv at $(DEV_VENV)..."; \
		virtualenv $(DEV_VENV); \
		$(DEV_VENV)/bin/pip install --upgrade pip; \
		if [ -f "$(LOCK_FILE)" ]; then \
			echo "Installing dependencies from $(LOCK_FILE)..."; \
			$(DEV_VENV)/bin/pip install -r $(LOCK_FILE); \
		else \
			echo "Warning: $(LOCK_FILE) not found. Skipping dependency install."; \
		fi \
	fi

	$(DIR_OF_THIS_SCRIPT)/venv/bin/python -m pytest -v -s $(DIR_OF_THIS_SCRIPT)/tests/integration_test/run_implant_tasks.py::test_run_implant_tasks

# ---------------------------------------------------------------------------
# Local test targets (no implant required — just a running server + Docker DBs)
# ---------------------------------------------------------------------------

.PHONY: server_tests
server_tests:
	# Run API server tests: auth, health, implants, listeners, filestore, build.
	# Requires: server running on localhost:45045 and Docker DBs up.
	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_auth.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_health.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_implants.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_listeners.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_filestore.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_build.py \
		$(DIR_OF_THIS_SCRIPT)/tests/server/test_unauth.py

.PHONY: web_tests
web_tests:
	# Run UI smoke tests. No server or implant needed.
	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py

.PHONY: test_implant_responses
test_implant_responses:
	# Run implant response validation tests against a live beaconing implant.
	# Requires: server running, Docker DBs up, live implant beaconing.
	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
		$(DIR_OF_THIS_SCRIPT)/tests/integration_test/test_implant_responses.py

.PHONY: local_tests
local_tests: server_tests web_tests
	# Run all non-implant tests (server API + UI smoke).