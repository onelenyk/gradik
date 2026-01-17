.PHONY: help dev build release clean install test

help:
	@echo "Gradik Development Commands"
	@echo ""
	@echo "  make dev       - Start development server"
	@echo "  make build     - Build standalone binary"
	@echo "  make release   - Create release (GitHub Actions builds it)"
	@echo "  make clean     - Clean build artifacts"
	@echo "  make install   - Install as editable package"
	@echo "  make test      - Test the binary"
	@echo ""
	@echo "Release example:"
	@echo "  make release VERSION=1.0.0"
	@echo ""
	@echo "GitHub Actions will automatically build & upload!"
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
