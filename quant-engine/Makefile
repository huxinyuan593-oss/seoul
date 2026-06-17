.PHONY: install test backtest lint clean

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/unit/ -v

test-all:
	python -m pytest tests/ -v

backtest:
	python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001

lint:
	ruff check src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
