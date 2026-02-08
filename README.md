# Fecapass - Face Recognition Service

Fecapass - это сервис распознавания лиц с модульной Docker-архитектурой, построенный на FastAPI, PostgreSQL (с pgvector), Redis и Celery.

## Архитектура

Система состоит из 5 Docker контейнеров:

- **db_main** - PostgreSQL 16 для основных данных
- **db_vector** - PostgreSQL с pgvector для векторных представлений лиц
- **redis** - Redis для кэширования и Celery broker
- **app** - FastAPI приложение (REST API)
- **worker** - Celery workers для асинхронной обработки

## Структура проекта

```
fecapass/
├── app/                    # FastAPI приложение
│   ├── main.py            # Точка входа приложения
│   ├── api/               # API endpoints
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py    # Health check
│   │   │   │   └── faces.py     # Face endpoints
│   │   │   └── router.py
│   │   └── deps.py        # Dependency injection
│   └── schemas/           # Pydantic схемы
│       └── face.py
├── core/                  # Ядро системы
│   ├── config.py         # Конфигурация
│   ├── database.py       # Подключения к БД
│   └── s3.py             # S3 клиент
├── models/               # SQLAlchemy модели
│   ├── user.py
│   └── face.py
├── services/             # Бизнес-логика
├── workers/              # Celery задачи
│   ├── celery_app.py
│   └── tasks.py
├── scripts/              # Утилиты
│   └── init_db.py       # Инициализация БД
├── tests/               # Тесты
│   ├── unit/
│   └── property/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd fecapass
```

### 2. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните необходимые значения:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл, указав:
- Пароли для PostgreSQL
- Credentials для Beget S3
- Другие настройки при необходимости

### 3. Запуск всех сервисов

```bash
docker-compose up -d
```

Эта команда:
- Соберет Docker образы
- Запустит все контейнеры
- Дождется готовности баз данных и Redis (health checks)

### 4. Инициализация баз данных

После запуска контейнеров выполните скрипт инициализации:

```bash
docker-compose exec app python scripts/init_db.py
```

Этот скрипт:
- Создаст расширение pgvector в векторной БД
- Создаст все необходимые таблицы

### 5. Проверка работоспособности

Откройте в браузере или выполните curl:

```bash
curl http://localhost:8000/
```

Проверьте health check:

```bash
curl http://localhost:8000/api/v1/health
```

Документация API (Swagger):

```
http://localhost:8000/docs
```

## Основные команды

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f app
docker-compose logs -f worker
```

### Остановка сервисов

```bash
# Остановить без удаления контейнеров
docker-compose stop

# Остановить и удалить контейнеры
docker-compose down

# Остановить и удалить контейнеры + volumes (УДАЛИТ ДАННЫЕ!)
docker-compose down -v
```

### Перезапуск сервисов

```bash
# Перезапустить все
docker-compose restart

# Перезапустить конкретный сервис
docker-compose restart app
```

### Масштабирование workers

```bash
docker-compose up -d --scale worker=3
```

### Выполнение команд внутри контейнера

```bash
# Запустить bash в контейнере app
docker-compose exec app bash

# Выполнить Python скрипт
docker-compose exec app python scripts/init_db.py

# Запустить тесты
docker-compose exec app pytest
```

### Пересборка образов

```bash
# Пересобрать все образы
docker-compose build

# Пересобрать конкретный сервис
docker-compose build app

# Пересобрать и запустить
docker-compose up -d --build
```

## Разработка

### Локальная разработка без Docker

1. Создайте виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите PostgreSQL и Redis локально или через Docker:

```bash
docker-compose up -d db_main db_vector redis
```

4. Запустите приложение:

```bash
uvicorn app.main:app --reload
```

5. Запустите Celery worker:

```bash
celery -A workers.celery_app worker --loglevel=info
```

### Запуск тестов

```bash
# Все тесты
pytest

# Unit тесты
pytest tests/unit/

# Property тесты
pytest tests/property/

# С покрытием кода
pytest --cov=. --cov-report=html
```

## API Endpoints

### Health Check

```bash
GET /api/v1/health
```

Проверяет подключение к базам данных и Redis.

### Face Recognition (в разработке)

```bash
# Загрузка лица
POST /api/v1/faces/upload

# Поиск похожих лиц
POST /api/v1/faces/search
```

## Конфигурация

Все настройки управляются через переменные окружения в `.env` файле:

### База данных

- `POSTGRES_USER` - пользователь PostgreSQL
- `POSTGRES_PASSWORD` - пароль PostgreSQL
- `POSTGRES_DB` - имя основной БД
- `VECTOR_POSTGRES_DB` - имя векторной БД

### S3 Storage (Beget)

- `S3_ENDPOINT` - endpoint Beget S3
- `S3_ACCESS_KEY` - access key
- `S3_SECRET_KEY` - secret key
- `S3_BUCKET` - имя bucket

### Redis & Celery

- `REDIS_HOST` - хост Redis
- `REDIS_PORT` - порт Redis
- `CELERY_BROKER_URL` - URL брокера (опционально)

### Face Recognition

- `FACE_DETECTION_THRESHOLD` - порог детекции лица (0.0-1.0)
- `FACE_SIMILARITY_THRESHOLD` - порог схожести (0.0-1.0)
- `EMBEDDING_DIMENSION` - размерность векторов (512)

## Troubleshooting

### Контейнеры не запускаются

Проверьте логи:
```bash
docker-compose logs
```

### Ошибки подключения к БД

Убедитесь, что health checks проходят:
```bash
docker-compose ps
```

Все сервисы должны быть в статусе "healthy".

### Ошибки при инициализации БД

Проверьте, что переменные окружения заданы правильно:
```bash
docker-compose exec app env | grep POSTGRES
```

### Celery worker не обрабатывает задачи

Проверьте логи worker:
```bash
docker-compose logs -f worker
```

Убедитесь, что Redis доступен:
```bash
docker-compose exec worker redis-cli -h redis ping
```

## Production Deployment

Для production окружения рекомендуется:

1. **Использовать secrets management** вместо .env файлов
2. **Настроить SSL/TLS** для всех соединений
3. **Использовать managed PostgreSQL** вместо контейнеров
4. **Настроить мониторинг** (Prometheus + Grafana)
5. **Настроить централизованное логирование** (ELK stack)
6. **Использовать reverse proxy** (Nginx/Traefik) перед app
7. **Настроить автоматические бэкапы** баз данных
8. **Сканировать образы** на уязвимости

## Лицензия

[Укажите лицензию проекта]

## Контакты

[Укажите контактную информацию]
