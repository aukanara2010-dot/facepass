# Архитектура FacePass — Текущее состояние системы

> **Версия приложения:** 2.0.0  
> **Язык:** Python 3.12  
> **Дата актуализации:** 08.04.2026  
> **Основано на:** реальном коде проекта + мастер-документе + данных стресс-теста 06–07.04.2026

---

## 1. Технологический стек

| Компонент | Технология | Версия/Детали |
|---|---|---|
| Язык | Python | 3.12 |
| API-фреймворк | FastAPI | — |
| Очередь задач | Celery + Redis | Redis 7 Alpine |
| База данных | PostgreSQL + pgvector | ankane/pgvector |
| Нейронная сеть | InsightFace buffalo_l | CPU-only, 512-мерные эмбеддинги |
| Хранилище фото | Beget S3 (boto3) | 0.07 ₽/ГБ/день |
| Веб-сервер | NGINX | reverse proxy |
| Менеджер процессов | PM2 | управление FastAPI + Celery |
| Мониторинг | Prometheus | порт 9090 |
| Логирование | structlog | JSON-формат |
| Деплой | Docker Compose | один сервер |

---

## 2. Общая схема системы

```
                    ┌─────────────────────────────────────────────────────┐
                    │                  ОДИН СЕРВЕР                        │
                    │              (16 CPU, 32 GB RAM)                    │
                    │                                                     │
  Клиент ──HTTP──▶  │  ┌──────────┐     ┌─────────────────────────────┐  │
                    │  │  NGINX   │────▶│  FastAPI (port 8000)        │  │
                    │  │ (proxy)  │     │  + Rate Limiting             │  │
                    │  └──────────┘     │  + API Key Auth              │  │
                    │                  │  + structlog (JSON)           │  │
                    │                  └──────────┬──────────────────┬─┘  │
                    │                             │                  │    │
                    │                    async    │          sync    │    │
                    │                    task     │          query   │    │
                    │                             ▼                  ▼    │
                    │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐│
                    │  │    Redis     │  │   Celery     │  │ PostgreSQL ││
                    │  │  (broker)    │─▶│  Workers     │  │ + pgvector ││
                    │  │  port 6379   │  │  (2–4 шт.)   │  │ port 5432  ││
                    │  └──────────────┘  └──────┬───────┘  └────────────┘│
                    │                           │                         │
                    │  ┌──────────────┐         │ InsightFace             │
                    │  │  Prometheus  │         │ buffalo_l               │
                    │  │  port 9090   │         │ (нейросеть)             │
                    │  └──────────────┘         │                         │
                    └───────────────────────────┼─────────────────────────┘
                                                │
                                                ▼
                                  ┌─────────────────────────┐
                                  │      Beget S3           │
                                  │   Object Storage        │
                                  │   0.07 ₽/ГБ/день        │
                                  └─────────────────────────┘
```

---

## 3. Компоненты системы

### 3.1 NGINX (входная точка)
- Принимает все HTTP-запросы снаружи
- Проксирует на FastAPI (порт 8000)
- Конфиг: `/etc/nginx/sites-available/facepass.pixorasoft.ru`

### 3.2 PM2 (менеджер процессов)
- Управляет запуском и перезапуском FastAPI и Celery workers
- Обеспечивает автозапуск при перезагрузке сервера
- **Важно:** Celery worker **не описан в docker-compose.yml** — запускается через PM2 отдельно

### 3.3 FastAPI (API-сервер)
- **Запуск:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Аутентификация:** API-ключи (`app/middleware/auth.py`)
- **Rate limiting:** slowapi (`app/middleware/rate_limit.py`)
- **Логирование:** structlog (JSON-формат)
- **Инициализация:** при старте загружает модель InsightFace buffalo_l в память (~6–8 ГБ RAM)

### 3.4 Redis (очередь задач)
- **Образ:** `redis:7-alpine`
- **Режим:** одиночный (без репликации — единая точка отказа)
- **Роль:** брокер сообщений для Celery
- **Persistence:** AOF (`appendonly yes`) — данные сохраняются при перезапуске

### 3.5 Celery Workers (фоновая обработка)
- **Конкурентность:** `min(4, max(2, cpu_count // 2))` → на 16-ядерном сервере = **4 воркера**
- **Задача:** `sync_s3_photos_task(session_id)` — скачать фото из S3, извлечь эмбеддинги, сохранить в БД
- **Результаты:** игнорируются (`task_ignore_result=True`) — важны только side-effects (запись в БД)
- **Нет DLQ:** упавшие задачи теряются без возможности повтора

### 3.6 PostgreSQL + pgvector (база данных)
- **Образ:** `ankane/pgvector:latest`
- **Таблица:** `face_embeddings`
- **Хранит:** 512-мерные float32 векторы (эмбеддинги лиц)
- **Поиск:** косинусное сходство через pgvector (`<=>` оператор)
- **Идемпотентность:** повторная индексация одного фото обновляет существующий эмбеддинг

```sql
CREATE TABLE face_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id    VARCHAR NOT NULL,
    session_id  VARCHAR NOT NULL,
    embedding   VECTOR(512) NOT NULL,
    confidence  FLOAT,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (photo_id, session_id)
);
```

### 3.7 InsightFace buffalo_l (нейронная сеть)
- **Что делает:** детектирует лица, извлекает 512-мерный эмбеддинг
- **Режим:** CPU-only (нет GPU-ускорения)
- **Загрузка:** при старте приложения (warm-up ~6–8 ГБ RAM)
- **Производительность:** ~9–11 сек на задачу при нагрузке (из стресс-теста)
- **Настройки:** `FACE_DETECTION_THRESHOLD`, `FACE_SIMILARITY_THRESHOLD`, `EMBEDDING_DIMENSION`

### 3.8 Beget S3 (хранилище фотографий)
- **Клиент:** boto3 (AWS SDK)
- **Тариф:** 0.07 ₽/ГБ/день
- **Структура ключей:**
  ```
  {S3_ENV_PREFIX}/photos/{session_id}/originals/  — оригинальные фото
  {S3_ENV_PREFIX}/photos/{session_id}/previews/   — превью для отображения
  ```
- **Поддерживаемые форматы:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.heif`
- **Окружения:** staging / production (переключается через `S3_ENV_PREFIX`)

---

## 4. API-эндпоинты

| Метод | Путь | Авторизация | Rate Limit | Описание |
|---|---|---|---|---|
| `POST` | `/api/v1/index` | ✅ API Key | ✅ | Индексировать одно фото (файл или S3-ключ) |
| `POST` | `/api/v1/index/batch` | ✅ API Key | ✅ | Пакетная индексация нескольких фото |
| `DELETE` | `/api/v1/index/{session_id}` | ✅ API Key | ✅ | Удалить все эмбеддинги сессии |
| `GET` | `/api/v1/search/status/{session_id}` | ❌ | ❌ | Статус индексации сессии |
| `POST` | `/api/v1/search` | ❌ | ✅ | Найти похожие лица по селфи |
| `GET` | `/api/v1/health` | ❌ | ❌ | Проверка состояния сервиса |
| `GET` | `/api/v1/metrics` | ❌ | ❌ | Метрики Prometheus |

---

## 5. Потоки данных

### 5.1 Индексация одного фото

```
Клиент
  │ POST /api/v1/index
  │ (photo_id, session_id, file или s3_key)
  ▼
NGINX ──▶ FastAPI
              ├─ Проверка API-ключа
              ├─ Rate limit check
              ├─ Валидация файла (формат, размер)
              ├─ [если file] S3: upload_image()
              ├─ [если s3_key] S3: download_image()
              ├─ InsightFace: extract_embedding() → vector[512], confidence
              ├─ Нормализация вектора (L2 norm)
              ├─ PostgreSQL: INSERT/UPDATE face_embeddings (идемпотентно)
              └─ Response: {success, confidence, faces_detected}
```

### 5.2 Массовая синхронизация из S3 (фоновая)

```
Клиент
  │ POST /api/v1/sync-s3 {session_id}
  ▼
FastAPI
  ├─ sync_s3_photos_task.delay(session_id) → Redis queue
  └─ Response: {task_id, status: "queued"}

              Асинхронно — Celery Worker:
              ├─ S3: list_objects(prefix=session_id/originals/)
              └─ Для каждого нового фото:
                  ├─ S3: download_image()
                  ├─ InsightFace: extract_embedding()
                  └─ PostgreSQL: INSERT/UPDATE face_embeddings
```

### 5.3 Поиск по лицу (с Lazy Indexing)

```
Клиент
  │ POST /api/v1/search
  │ (selfie_file, session_id, threshold, limit)
  ▼
FastAPI
  ├─ InsightFace: extract_embedding(selfie) → query_vector[512]
  ├─ PostgreSQL: COUNT(*) WHERE session_id = ?
  │
  ├─ [Нет индексированных фото]
  │   ├─ sync_s3_photos_task.delay(session_id)  ← запуск индексации
  │   └─ Response: 404 "Not indexed yet, retry later"
  │
  └─ [Есть индексированные фото]
      ├─ sync_s3_photos_task.delay(session_id)  ← fire-and-forget (новые фото)
      ├─ PostgreSQL: SELECT * ORDER BY embedding <=> query_vector LIMIT ?
      └─ Response: [{photo_id, similarity, confidence, url}, ...]
```

> **Lazy Indexing** — ключевой паттерн системы: индексация запускается автоматически при первом поисковом запросе, не требуя явного вызова. Новые фото в S3 подхватываются при каждом поиске в фоне.

---

## 6. Механизм Lazy Indexing (подробно)

```
Первый поиск в сессии:
  Клиент ──▶ /search ──▶ БД пуста ──▶ 404 + запуск индексации в фоне
  Клиент ──▶ /search (через ~30 сек) ──▶ БД заполнена ──▶ результаты

Последующие поиски:
  Клиент ──▶ /search ──▶ результаты из БД (быстро, ~200 мс)
                       + фоновая синхронизация новых фото из S3
```

**Преимущества:**
- Быстрый отклик (~200 мс) для поиска — не ждёт S3
- Новые фото становятся доступными автоматически
- Идемпотентность — повторный запуск задачи безопасен

**Риски:**
- Первый поиск всегда возвращает 404 — клиент должен уметь повторять запрос
- Нет DLQ — если задача упала, новые фото не проиндексируются

---

## 7. Карта кода

```
facepass/
├── app/
│   ├── main.py                    — FastAPI app, middleware, startup
│   ├── api/v1/
│   │   ├── router.py              — регистрация маршрутов
│   │   └── endpoints/
│   │       └── indexing.py        — все эндпоинты (746 строк)
│   ├── middleware/
│   │   ├── auth.py                — проверка API-ключей
│   │   └── rate_limit.py          — ограничение запросов (slowapi)
│   ├── schemas/
│   │   └── indexing.py            — Pydantic-модели запросов/ответов
│   └── utils/
│       └── validation.py          — валидация входных данных
│
├── core/
│   ├── config.py                  — Settings (pydantic-settings, lru_cache)
│   ├── celery_app.py              — Celery конфигурация, concurrency=4
│   ├── database.py                — SQLAlchemy + pgvector подключение
│   └── s3.py                      — boto3 клиент для Beget S3
│
├── services/
│   ├── face_recognition.py        — InsightFace buffalo_l, extract_embedding()
│   ├── indexing.py                — IndexingService, load_embeddings_from_s3()
│   ├── photo_indexing.py          — высокоуровневые workflow обработки фото
│   └── tasks.py                   — Celery task: sync_s3_photos_task()
│
├── models/
│   └── face.py                    — FaceEmbedding ORM-модель (pgvector)
│
├── docker-compose.yml             — db_vector, redis, app, prometheus
├── Dockerfile                     — образ приложения
├── prometheus.yml                 — конфигурация Prometheus
└── .env                           — переменные окружения (не в git)
```

---

## 8. Docker Compose — текущая конфигурация

```yaml
services:
  db_vector:    # PostgreSQL + pgvector, порт 5432
  redis:        # Redis 7 Alpine, порт 6379, AOF persistence
  app:          # FastAPI + uvicorn, порт 8000
  prometheus:   # Prometheus, порт 9090
```

> ⚠️ **Celery worker НЕ в docker-compose** — запускается через PM2 отдельно.  
> При `docker-compose up` воркеры не поднимаются автоматически.

---

## 9. Конфигурация (переменные окружения)

| Переменная | Обязательная | Описание |
|---|---|---|
| `POSTGRES_USER` | ✅ | Пользователь БД |
| `POSTGRES_PASSWORD` | ✅ | Пароль БД |
| `POSTGRES_DB` | ✅ | Имя базы данных |
| `POSTGRES_HOST` | — | Хост БД (default: `db_vector`) |
| `REDIS_HOST` | — | Хост Redis (default: `redis`) |
| `REDIS_PORT` | — | Порт Redis (default: `6379`) |
| `S3_ENDPOINT` | ✅ | URL Beget S3 |
| `S3_ACCESS_KEY` | ✅ | Ключ доступа S3 |
| `S3_SECRET_KEY` | ✅ | Секретный ключ S3 |
| `S3_BUCKET` | ✅ | Имя бакета |
| `S3_REGION` | — | Регион (default: `ru-1`) |
| `S3_ENV_PREFIX` | — | Префикс среды (default: `staging`) |
| `API_KEYS` | — | Список API-ключей через запятую |
| `FACE_DETECTION_THRESHOLD` | — | Порог уверенности детекции лица |
| `FACE_SIMILARITY_THRESHOLD` | — | Порог схожести при поиске |
| `EMBEDDING_DIMENSION` | — | Размерность вектора (default: 512) |
| `CORS_ORIGINS` | — | Разрешённые CORS-источники |

---

## 10. Что показал стресс-тест (06–07.04.2026)

| Метрика | Значение |
|---|---|
| Длительность | 29 ч 17 мин |
| Объектов загружено в S3 | 759 010 |
| Объём данных | ~4 ТБ |
| Пиковая нагрузка CPU | 44.9% (7.2 из 16 ядер) |
| Пиковое потребление RAM | 11.04 ГБ (35.2% из 32 ГБ) |
| Утечки памяти | **Нет** (плато после warm-up) |
| Критических отказов | **0** |
| Точка насыщения | point_index=7 → avg_runtime 0→9.39 сек |
| Реальный RPS обработки лиц | **0** (аномалия — воркеры не обрабатывали) |
| Запас CPU | ~55% свободно |
| Запас RAM | ~65% свободно (20.96 ГБ) |

---

## 11. Известные проблемы и технический долг

| # | Проблема | Критичность | Где исправить |
|---|---|---|---|
| 1 | Celery worker не в docker-compose — не поднимается автоматически без PM2 | 🔴 Высокая | `docker-compose.yml` |
| 2 | Нет Dead Letter Queue — упавшие задачи теряются | 🔴 Высокая | `core/celery_app.py` |
| 3 | Redis без репликации — единая точка отказа | 🔴 Высокая | `docker-compose.yml` |
| 4 | `total_completed_tasks` в мониторинге заморожен — нет реального RPS обработки | 🔴 Высокая | `one_day_marathon.py` |
| 5 | Нет Circuit Breaker — при переполнении очереди API продолжает принимать задачи | 🟠 Средняя | `app/api/v1/endpoints/indexing.py` |
| 6 | `task_ignore_result=True` — нет возможности отследить статус задачи через API | 🟠 Средняя | `core/celery_app.py` |
| 7 | `network_io` метрика сломана (отрицательные значения) | 🟠 Средняя | `one_day_marathon.py` |
| 8 | Нет партиционирования PostgreSQL — при >1M строк поиск замедлится | 🟡 Низкая | `models/face.py` |
| 9 | Нет S3 Lifecycle Policy — объём хранилища растёт бесконечно | 🟡 Низкая | Beget S3 консоль |

---

## 12. Целевая архитектура при масштабировании

```
                    ┌─────────────────────┐
                    │   Load Balancer     │
                    │  (NGINX / HAProxy)  │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │ FacePass #1  │   │ FacePass #2  │   │ FacePass #3  │
  │ FastAPI      │   │ FastAPI      │   │ FastAPI      │
  │ + Workers    │   │ + Workers    │   │ + Workers    │
  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
         └──────────────────┼──────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Redis Cluster│  │  PostgreSQL  │  │  Beget S3    │
│ (3 ноды)     │  │  Primary +   │  │  + Lifecycle │
│              │  │  2 Replicas  │  │  Policy      │
└──────────────┘  └──────────────┘  └──────────────┘
```

Подробнее: [`plans/FacePass_Cluster_Architecture_RU.md`](plans/FacePass_Cluster_Architecture_RU.md)

---

## 13. Связанные документы

| Документ | Описание |
|---|---|
| [`plans/FacePass_Master_Design_Document_RU.md`](plans/FacePass_Master_Design_Document_RU.md) | Мастер-документ проекта (детальная бизнес-логика) |
| [`plans/FacePass_Highload_Stress_Report.md`](plans/FacePass_Highload_Stress_Report.md) | Технический отчёт по стресс-тесту |
| [`plans/FacePass_Business_Report.md`](plans/FacePass_Business_Report.md) | Бизнес-отчёт для заказчика |
| [`plans/FacePass_Cluster_Architecture_RU.md`](plans/FacePass_Cluster_Architecture_RU.md) | Архитектура кластера (целевое состояние) |
| [`plans/FacePass_Performance_Analysis_RU.md`](plans/FacePass_Performance_Analysis_RU.md) | Анализ производительности |
