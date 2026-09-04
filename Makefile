.PHONY: install dev test lint serve benchmark docker-up docker-down

install:
	python -m pip install -r requirements.txt

dev:
	python -m pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check app benchmarks tests

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

benchmark:
	python -m benchmarks.benchmark --requests 16 --concurrency 4

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
