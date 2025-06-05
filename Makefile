# Makefile for ID Generator
# =========================

PYTHON := python3
SCRIPT := scripts/generate_ids.py
DATA_FILE := tests/data.yaml
TARGET := matrices
PREFLABEL := label
TYPE_PREFIX := MA
OUTPUT_FILE := output.yaml
NAMESPACE:= https://w3id.org/peh/

# Default target
.PHONY: help
help:
	@echo "ID Generator Makefile"
	@echo "===================="
	@echo ""
	@echo "Available targets:"
	@echo "  test-run       - Dry run to preview changes"
	@echo "  run            - Generate IDs and update file"
	@echo "  run-new        - Generate IDs to new output file"
	@echo "  help           - Show this help message"
	@echo ""
	@echo "Variables (customize at top of Makefile):"
	@echo "  DATA_FILE      = $(DATA_FILE)"
	@echo "  TARGET         = $(TARGET)"
	@echo "  PREFLABEL      = $(PREFLABEL)"
	@echo "  TYPE_PREFIX    = $(TYPE_PREFIX)"

# Test run - dry run with verbose output
.PHONY: test-run
test-run:
	@echo "Running dry run preview..."
	$(PYTHON) $(SCRIPT) \
		--data $(DATA_FILE) \
		--target $(TARGET) \
		--preflabel $(PREFLABEL) \
		--type-prefix $(TYPE_PREFIX) \
		--parent-key parent_matrix \
		--namespace $(NAMESPACE) \
		--dry-run \
		--verbose

# Actual run - updates the original file
.PHONY: run
run:
	@echo "Generating IDs and updating $(DATA_FILE)..."
	$(PYTHON) $(SCRIPT) \
		--data $(DATA_FILE) \
		--target $(TARGET) \
		--preflabel $(PREFLABEL) \
		--type-prefix $(TYPE_PREFIX) \
		--parent-key parent_matrix \
		--namespace $(NAMESPACE) \
		--verbose

# Run with new output file
.PHONY: run-new
run-new:
	@echo "Generating IDs to new file $(OUTPUT_FILE)..."
	$(PYTHON) $(SCRIPT) \
		--data $(DATA_FILE) \
		--target $(TARGET) \
		--preflabel $(PREFLABEL) \
		--type-prefix $(TYPE_PREFIX) \
		--parent-key parent_matrix \
		--namespace $(NAMESPACE) \
		--output $(OUTPUT_FILE) \
		--verbose
