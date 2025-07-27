# Makefile for project documentation and build tasks

.PHONY: docs docs-serve docs-clean help

# Documentation targets
docs: docs-clean  ## Build HTML documentation
	@echo "Building documentation..."
	mkdocs build
	@echo "Documentation built successfully in site/ directory"

docs-serve: ## Serve documentation locally with auto-reload
	@echo "Starting documentation server..."
	@echo "Visit http://127.0.0.1:8000 to view the documentation"
	mkdocs serve

docs-clean: ## Clean documentation build artifacts
	@echo "Cleaning documentation build artifacts..."
	rm -rf site/
	@echo "Documentation artifacts cleaned"

# Help target
help: ## Show this help message
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
