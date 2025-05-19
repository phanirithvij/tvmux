.PHONY: start stop clean test

CACHE_DIR := .cache
SCRIPT := ./tmux_monitor.sh

# Find all test files
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
	@rm -rf $(CACHE_DIR) current.cast
	@echo "Cleaned cache and symlink"

# Test target depends on all test files and the runner script
test: $(TEST_FILES) tests/run_all.sh
	@tests/run_all.sh
