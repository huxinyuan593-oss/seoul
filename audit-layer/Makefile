.PHONY: install test lint clean

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/unit/ -v

test-all:
	python -m pytest tests/ -v --cov=src

lint:
	ruff check src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
