.PHONY: help install dev prod stop clean logs test

help:
	@echo "AI Bot Platform - Make commands"
	@echo ""
	@echo "make install    - Установить и запустить (продакшн)"
	@echo "make dev        - Запустить в режиме разработки"
	@echo "make prod       - Запустить в продакшн режиме"
	@echo "make stop       - Остановить все сервисы"
	@echo "make clean      - Удалить все данные и контейнеры"
	@echo "make logs       - Показать логи"
	@echo "make restart    - Перезапустить сервисы"

install:
	@cp docker/.env.example docker/.env
	@echo "Отредактируйте docker/.env перед продолжением"
	@read -p "Продолжить? (y/n) " -n 1 -r; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then exit 1; fi
	docker-compose -f docker/docker-compose.yml up -d
	@echo "Готово! Откройте http://localhost"

dev:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d

prod:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d

stop:
	docker-compose -f docker/docker-compose.yml stop

clean:
	docker-compose -f docker/docker-compose.yml down -v --remove-orphans
	docker volume rm ai-bot-platform_postgres_data ai-bot-platform_redis_data 2>/dev/null || true

logs:
	docker-compose -f docker/docker-compose.yml logs -f

restart:
	docker-compose -f docker/docker-compose.yml restart

status:
	docker-compose -f docker/docker-compose.yml ps
