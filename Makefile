# Simple Makefile

#all: myapp

VENV_PATH ?= ./venv
DOCKER_DIR := setup/docker_images

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



install:
	@echo "=================================================="
	@echo "Installing required dependencies"
	@echo "=================================================="

	sudo apt-get update
	sudo apt-get install python3 python3-pip virtualenv docker.io redis-tools postgresql-client -y

	# docker install
	sudo docker pull mysql:latest
	sudo docker pull redis:latest
	sudo docker pull neo4j:latest

	@echo "=================================================="
	@echo "Starting docker images..."
	@echo "=================================================="

	# https://hub.docker.com/_/mysql
	@echo "Starting mysql"
	sudo docker run --name C2_mysql -p 0.0.0.0:3306:3306 -p 127.0.0.1:33060:33060 -e MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) -d mysql:latest

	# https://hub.docker.com/_/redis
	@echo "Starting redis"
	#8001: Redis Insight. Enabled for dev, can disable/put on localhost for prod.
	sudo docker run -d --name C2_redis-stack -p 127.0.0.1:6379:6379 -p 0.0.0.0:8001:8001 -e REDIS_ARGS="--requirepass $(REDIS_PASSWORD)" redis/redis-stack:latest

	# https://hub.docker.com/_/neo4j
	@echo "Starting neo4j"
	sudo docker run -d --name C2_neo4j-stack -p 7474:7474 -p 7687:7687 --volume=$(HOME)/neo4j/data:/data --env=NEO4J_AUTH=$(NEO4J_USER)/$(NEO4J_PASSWORD) neo4j:latest

	@echo "=================================================="
	@echo "Creating docker images for cross compilation"
	@echo "=================================================="
	$(MAKE) create_docker_images

	@echo "=================================================="
	@echo "Creating virtualenv @ $(VENV_PATH)"
	@echo "=================================================="
	virtualenv $(VENV_PATH)
	$(VENV_PATH)/bin/pip install -r ./server/src/server/requirements.txt
	$(VENV_PATH)/bin/pip install -r ./client/src/client/requirements.txt

	@echo "=================================================="
	@echo "Creating .env..."
	@echo "=================================================="
	echo MYSQL_HOST=$(MYSQL_HOST) >> .env
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

	@echo "=================================================="
	@echo "Final Steps:"
	@echo "=================================================="

	@echo "REDIS:"
	@echo "\tServer: $(REDIS_HOST):$(REDIS_PORT)"
	@echo "\tUser: $(REDIS_USER)"
	@echo "\tInsights: 0.0.0.0:8001"
	@echo ""

	@echo "MYSQL:"
	@echo "\tDB: $(MYSQL_HOST):$(MYSQL_PORT)"
	@echo "\tUser: $(MYSQL_ROOT_USER)"
	@echo "\tDatabase: c2_db"
	@echo ""

	@echo "NEO4J:"
	@echo "\tWeb: $(NEO4J_HOST):$(NEO4J_WEB_PORT)"
	@echo "\tDB: $(NEO4J_HOST):$(NEO4J_DB_PORT)"
	@echo "\tUser: $(NEO4J_USER)"
	@echo ""

	@echo "C2"
	@echo "\tManagement: X:X"
	@echo ""
	
	@echo "Activate the venv with 'source $(VENV_PATH)/bin/activate'"
	@echo "Start the application with ..."


uninstall:
	@echo "=================================================="
	@echo "Uninstalling..."
	@echo "=================================================="

	@echo "=================================================="
	@echo "Stopping & removing docker containers"
	@echo "=================================================="

	@echo "Stopping and removing Docker containers"
	-sudo docker stop C2_mysql
	-sudo docker rm C2_mysql
	-sudo docker stop C2_redis-stack
	-sudo docker rm C2_redis-stack
	-sudo docker stop C2_neo4j-stack
	-sudo docker rm C2_neo4j-stack

	-sudo docker rmi mysql:latest
	-sudo docker rmi redis-stack:latest
	-sudo docker rmi neo4j:latest

	@echo "=================================================="
	@echo "Removing virtualenv"
	@echo "=================================================="
	rm -rf ./venv

	@echo "=================================================="
	@echo "Removing .env"
	@echo "=================================================="

	@echo "Removing .env"
	-rm .env


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


clean:
	#rm -f myapp

reset: uninstall install
	@echo "=================================================="
	@echo "Everything Reset!"
	@echo "=================================================="

.PHONY: all install uninstall clean
