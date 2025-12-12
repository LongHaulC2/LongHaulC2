# Simple Makefile

#all: myapp

install:
	@echo "=================================================="
	@echo "Installing..."
	@echo "=================================================="

	sudo apt-get update
	sudo apt-get install python3 python3-pip virtualenv docker.io -y

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

clean:
	#rm -f myapp

reset: uninstall install
	@echo "=================================================="
	@echo "Everthing Reset!"
	@echo "=================================================="

.PHONY: all install uninstall clean
