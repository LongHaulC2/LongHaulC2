SHELL := /bin/bash

# ---------------------------------------------------------------------------
# LongHaulC2 Documentation — Docusaurus build targets
#
# Requires: Node >= 18, npm
# All targets run from this directory (documentation/).
# ---------------------------------------------------------------------------

NODE_BIN     := node_modules/.bin
DOCUSAURUS   := $(NODE_BIN)/docusaurus
BUILD_DIR    := build

.PHONY: install dev build serve clean deploy help

# Default target
all: build

# ======================================
# Setup
# ======================================

## install: Install npm dependencies (runs automatically as a prereq)
install: package.json
	npm install --prefer-offline
	@touch $(NODE_BIN)/.installed

$(NODE_BIN)/.installed: package.json
	$(MAKE) install

# ======================================
# Development
# ======================================

## dev: Start local dev server with hot reload (http://localhost:3000)
dev: $(NODE_BIN)/.installed
	$(DOCUSAURUS) start

## build: Build the static site to ./build/
build: $(NODE_BIN)/.installed
	$(DOCUSAURUS) build
	# hack to get cname in the build so docs.longhaulc2.com works
	echo docs.longhaulc2.com >> ./build/CNAME
## serve: Build the static site and serve it locally
serve: build
	$(DOCUSAURUS) serve


REPO_DIR = longhaulc2.github.io
TIMESTAMP = $(shell date +"%Y-%m-%d %H:%M:%S")

deploy_to_gh_site: 
	@echo "Deploying docs..."
	
# 1. Clone the repo
	gum spin --show-error --spinner dot --title "Cloning repository..." -- git clone https://github.com/longhaulc2/longhaulc2.github.io $(REPO_DIR)
	
# 2. Build the docs
# We added || (...) to catch the failure, print a red error, and exit
	gum spin --show-error --spinner dot --title "Building docs..." -- make build || \
		(gum style --foreground 196 --bold "Build Failed!"; exit 1)
	
# 3. Swap the old docs for the new build
	gum spin --show-error --spinner dot --title "Staging files..." -- bash -c "rm -rf ./$(REPO_DIR)/docs && cp -r ./build ./$(REPO_DIR)/docs" || \
		(gum style --foreground 196 --bold "Staging Failed!"; exit 1)
	
# 4. Commit and Push
	gum spin --show-error --spinner dot --title "Pushing to remote..." -- bash -c "cd $(REPO_DIR) && git add . && git commit -m 'docs push $(TIMESTAMP)' && git push" || \
		(gum style --foreground 196 --bold "Git Push Failed!"; exit 1)
	
# 5. Cleanup
	gum spin --show-error --spinner dot --title "Cleaning up..." -- rm -rf ./$(REPO_DIR)
	
# Print a nice styled success message
	gum style --foreground 212 --bold "Docs successfully pushed and deployed!"

# ======================================
# Maintenance
# ======================================

## clean: Remove build artifacts (node_modules kept)
clean:
	rm -rf $(BUILD_DIR) .docusaurus

## clean-all: Remove build artifacts AND node_modules
clean-all: clean
	rm -rf node_modules

## deploy: Deploy to GitHub Pages (requires GH_TOKEN or SSH key)
deploy: $(NODE_BIN)/.installed
	$(DOCUSAURUS) deploy

# ======================================
# Help
# ======================================

## help: Show this help message
help:
	@echo ""
	@echo "LongHaulC2 Documentation — Makefile targets"
	@echo "============================================="
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""
	@echo "Examples:"
	@echo "  make dev      # Start hot-reload dev server at http://localhost:3000"
	@echo "  make build    # Build static site to ./build/"
	@echo "  make serve    # Build + serve at http://localhost:3000"
	@echo "  make clean    # Remove build artifacts"
	@echo ""
	@echo "Dev Options:"
	@echo "  make deploy_to_gh_site    # Pull docs repo, build current docs, and push to docs repo"
	@echo ""
