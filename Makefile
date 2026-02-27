PREFIX ?= /opt
INSTALL_DIR = $(PREFIX)/longhaulc2
SVC_USER = longhaul
DOCKER_DIR := setup/docker_images
WORKSPACE_DIR = /var/lib/longhaulc2
# Dependencies
APT_PACKAGES = python3 python3-pip virtualenv docker.io redis-tools postgresql-client
SYSTEMD_SERVICES = longhaulc2-server longhaulc2-web

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
# can specify creds manually with:
#make install MYSQL_ROOT_PASSWORD=SuperSecure123

# ideas - a skip DB, which leaves all the DB files, but resets everything else for deploy

# ======================================
# For prod deployment
# ======================================

.PHONY: deploy
deploy:
	@echo "Starting LongHaulC2 Enterprise Deployment..."
	
	$(MAKE) check_root
	
	sudo apt-get update -y
	# sudo apt-get install $(APT_PACKAGES) -y

	# Docker fails on GH actions becuase it's already installed. Ignore if we're a GH runner
	# Additionally, python is already installed, so we can skip that too
	
	@if [ -n "$$CI" ]; then \
		echo "GitHub Actions detected! Skipping docker.io installation to avoid conflicts..."; \
		sudo apt-get install virtualenv redis-tools postgresql-client -y; \
	else \
		echo "Local environment detected! Installing full dependencies..."; \
		sudo apt-get install $(APT_PACKAGES) -y; \
	fi

	@echo "Dependencies installed, continuing with deployment..."

	@echo "=================================================="
	@echo "Creating longhaul user"
	@echo "================================================="

	# Create the restricted system user
	@id -u $(SVC_USER) >/dev/null 2>&1 || useradd --system --no-create-home --shell /bin/false $(SVC_USER)

	# create docker group if it doesn't already exist
	sudo getent group docker || groupadd docker
	# add user to docker group
	sudo usermod -aG docker $(SVC_USER)

	@echo "=================================================="
	@echo "Creating .env"
	@echo "================================================="

	$(MAKE) create_env

	@echo "=================================================="
	@echo "Creating directories"
	@echo "================================================="

	# 2. Build the FHS directory structure
	mkdir -p $(INSTALL_DIR)/server
	mkdir -p $(INSTALL_DIR)/client

	mkdir -p $(INSTALL_DIR)/server/venv
	mkdir -p $(INSTALL_DIR)/client/venv

	# /var/lib/longhaulc2 for workspace items
	mkdir -p $(WORKSPACE_DIR)
	# log dir
	mkdir -p /var/log/longhaulc2

	# copy over user contents into new workspace
	cp -r ./client/src/client/user/. $(WORKSPACE_DIR)

	@echo "=================================================="
	@echo "Copying files"
	@echo "================================================="
	
	# Copy files
	cp -r server/* $(INSTALL_DIR)/server/
	cp -r client/* $(INSTALL_DIR)/client/
	cp -r .env $(INSTALL_DIR)/

	@echo "=================================================="
	@echo "Creating virtualenv"
	@echo "=================================================="

	#server venv
	virtualenv $(INSTALL_DIR)/server/venv/
	$(INSTALL_DIR)/server/venv/bin/pip install -r $(INSTALL_DIR)/server/src/server/requirements.txt

	#web venv
	virtualenv $(INSTALL_DIR)/client/venv/
	$(INSTALL_DIR)/client/venv/bin/pip install -r $(INSTALL_DIR)/client/src/client/requirements.txt


	@echo "=================================================="
	@echo "Settings perms" 
	@echo "=================================================="

	# 4. Lock down permissions
	# Code is owned by root, but readable by the service
	chown -R root:$(SVC_USER) $(INSTALL_DIR)
	chmod -R 750 $(INSTALL_DIR)
	
	# State, Configs, and Logs MUST be writable by the service
	chown -R $(SVC_USER):$(SVC_USER) /var/lib/longhaulc2
	chown -R $(SVC_USER):$(SVC_USER) /var/log/longhaulc2
	#chown -R $(SVC_USER):$(SVC_USER) /etc/longhaulc2

	@echo "=================================================="
	@echo "Setting up services" 
	@echo "=================================================="

	# 5. Parse systemd templates and install them
	sed -e 's|@INSTALL_DIR@|$(INSTALL_DIR)|g' ./setup/longhaulc2-server.service.in > /etc/systemd/system/longhaulc2-server.service
	sed -e 's|@INSTALL_DIR@|$(INSTALL_DIR)|g' ./setup/longhaulc2-web.service.in > /etc/systemd/system/longhaulc2-web.service

	# 6. Reload and enable systemd
	systemctl daemon-reload
	systemctl enable longhaulc2-server
	systemctl enable longhaulc2-web

	@echo "=================================================="
	@echo "Setting up docker containers" 
	@echo "=================================================="
	# doing last, incase this fails, so everything else is setup
	$(MAKE) pull_docker_images
	$(MAKE) create_docker_images
	$(MAKE) start_docker_images

	@echo "=================================================="
	@echo "Complete!" 
	@echo "=================================================="

	$(MAKE) print_all_install_locations
	@echo
	@echo "Deployment complete."
	sudo systemctl start longhaulc2-server
	sudo systemctl start longhaulc2-web
	@echo "Run 'systemctl start longhaulc2-server' and 'systemctl start longhaulc2-web' to boot."

PHONY: undeploy
undeploy:
	@echo "Starting LongHaulC2 Enterprise Uninstall..."

	$(MAKE) check_root

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
	rm -rf $(INSTALL_DIR)
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
redeploy:
	@echo "Re-Deploying LongHaulC2"
	$(MAKE) undeploy
	$(MAKE) deploy


.PHONY: create_docker_images

# ======================================
# For development install
# ======================================
DEV_VENV_PATH ?= ./venv

.PHONY: dev_install
dev_install:
	@echo "Starting LongHaulC2 Development Install..."

	@echo "=================================================="
	@echo "Installing required dependencies"
	@echo "=================================================="

	sudo apt-get update
	sudo apt-get install python3 python3-pip virtualenv docker.io redis-tools postgresql-client -y


	@echo "=================================================="
	@echo "Creating virtualenv @ $(DEV_VENV_PATH)"
	@echo "=================================================="
	virtualenv $(DEV_VENV_PATH)
	$(DEV_VENV_PATH)/bin/pip install -r ./server/src/server/requirements.txt
	$(DEV_VENV_PATH)/bin/pip install -r ./client/src/client/requirements.txt

	@echo "=================================================="
	@echo "Creating .env"
	@echo "================================================="

	$(MAKE) create_env

	# create workspace dir here as well, for workspace items for dev. 
	# /var/lib/longhaulc2 for workspace items
	mkdir -p $(WORKSPACE_DIR)
	# log dir
	mkdir -p /var/log/longhaulc2

	# copy over user contents into new workspace
	cp -r ./client/src/client/user/. $(WORKSPACE_DIR)

	@echo "=================================================="
	@echo "Setting up docker containers" 
	@echo "=================================================="
	# doing this LAST, so everything else gets setup incase these fail
	# create docker group if it doesn't already exist
	sudo getent group docker || groupadd docker
	# add user to docker group, no logout needed
	#newgrp docker


	$(MAKE) pull_docker_images
	$(MAKE) create_docker_images
	$(MAKE) start_docker_images


	@echo "Activate the venv with 'source $(VENV_PATH)/bin/activate'"
	@echo "Development env setup & ready to go"


.PHONY: dev_uninstall
dev_uninstall:
	@echo "=================================================="
	@echo "Uninstalling..."
	@echo "=================================================="

	@echo "=================================================="
	@echo "Stopping & removing docker containers"
	@echo "=================================================="

	@echo "Stopping and removing Docker containers"
	-sudo docker stop $(MYSQL_CONTAINER) $(REDIS_CONTAINER) $(NEO4J_CONTAINER)
	-sudo docker rm $(MYSQL_CONTAINER) $(REDIS_CONTAINER) $(NEO4J_CONTAINER)

	@echo "=================================================="
	@echo "Removing virtualenv"
	@echo "=================================================="
	rm -rf ./venv

	@echo "=================================================="
	@echo "Removing .env"
	@echo "=================================================="

	@echo "Removing .env"
	-rm .env

	# nuke workspace and log dirs as well
	rm -rf /var/lib/longhaulc2
	rm -rf /var/log/longhaulc2

.PHONY: dev_reset
dev_reset: dev_uninstall dev_install
	@echo "=================================================="
	@echo "Everything Reset!"
	@echo "=================================================="

.PHONY: create_docker_images
create_docker_images:
	sudo getent group docker >/dev/null || sudo groupadd docker

	sudo usermod -aG docker "$(USER)"
	echo "Log out and back in (or run: newgrp docker) for changes to take effect."

	@echo "=================================================="
	@echo "Creating docker images"
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
	@echo "Starting docker images..."
	@echo "=================================================="

	# https://hub.docker.com/_/mysql
	@echo "Starting mysql"
	sudo docker run --name $(MYSQL_CONTAINER) -p 0.0.0.0:3306:3306 -p 127.0.0.1:33060:33060 -e MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) -d mysql:latest

	# https://hub.docker.com/_/redis
	@echo "Starting redis"
	#8001: Redis Insight. Enabled for dev, can disable/put on localhost for prod.
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

.PHONY: create_env
create_env:
	@echo "=================================================="
	@echo "Creating .env..."
	@echo "=================================================="
	touch .env
	echo MYSQL_HOST=$(MYSQL_HOST) > .env
	echo MYSQL_PORT=$(MYSQL_PORT) >> .env
	echo MYSQL_ROOT_USER=$(MYSQL_ROOT_USER) >> .env
	echo MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) >> .env
	# Change this to like my_engagement_202X_month or whatever to track different engagements if you're using one an external DB for multiple servers
	echo MYSQL_DATABASE=c2_db >> .env

	echo REDIS_HOST=$(REDIS_HOST) >> .env
	echo REDIS_PORT=$(REDIS_PORT) >> .env
	echo REDIS_USER=$(REDIS_USER) >> .env
	echo REDIS_PASSWORD=$(REDIS_PASSWORD) >> .env

	echo NEO4J_HOST=$(NEO4J_HOST) >> .env
	echo NEO4J_WEB_PORT=$(NEO4J_WEB_PORT) >> .env
	echo NEO4J_DB_PORT=$(NEO4J_DB_PORT) >> .env
	echo NEO4J_USER=$(NEO4J_USER) >> .env
	echo NEO4J_PASSWORD=$(NEO4J_PASSWORD) >> .env

	# nicegui storage secret - used for user sessions
	# use bash to generate a random string
	_NICEGUI_STORAGE_SECRET=$$(LC_ALL=C tr -dc 'A-Za-z0-9-_' < /dev/urandom | head -c 43)
	echo "NICEGUI_STORAGE_SECRET=$(SECRET)" >> .env

	# add in docker container names
	echo MYSQL_CONTAINER=$(MYSQL_CONTAINER) >> .env
	echo REDIS_CONTAINER=$(REDIS_CONTAINER) >> .env
	echo NEO4J_CONTAINER=$(NEO4J_CONTAINER) >> .env

check_root:
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "==============================================================================="; \
		echo "Error: This target must be run with superuser privileges (e.g., sudo make $@)"; \
		echo "===============================================================================" \
		exit 1; \
	fi

.PHONY: print_all_install_locations
print_all_install_locations:
	@echo "I can't stand it when projects don't tell me what they messed with on my system." >> install_reference
	@echo "Here's everything this script touched:" >> install_reference
	@echo "" >> install_reference
	@echo "Installed APT Packages:" >> install_reference
	@echo "$(APT_PACKAGES)" >> install_reference
	@echo "" >> install_reference
	@echo "Install Directory:" >> install_reference
	@echo "$(INSTALL_DIR)" >> install_reference
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


