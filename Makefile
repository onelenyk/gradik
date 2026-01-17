.PHONY: help dev build release release-manual clean install test gh-setup

help:
	@echo "Gradik Development Commands"
	@echo ""
	@echo "  make dev            - Start development server"
	@echo "  make build          - Build standalone binary"
	@echo "  make release        - Automated release (requires gh CLI)"
	@echo "  make release-manual - Manual release instructions"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make install        - Install as editable package"
	@echo "  make test           - Test the binary"
	@echo "  make gh-setup       - Install & setup GitHub CLI"
	@echo ""
	@echo "Release example:"
	@echo "  make release VERSION=1.0.0"
	@echo ""

dev:
	./scripts/dev.sh

build:
	./scripts/build.sh

release:
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION required. Usage: make release VERSION=1.0.0"; \
		exit 1; \
	fi
	./scripts/release.sh $(VERSION)

release-manual:
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION required. Usage: make release-manual VERSION=1.0.0"; \
		exit 1; \
	fi
	./scripts/release-manual.sh $(VERSION)

clean:
	rm -rf build dist __pycache__ *.spec *.egg-info
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

install:
	pip install -e .

test:
	@if [ -f dist/gradik ]; then \
		echo "Testing binary..."; \
		./dist/gradik --help > /dev/null && echo "✅ Binary works!"; \
	else \
		echo "❌ Binary not found. Run 'make build' first."; \
		exit 1; \
	fi

gh-setup:
	@echo "Installing GitHub CLI..."
	@if command -v brew &> /dev/null; then \
		brew install gh; \
		echo ""; \
		echo "✅ GitHub CLI installed!"; \
		echo ""; \
		echo "Now authenticate:"; \
		echo "  gh auth login"; \
	else \
		echo "❌ Homebrew not found."; \
		echo ""; \
		echo "Install manually:"; \
		echo "  https://cli.github.com/"; \
	fi
