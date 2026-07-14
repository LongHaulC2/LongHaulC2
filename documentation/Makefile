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
