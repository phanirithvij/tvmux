.PHONY: start stop clean test build install save help

NAME         := tvmux
SCRIPT       := ./$(NAME).sh
BUILT_SCRIPT := build/$(NAME)
PREFIX       ?= $(HOME)/.local

# Find all test files
CACHE_DIR  := .cache
TEST_FILES := $(wildcard tests/test_*.sh)

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

start: ## Start recording a tmux session
	@$(SCRIPT) start $(CACHE_DIR)
	@find $(CACHE_DIR) -name "session.cast" | sort | tail -n1 | xargs -I {} ln -sf {} current.cast
	@echo "Recording started. Symlinked to current.cast"

stop: ## Stop the current recording
	@$(SCRIPT) stop
	@echo "Recording stopped"

save: ## Save recording to timestamped file and clean up
	@echo "Saving recording..."
	@$(SCRIPT) stop
	@if [ -L current.cast ]; then \
		DEST=$$(readlink current.cast); \
		FILENAME=$$(date +%Y-%m-%d_%H%M).cast; \
		cp "$$DEST" "./$$FILENAME"; \
		echo "Saved to $$FILENAME"; \
		$(MAKE) clean; \
	else \
		echo "Error: current.cast not found"; \
		exit 1; \
	fi

status: ## Show recording status
	@$(SCRIPT) status

clean: ## Remove cache/temporary files (including current recording)
	@rm -rf $(CACHE_DIR) current.cast $(BUILT_SCRIPT)

# Test target depends on all test files and the runner script
test: ## Run all tests
test: $(TEST_FILES) tests/run.sh
	@tests/run.sh

# Build target - concatenate all sources into a single script
build: ## Build standalone script
build: $(BUILT_SCRIPT)

install: ## Install to PREFIX (default: ~/.local)
install: $(PREFIX)/bin/$(NAME)

$(BUILT_SCRIPT): $(SCRIPT) lib/*.sh
	@echo "Building $(NAME)..."
	@./tvmux.sh build $@

$(PREFIX)/bin/$(NAME): $(BUILT_SCRIPT)
	@echo "Installing $(NAME) to $(PREFIX)/bin"
	@mkdir -p $(PREFIX)/bin
	@install -m 755 $(BUILT_SCRIPT) $(PREFIX)/bin/$(NAME)
	@echo "Installed to $(PREFIX)/bin/$(NAME)"
