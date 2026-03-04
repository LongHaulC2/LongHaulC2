# deploy options
PREFIX ?= /opt
DEPLOY_DIR = $(PREFIX)/longhaulc2
SVC_USER = longhaul
DOCKER_DIR := setup/docker_images
WORKSPACE_DIR = /var/lib/longhaulc2

# dev vars
DIR_OF_THIS_SCRIPT := $(shell pwd)
DEV_VENV := $(DIR_OF_THIS_SCRIPT)/venv
DEV_VENV_PATH ?= /venv

# Dependencies
APT_PACKAGES = python3 python3-pip virtualenv docker.io redis-tools postgresql-client
SYSTEMD_SERVICES = longhaulc2-server longhaulc2-web

# Minimal packages for hosted runnersm tldr, they already have docker installed
GH_RUNNER_PACKAGES = virtualenv redis-tools postgresql-client

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

# ======================================
# Production Deployment
# ======================================

.PHONY: deploy
deploy: check_root
	@echo "=================================================="
	@echo "Starting LongHaulC2 Enterprise Deployment..."
	@echo "=================================================="
	
	sudo apt-get update -y
	
# 	# Docker fails on GH actions because it's already installed. Ignore if we're a GH runner
# 	# Additionally, python is already installed, so we can skip that too
# 	@if [ "$$GITHUB_ACTIONS" = "true" ]; then \
# 		echo "GitHub Actions detected! Skipping docker.io installation to avoid conflicts..."; \
# 		sudo apt-get install virtualenv redis-tools postgresql-client -y; \
# 	else \
# 		echo "Local environment detected! Installing full dependencies..."; \
# 		sudo apt-get install $(APT_PACKAGES) -y; \
# 	fi
	
	# Docker fails on GH actions because it's already installed. Ignore if we're a non self hosted GH runner
	# 1. Self-hosted GH Runner
	@if echo "$$RUNNER_LABELS" | grep -q "self-hosted"; then \
		echo "Self-hosted runner detected! Installing FULL dependencies..."; \
		sudo apt-get install -y $(APT_PACKAGES); \
	# 2. GitHub-hosted Runner (Checking if it's GH Actions but NOT self-hosted)
	elif [ "$$GITHUB_ACTIONS" = "true" ] && ! echo "$$RUNNER_LABELS" | grep -q "self-hosted"; then \
		echo "GitHub-hosted runner detected! Installing MINIMAL dependencies..."; \
		sudo apt-get install -y $(MIN_PACKAGES); \
	# 3. Local / Everything else
	else \
		echo "Local non-GitHub environment detected! Installing FULL dependencies..."; \
		sudo apt-get install -y $(APT_PACKAGES); \
	fi
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
	$(MAKE) create_env
	
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
	# log dir
	mkdir -p /var/log/longhaulc2
	
	# copy over user contents into new workspace
	cp -r ./client/src/client/user/. $(WORKSPACE_DIR)
	
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
	
	-$(DEPLOY_DIR)/server/venv/bin/pip install -r $(LOCK_FILE) --no-deps

	virtualenv $(DEPLOY_DIR)/client/venv/
	#$(DEPLOY_DIR)/client/venv/bin/pip install "$(DIR_OF_THIS_SCRIPT)[web]" -c $(LOCK_FILE)
	-$(DEPLOY_DIR)/client/venv/bin/pip install -r $(LOCK_FILE) --no-deps


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
	# doing last, in case this fails, so everything else is setup
	$(MAKE) pull_docker_images
	$(MAKE) create_docker_images
	$(MAKE) start_docker_images
	
	@echo "=================================================="
	@echo "Complete!"
	@echo "=================================================="
	$(MAKE) print_all_install_locations
	@echo "Deployment complete."
	sudo systemctl start longhaulc2-server
	sudo systemctl start longhaulc2-web

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
	
	@echo "=================================================="
	@echo "Stopping and removing Docker containers"
	@echo "=================================================="
	-sudo docker stop $(MYSQL_CONTAINER) $(REDIS_CONTAINER) $(NEO4J_CONTAINER)
	-sudo docker rm $(MYSQL_CONTAINER) $(REDIS_CONTAINER) $(NEO4J_CONTAINER)
	
	@echo "=================================================="
	@echo "Removing installed directories and files"
	@echo "=================================================="
	rm -rf $(DEPLOY_DIR)
	rm -rf /var/lib/longhaulc2
	rm -rf /var/log/longhaulc2
	rm -f .env install_reference
	
	@echo "=================================================="
	@echo "Removing system user"
	@echo "=================================================="
	-userdel $(SVC_USER)
	
	@echo "=================================================="
	@echo "Uninstall complete!"
	@echo "=================================================="
	@echo "Note: APT packages ($(APT_PACKAGES)) and Docker base images were NOT removed to prevent breaking other tools on your system."

.PHONY: redeploy
redeploy: undeploy deploy
	@echo "=================================================="
	@echo "Re-Deploying LongHaulC2 Complete"
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
	
	# create workspace dir here as well, for workspace items for dev. 
	mkdir -p $(WORKSPACE_DIR)
	mkdir -p /var/log/longhaulc2
	cp -r ./client/src/client/user/. $(WORKSPACE_DIR)
	

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
	
	$(MAKE) pull_docker_images
	$(MAKE) create_docker_images
	$(MAKE) start_docker_images
	
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
	-sudo docker stop $(MYSQL_CONTAINER) $(REDIS_CONTAINER) $(NEO4J_CONTAINER)
	-sudo docker rm $(MYSQL_CONTAINER) $(REDIS_CONTAINER) $(NEO4J_CONTAINER)
	
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
	@echo "Starting docker containers..."
	@echo "=================================================="
	
	# https://hub.docker.com/_/mysql
	@echo "Starting mysql"
	sudo docker run --name $(MYSQL_CONTAINER) -p 0.0.0.0:3306:3306 -p 127.0.0.1:33060:33060 -e MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) -d mysql:latest
	
	# https://hub.docker.com/_/redis
	@echo "Starting redis"
	# 8001: Redis Insight. Enabled for dev, can disable/put on localhost for prod.
	sudo docker run -d --name $(REDIS_CONTAINER) -p 127.0.0.1:6379:6379 -p 0.0.0.0:8001:8001 -e REDIS_ARGS="--requirepass $(REDIS_PASSWORD)" redis/redis-stack:latest
	
	# https://hub.docker.com/_/neo4j
	@echo "Starting neo4j"
	sudo docker run -d --name $(NEO4J_CONTAINER) -p 7474:7474 -p 7687:7687 --volume=$(HOME)/neo4j/data:/data --env=NEO4J_AUTH=$(NEO4J_USER)/$(NEO4J_PASSWORD) neo4j:latest

.PHONY: pull_docker_images
pull_docker_images:
	@echo "=================================================="
	@echo "Pulling docker images..."
	@echo "=================================================="
	sudo docker pull mysql:latest
	sudo docker pull redis:latest
	sudo docker pull neo4j:latest

# ======================================
# General Utilities
# ======================================

.PHONY: create_env
create_env:
	@touch .env
	@echo "MYSQL_HOST=$(MYSQL_HOST)" > .env
	@echo "MYSQL_PORT=$(MYSQL_PORT)" >> .env
	@echo "MYSQL_ROOT_USER=$(MYSQL_ROOT_USER)" >> .env
	@echo "MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD)" >> .env
	# Change this to like my_engagement_202X_month to track different engagements
	@echo "MYSQL_DATABASE=c2_db" >> .env
	@echo "REDIS_HOST=$(REDIS_HOST)" >> .env
	@echo "REDIS_PORT=$(REDIS_PORT)" >> .env
	@echo "REDIS_USER=$(REDIS_USER)" >> .env
	@echo "REDIS_PASSWORD=$(REDIS_PASSWORD)" >> .env
	@echo "NEO4J_HOST=$(NEO4J_HOST)" >> .env
	@echo "NEO4J_WEB_PORT=$(NEO4J_WEB_PORT)" >> .env
	@echo "NEO4J_DB_PORT=$(NEO4J_DB_PORT)" >> .env
	@echo "NEO4J_USER=$(NEO4J_USER)" >> .env
	@echo "NEO4J_PASSWORD=$(NEO4J_PASSWORD)" >> .env
	
	# nicegui storage secret - used for user sessions
	@SECRET=$$(LC_ALL=C tr -dc 'A-Za-z0-9-_' < /dev/urandom | head -c 43); \
	echo "NICEGUI_STORAGE_SECRET=$$SECRET" >> .env
	
	# add in docker container names
	@echo "MYSQL_CONTAINER=$(MYSQL_CONTAINER)" >> .env
	@echo "REDIS_CONTAINER=$(REDIS_CONTAINER)" >> .env
	@echo "NEO4J_CONTAINER=$(NEO4J_CONTAINER)" >> .env

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

.PHONY: freeze
freeze: clean_python
	# freeze requirements excluding editable
	pip freeze --exclude-editable > requirements.lock


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
		python3 -m venv $(DEV_VENV); \
		$(DEV_VENV)/bin/pip install --upgrade pip; \
		if [ -f "$(LOCK_FILE)" ]; then \
			echo "Installing dependencies from $(LOCK_FILE)..."; \
			$(DEV_VENV)/bin/pip install -r $(LOCK_FILE); \
		else \
			echo "Warning: $(LOCK_FILE) not found. Skipping dependency install."; \
		fi \
	fi

	# *the* testing call to use on push
	# fails on failed test

# 	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
# 			--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
# 			$(DIR_OF_THIS_SCRIPT)/tests/server/api_schematesis.py


# 	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
# 		--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
# 		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py

	# just doing full scope test at the moment
 	PYTHONPATH=$(DIR_OF_THIS_SCRIPT) $(DEV_VENV)/bin/python -m pytest -v -s \
 		--ignore=$(DIR_OF_THIS_SCRIPT)/dev_testing \
 		$(DIR_OF_THIS_SCRIPT)/tests/web/web_tests.py::test_setup_implant