# Simple Makefile

#all: myapp

VENV_PATH ?= ./venv

# creds
MYSQL_ROOT_PASSWORD ?= P@ssw0rd1!
MYSQL_ROOT_USER ?= root
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
	sudo docker run --name C2_mysql -e MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) -d mysql:latest

	# https://hub.docker.com/_/redis
	sudo docker run --name C2_redis -d redis:latest


	# create venv
	virtualenv $(VENV_PATH)
	
	@echo "Activate the venv with 'source $(VENV_PATH)/bin/activate'"

	# create .env
	echo MYSQL_ROOT_USER=$(MYSQL_ROOT_USER) >> .env
	echo MYSQL_ROOT_PASSWORD=$(MYSQL_ROOT_PASSWORD) >> .env

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
	-sudo docker stop C2_redis
	-sudo docker rm C2_redis

	@echo "Removing Docker images"
	-sudo docker rmi mysql:latest
	-sudo docker rmi redis:latest

	@echo "Removing .env"
	-rm .env

clean:
	#rm -f myapp

reset: uninstall install
	@echo "=================================================="
	@echo "Everything Reset!"
	@echo "=================================================="

.PHONY: all install uninstall clean
