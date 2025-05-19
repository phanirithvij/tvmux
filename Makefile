.PHONY: start stop clean test build install

NAME         := tvmux
SCRIPT       := ./$(NAME).sh
BUILT_SCRIPT := build/$(NAME)
PREFIX       ?= $(HOME)/.local

# Find all test files
CACHE_DIR  := .cache
TEST_FILES := $(wildcard tests/test_*.sh)

start:
	@$(SCRIPT) start $(CACHE_DIR)
	@find $(CACHE_DIR) -name "session.cast" | sort | tail -n1 | xargs -I {} ln -sf {} current.cast
	@echo "Recording started. Symlinked to current.cast"

stop:
	@$(SCRIPT) stop
	@echo "Recording stopped"
status:
	@$(SCRIPT) status

clean:
	@rm -rf $(CACHE_DIR) current.cast $(BUILT_SCRIPT)

# Test target depends on all test files and the runner script
test: $(TEST_FILES) tests/run_all.sh
	@tests/run_all.sh

# Build target - concatenate all sources into a single script
build: $(BUILT_SCRIPT)
install: $(PREFIX)/bin/$(NAME)

$(BUILT_SCRIPT): $(SCRIPT) lib/*.sh
	@echo "Building $(NAME)..."
	@mkdir -p build
	@# Use bash debug tracing to output everything, then filter out shebangs and source lines
	@echo "#!/bin/bash" > $(BUILT_SCRIPT)
	@echo "" >> $(BUILT_SCRIPT)
	@PS4="8======D ~ ~ ~ ~" bash -xv -c 'source $(SCRIPT)' 2>&1 | \
	  grep -v "8======D ~ ~ ~ ~" | grep -Ev '^(#|source )' >> $(BUILT_SCRIPT)
	@chmod +x $(BUILT_SCRIPT)
	@echo "Built $(BUILT_SCRIPT)"

$(PREFIX)/bin/$(NAME): $(BUILT_SCRIPT)
	@echo "Installing $(NAME) to $(PREFIX)/bin"
	@mkdir -p $(PREFIX)/bin
	@install -m 755 $(BUILT_SCRIPT) $(PREFIX)/bin/$(NAME)
	@echo "Installed to $(PREFIX)/bin/$(NAME)"
