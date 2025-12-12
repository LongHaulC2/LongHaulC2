# Simple Makefile

#all: myapp

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
	sudo docker run --name C2_mysql -e MYSQL_ROOT_PASSWORD=my-secret-pw -d mysql:latest

	# https://hub.docker.com/_/redis
	sudo docker run --name C2_redis -d redis:latest


	# create venv
	virtualenv ./venv
	
	@echo "Activate the venv with 'source ./venv/bin/activate'"

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

clean:
	#rm -f myapp

reset: uninstall install
	@echo "=================================================="
	@echo "Everything Reset!"
	@echo "=================================================="

.PHONY: all install uninstall clean
