.PHONY: install test lint fmt docker-build docker-test deploy diag

install:
	pip install -e ".[dev,ponte]"

test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff check --fix .
	ruff format .

docker-build:
	docker compose build lab

docker-test:
	docker compose run --rm --entrypoint pytest lab -q

deploy:
	bash infra/vps/deploy.sh

diag:
	bash infra/vps/03-diagnostico.sh
