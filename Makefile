.PHONY: up down logs build rebuild

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker-compose build

rebuild:
	docker-compose build --no-cache