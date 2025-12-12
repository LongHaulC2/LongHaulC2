# Simple Makefile

#all: myapp

VENV_PATH ?= ./venv

# creds
MYSQL_ROOT_PASSWORD ?= P@ssw0rd1!
MYSQL_ROOT_USER ?= root
REDIS_PASSWORD ?= P@ssw0rd1!
# can specify creds manually with:
#make install MYSQL_ROOT_PASSWORD=SuperSecure123

install:
	@echo "=================================================="
	@echo "Installing..."
	@echo "=================================================="

	sudo apt-get update
	sudo apt-get install python3 python3-pip virtualenv docker.io redis-tools postgresql-client -y

	# docker install
	sudo docker pull mysql:latest
	sudo docker pull redis:latest

	# docker start

	# https://hub.docker.com/_/mysql
	sudo docker run --name C2_mysql -p 127.0.0.1:3306:3306 -p 127.0.0.1:33060:33060 -e MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) -d mysql:latest

	# https://hub.docker.com/_/redis
	@echo "Redis insights is on, Access at <IP>:8001"
	#8001: Redis Insight. Enabled for dev, can disable/put on localhost for prod.
	sudo docker run -d --name C2_redis-stack -p 127.0.0.1:6379:6379 -p 0.0.0.0:8001:8001 -e REDIS_ARGS="--requirepass $(REDIS_PASSWORD)" redis/redis-stack:latest


	# create venv
	virtualenv $(VENV_PATH)
	
	@echo "Activate the venv with 'source $(VENV_PATH)/bin/activate'"

	# create .env
	echo MYSQL_ROOT_USER=$(MYSQL_ROOT_USER) >> .env
	echo MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) >> .env
	echo REDIS_PASSWORD=$(REDIS_PASSWORD) >> .env

uninstall:
	@echo "=================================================="
	@echo "Uninstalling..."
	@echo "=================================================="

	#rm -f /usr/local/bin/myapp

	@echo "Removing virtualenv"
	rm -rf ./venv

	@echo "Removing docker containers"

	@echo "Stopping and removing Docker containers"
	-sudo docker stop C2_mysql
	-sudo docker rm C2_mysql
	-sudo docker stop C2_redis-stack
	-sudo docker rm C2_redis-stack

	@echo "Removing Docker images"
	-sudo docker rmi mysql:latest
	-sudo docker rmi redis-stack:latest

	@echo "Removing .env"
	-rm .env

clean:
	#rm -f myapp

reset: uninstall install
	@echo "=================================================="
	@echo "Everything Reset!"
	@echo "=================================================="

.PHONY: all install uninstall clean
