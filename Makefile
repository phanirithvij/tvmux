.PHONY: start stop clean test

CACHE_DIR := .cache
SCRIPT := ./tmux_monitor.sh

start:
	@$(SCRIPT) start $(CACHE_DIR)
	@sleep 1
	@find $(CACHE_DIR) -name "session.cast" | sort | tail -n1 | xargs -I {} ln -sf {} current.cast
	@echo "Recording started. Symlinked to current.cast"

stop:
	@$(SCRIPT) stop
	@echo "Recording stopped"

clean:
	@rm -rf $(CACHE_DIR) current.cast
	@echo "Cleaned cache and symlink"

test:
	@asciinema play -s 2 -i 0.1 current.cast