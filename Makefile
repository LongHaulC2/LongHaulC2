# Simple Makefile

#all: myapp

VENV_PATH ?= ./venv
DOCKER_DIR := setup/docker_images

# creds
MYSQL_ROOT_PASSWORD ?= P@ssw0rd1!
MYSQL_ROOT_USER ?= root
REDIS_USER ?= default
REDIS_PASSWORD ?= P@ssw0rd1!
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

	@echo "=================================================="
	@echo "Starting docker images..."
	@echo "=================================================="

	# https://hub.docker.com/_/mysql
	sudo docker run --name C2_mysql -p 0.0.0.0:3306:3306 -p 127.0.0.1:33060:33060 -e MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) -d mysql:latest

	# https://hub.docker.com/_/redis
	@echo "Redis insights is on, Access at <IP>:8001"
	#8001: Redis Insight. Enabled for dev, can disable/put on localhost for prod.
	sudo docker run -d --name C2_redis-stack -p 127.0.0.1:6379:6379 -p 0.0.0.0:8001:8001 -e REDIS_ARGS="--requirepass $(REDIS_PASSWORD)" redis/redis-stack:latest

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
	echo MYSQL_HOST=localhost >> .env
	echo MYSQL_ROOT_USER=$(MYSQL_ROOT_USER) >> .env
	echo MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) >> .env
	echo MYSQL_DATABASE=c2_db >> .env

	echo REDIS_HOST=localhost >> .env
	echo REDIS_USER=$(REDIS_USER) >> .env
	echo REDIS_PASSWORD=$(REDIS_PASSWORD) >> .env

	@echo "=================================================="
	@echo "Final Steps:"
	@echo "=================================================="

	@echo "REDIS:"
	@echo "\tServer: 127.0.0.1:6379"
	@echo "\tInsights: 0.0.0.0:8001"
	@echo ""

	@echo "MYSQL:"
	@echo "\tDB: 127.0.0.1:3306"
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

	-sudo docker rmi mysql:latest
	-sudo docker rmi redis-stack:latest

	@echo "=================================================="
	@echo "Removing virtualenv"
	@echo "=================================================="
	rm -rf ./venv

	@echo "=================================================="
	@echo "Removing .env"
	@echo "=================================================="

	@echo "Removing .env"
	-rm .env


.PHONY: docker
create_docker_images:
	@echo "=================================================="
	@echo "Creating docker images"
	@echo "=================================================="
	@for d in $(DOCKER_DIR)/*; do \
		if [ -d "$$d" ]; then \
			img_name=$$(basename $$d); \
			echo "Building $$img_name from $$d"; \
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
