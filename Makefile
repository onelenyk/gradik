.PHONY: help dev build release clean install test

help:
	@echo "Gradik Development Commands"
	@echo ""
	@echo "  make dev       - Start development server"
	@echo "  make build     - Build standalone binary"
	@echo "  make release   - Prepare release (build + test)"
	@echo "  make clean     - Clean build artifacts"
	@echo "  make install   - Install as editable package"
	@echo "  make test      - Test the binary"
	@echo ""

dev:
	./scripts/dev.sh

build:
	./scripts/build.sh

release:
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
