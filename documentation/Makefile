SHELL := /bin/bash

# ---------------------------------------------------------------------------
# LongHaulC2 Documentation — Docusaurus build targets
#
# Requires: Node >= 18, npm
# All targets run from this directory (documentation/).
# ---------------------------------------------------------------------------

.DEFAULT_GOAL := help

NODE_BIN     := node_modules/.bin
DOCUSAURUS   := $(NODE_BIN)/docusaurus
BUILD_DIR    := build

# Gum helpers (matches root Makefile)
GUM_BORDER = gum style --bold --border rounded --border-foreground "\#a16ae8" --padding "0 2"
GUM_BORDER_SUCCESS = gum style --bold --border double --border-foreground "\#10b981" --padding "0 2"
GUM_BORDER_DANGER = gum style --bold --border rounded --border-foreground "\#ef4444" --padding "0 2"
GUM_SPIN = gum spin --show-error --spinner dot --spinner.foreground "\#10b981"

.PHONY: install dev build serve clean deploy help

# Default target
all: build

# ======================================
# Setup
# ======================================

## install: Install npm dependencies (runs automatically as a prereq)
install: package.json
	@$(GUM_BORDER) "Installing npm dependencies"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Running npm install..." -- \
		npm install --prefer-offline
	@touch $(NODE_BIN)/.installed
	@gum log --level info "Dependencies installed"

$(NODE_BIN)/.installed: package.json
	$(MAKE) install

# ======================================
# Development
# ======================================

## dev: Start local dev server with hot reload (http://localhost:3000)
dev: $(NODE_BIN)/.installed
	@$(GUM_BORDER) "Starting dev server (http://localhost:3000)"
	$(DOCUSAURUS) start

## build: Build the static site to ./build/
build: $(NODE_BIN)/.installed
	@$(GUM_BORDER) "Building static site"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Building docs..." -- \
		$(DOCUSAURUS) build
	# hack to get cname in the build so docs.longhaulc2.com works
	@echo docs.longhaulc2.com >> ./build/CNAME
	@$(GUM_BORDER_SUCCESS) "Build complete — output in ./build/"

## serve: Build the static site and serve it locally
serve: build
	@$(GUM_BORDER) "Serving docs (http://localhost:3000)"
	$(DOCUSAURUS) serve


REPO_DIR = longhaulc2.github.io
TIMESTAMP = $(shell date +"%Y-%m-%d %H:%M:%S")

deploy_to_gh_site:
	@$(GUM_BORDER) "Deploying docs to GitHub Pages"

# 1. Clone the repo
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Cloning repository..." -- \
		git clone https://github.com/longhaulc2/longhaulc2.github.io $(REPO_DIR)

# 2. Build the docs
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Building docs..." -- \
		make build || \
		($(GUM_BORDER_DANGER) "Build Failed!"; exit 1)

# 3. Swap the old docs for the new build
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Staging files..." -- \
		bash -c "rm -rf ./$(REPO_DIR)/docs && cp -r ./build ./$(REPO_DIR)/docs" || \
		($(GUM_BORDER_DANGER) "Staging Failed!"; exit 1)

# 4. Commit and Push
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Pushing to remote..." -- \
		bash -c "cd $(REPO_DIR) && git add . && git commit -m 'docs push $(TIMESTAMP)' && git push" || \
		($(GUM_BORDER_DANGER) "Git Push Failed!"; exit 1)

# 5. Cleanup
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Cleaning up..." -- \
		rm -rf ./$(REPO_DIR)

	@$(GUM_BORDER_SUCCESS) "Docs successfully pushed and deployed!"

# ======================================
# Maintenance
# ======================================

## clean: Remove build artifacts (node_modules kept)
clean:
	@$(GUM_BORDER) "Cleaning build artifacts"
	@rm -rf $(BUILD_DIR) .docusaurus
	@gum log --level info "Build artifacts removed"

## clean-all: Remove build artifacts AND node_modules
clean-all: clean
	@$(GUM_BORDER) "Removing node_modules"
	@rm -rf node_modules
	@gum log --level info "node_modules removed"

## deploy: Deploy to GitHub Pages (requires GH_TOKEN or SSH key)
deploy: $(NODE_BIN)/.installed
	@$(GUM_BORDER) "Deploying to GitHub Pages"
	@gum spin --show-error --spinner dot --spinner.foreground "#10b981" --title "Deploying..." -- \
		$(DOCUSAURUS) deploy
	@$(GUM_BORDER_SUCCESS) "Deployed to GitHub Pages"

# ======================================
# Help
# ======================================

## help: Show this help message
help:
	@echo ""
	@gum style --bold --border rounded --border-foreground "#a16ae8" --padding "1 2" \
		"LongHaulC2 Documentation — Makefile targets" \
		"============================================="
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""
	@gum log --level info "Examples:"
	@echo "  make dev      # Start hot-reload dev server at http://localhost:3000"
	@echo "  make build    # Build static site to ./build/"
	@echo "  make serve    # Build + serve at http://localhost:3000"
	@echo "  make clean    # Remove build artifacts"
	@echo ""
	@gum log --level info "Dev Options:"
	@echo "  make deploy_to_gh_site    # Pull docs repo, build current docs, and push to docs repo"
	@echo ""
