# Requirements Document: Facepass Microservice Isolation

## Introduction

Данный документ описывает требования к архитектурной реорганизации проекта Facepass для перехода от тесно интегрированного сервиса к независимому микросервису распознавания лиц (Face Recognition Engine).

Текущая архитектура имеет жесткую зависимость от внешнего сервиса Pixora (API и база данных), что создает следующие проблемы:
- Невозможность автономной работы сервиса
- Сложность тестирования и развертывания
- Зависимость от доступности внешних систем
- Запутанная логика синхронизации данных

Целью реорганизации является создание изолированного микросервиса, который:
- Работает автономно, используя только photo_id и векторы лиц
- Предоставляет чистый API для индексации и поиска
- Не содержит бизнес-логики Pixora (заказы, корзины, цены)
- Может быть легко интегрирован с любым внешним сервисом

## Glossary

- **Facepass**: Микросервис распознавания лиц для поиска фотографий по селфи
- **Pixora**: Внешний сервис управления фотостудиями (клиент Facepass)
- **Face_Recognition_Engine**: Изолированный сервис индексации и поиска по лицам
- **Vector_Database**: PostgreSQL с pgvector для хранения эмбеддингов лиц
- **Photo_ID**: Уникальный идентификатор фотографии (UUID или timestamp-hash)
- **Embedding**: 512-мерный вектор признаков лица
- **Session_ID**: UUID фотосессии
- **S3_Storage**: Объектное хранилище для фотографий (Beget S3)
- **Sync_Task**: Фоновая задача синхронизации фотографий из Pixora API
- **Main_Database**: Основная БД Facepass (faces, events таблицы)
- **Pixora_Database**: Внешняя БД Pixora (photo_sessions, photos таблицы)
- **CORS_Proxy**: Прокси-эндпоинт для обхода CORS при запросах к Pixora API

## Requirements

### Requirement 1: Анализ текущих зависимостей от Pixora

**User Story:** Как архитектор системы, я хочу получить полный анализ текущих зависимостей от Pixora, чтобы понять объем работ по изоляции сервиса

#### Acceptance Criteria


1. THE Face_Recognition_Engine SHALL identify all direct database connections to Pixora_Database
2. THE Face_Recognition_Engine SHALL identify all API calls to Pixora external services
3. THE Face_Recognition_Engine SHALL identify all background synchronization tasks that depend on Pixora
4. THE Face_Recognition_Engine SHALL document all configuration parameters specific to Pixora integration
5. THE Face_Recognition_Engine SHALL list all data models that reference Pixora-specific entities

**Current Dependencies Identified:**

**Database Dependencies:**
- `core/database.py`: `pixora_engine` - подключение к внешней БД Pixora через `MAIN_APP_DATABASE_URL`
- `core/database.py`: `get_pixora_db()` - dependency для доступа к Pixora БД
- `models/photo_session.py`: `PhotoSession` модель - читает из `photo_sessions` таблицы Pixora
- Запросы к таблице `public.photos` в Pixora БД для получения метаданных фотографий

**API Dependencies:**
- `app/main.py`: `/api/v1/remote-services/{session_id}` - CORS прокси к Pixora API
- `core/config.py`: `MAIN_API_URL` - URL Pixora API (https://staging.pixorasoft.ru)
- `app/api/v1/endpoints/faces.py`: `sync_session_photos()` - запросы к `https://staging.pixorasoft.ru/api/session/{session_id}`

**Synchronization Dependencies:**
- `app/api/v1/endpoints/faces.py`: `sync_session_photos()` - фоновая задача синхронизации новых фото из Pixora
- Логика сравнения локальных `photo_id` с фотографиями из Pixora API
- Автоматическая индексация при первом поиске в сессии

**Configuration Dependencies:**
- `MAIN_APP_DATABASE_URL` - строка подключения к Pixora БД
- `MAIN_API_URL` - базовый URL Pixora API
- `DOMAIN`, `STAGING_DOMAIN` - домены для определения окружения

**Data Model Dependencies:**
- `PhotoSession.facepass_enabled` - флаг активации FacePass в Pixora
- `PhotoSession.name` - название сессии из Pixora
- Структура ответа Pixora API: `{"session": {"photos": [...], "photoCount": N}}`
- Поля фотографий: `id`, `file_name`, `filePath`, `preview_path`, `created_at`

### Requirement 2: Изоляция хранения векторов

**User Story:** Как разработчик, я хочу чтобы сервис работал автономно с векторами и photo_id, чтобы не зависеть от внешних баз данных

#### Acceptance Criteria

1. THE Vector_Database SHALL store face embeddings indexed only by photo_id and session_id
2. THE Vector_Database SHALL NOT require connections to external databases for search operations
3. WHEN a search request is received, THE Face_Recognition_Engine SHALL return results using only Vector_Database data
4. THE Face_Recognition_Engine SHALL store minimal metadata (photo_id, session_id, confidence) without Pixora-specific fields
5. THE Vector_Database SHALL support both UUID and timestamp-hash formats for photo_id

**Current Implementation Analysis:**

**Vector Storage (PostgreSQL/pgvector):**
- Таблица: `face_embeddings` в Vector_Database
- Поля: `id`, `face_id`, `photo_id`, `event_id`, `session_id`, `embedding`, `confidence`, `created_at`
- Проблема: `face_id` ссылается на таблицу `faces` в Main_Database
- Проблема: `event_id` - legacy поле для старой архитектуры событий

**Required Changes:**
- Удалить зависимость от `face_id` (сделать nullable или удалить)
- Удалить `event_id` (legacy)
- Оставить только: `photo_id`, `session_id`, `embedding`, `confidence`, `created_at`
- Индексы: `photo_id`, `session_id` для быстрого поиска

### Requirement 3: Чистый API для внешних клиентов

**User Story:** Как внешний клиент (Pixora), я хочу использовать простой API для индексации и поиска, чтобы интегрировать Facepass в свою систему

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL provide POST /api/v1/index endpoint for photo indexing
2. WHEN indexing request is received, THE Face_Recognition_Engine SHALL accept photo_id, session_id, and image_data
3. THE Face_Recognition_Engine SHALL provide POST /api/v1/search endpoint for face search
4. WHEN search request is received, THE Face_Recognition_Engine SHALL return list of photo_id with similarity scores
5. THE Face_Recognition_Engine SHALL NOT expose Pixora-specific endpoints in public API
6. THE Face_Recognition_Engine SHALL NOT return Pixora-specific data (prices, orders, cart information)

**Endpoints to Keep (Clean API):**
- `POST /api/v1/index` - индексация одной фотографии
- `POST /api/v1/index/batch` - пакетная индексация
- `POST /api/v1/search` - поиск по селфи
- `GET /api/v1/index/status/{session_id}` - статус индексации сессии
- `DELETE /api/v1/index/{session_id}` - удаление индексов сессии

**Endpoints to Remove (Pixora-specific):**
- `/api/v1/remote-services/{session_id}` - CORS прокси к Pixora
- `/session/{session_id}` - публичный интерфейс с валидацией через Pixora БД
- Автоматическая синхронизация в `search-session` endpoint

**API Response Format:**
```json
{
  "matches": [
    {
      "photo_id": "uuid-or-timestamp-hash",
      "similarity": 0.95,
      "confidence": 0.87
    }
  ],
  "query_time_ms": 123.45,
  "total_matches": 5
}
```

### Requirement 4: Удаление синхронизации с Pixora

**User Story:** Как администратор системы, я хочу удалить автоматическую синхронизацию с Pixora, чтобы сервис не зависел от доступности внешних API

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL NOT automatically fetch photos from external APIs
2. THE Face_Recognition_Engine SHALL NOT trigger background sync tasks on search requests
3. WHEN a search is performed, THE Face_Recognition_Engine SHALL use only pre-indexed data
4. THE Face_Recognition_Engine SHALL provide manual indexing endpoints for external clients
5. THE Face_Recognition_Engine SHALL NOT validate session existence in external databases

**Code to Remove:**
- `sync_session_photos()` функция в `app/api/v1/endpoints/faces.py`
- `background_tasks.add_task(sync_session_photos, session_id)` в search endpoint
- Запросы к `https://staging.pixorasoft.ru/api/session/{session_id}`
- Логика автоматической индексации при первом поиске
- Проверка `is_indexed` с последующей индексацией

**Responsibility Shift:**
- Внешний клиент (Pixora) отвечает за вызов `/api/v1/index` при добавлении новых фото
- Facepass только хранит и ищет по уже проиндексированным данным


### Requirement 5: Миграция существующих данных

**User Story:** Как администратор БД, я хочу сохранить уже накопленную базу векторов, чтобы не потерять проиндексированные данные

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL preserve all existing face embeddings in Vector_Database
2. WHEN migration is performed, THE Face_Recognition_Engine SHALL validate data integrity of embeddings
3. THE Face_Recognition_Engine SHALL remove unused columns from face_embeddings table
4. THE Face_Recognition_Engine SHALL maintain backward compatibility during migration period
5. THE Face_Recognition_Engine SHALL provide rollback capability if migration fails

**Migration Steps:**

**Phase 1: Schema Analysis**
- Текущая схема: `face_embeddings(id, face_id, photo_id, event_id, session_id, embedding, confidence, created_at)`
- Целевая схема: `face_embeddings(id, photo_id, session_id, embedding, confidence, created_at)`
- Данные для сохранения: все записи с `session_id IS NOT NULL`

**Phase 2: Data Validation**
- Проверить количество записей: `SELECT COUNT(*) FROM face_embeddings WHERE session_id IS NOT NULL`
- Проверить уникальность: `SELECT COUNT(DISTINCT photo_id) FROM face_embeddings WHERE session_id IS NOT NULL`
- Проверить целостность векторов: все `embedding` должны быть 512-мерными

**Phase 3: Schema Migration**
```sql
-- Шаг 1: Создать резервную копию
CREATE TABLE face_embeddings_backup AS SELECT * FROM face_embeddings;

-- Шаг 2: Удалить неиспользуемые колонки
ALTER TABLE face_embeddings DROP COLUMN IF EXISTS face_id;
ALTER TABLE face_embeddings DROP COLUMN IF EXISTS event_id;

-- Шаг 3: Добавить NOT NULL constraints
ALTER TABLE face_embeddings ALTER COLUMN photo_id SET NOT NULL;
ALTER TABLE face_embeddings ALTER COLUMN session_id SET NOT NULL;

-- Шаг 4: Пересоздать индексы
CREATE INDEX IF NOT EXISTS idx_face_embeddings_photo_id ON face_embeddings(photo_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_session_id ON face_embeddings(session_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_session_photo ON face_embeddings(session_id, photo_id);
```

**Phase 4: Verification**
- Сравнить количество записей до и после миграции
- Проверить работу поиска на тестовых данных
- Измерить производительность запросов

### Requirement 6: Удаление Main Database зависимостей

**User Story:** Как архитектор, я хочу удалить зависимость от Main_Database, чтобы сервис использовал только Vector_Database

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL use only Vector_Database for all operations
2. THE Face_Recognition_Engine SHALL NOT create or query faces table in Main_Database
3. THE Face_Recognition_Engine SHALL NOT create or query events table in Main_Database
4. WHEN indexing is performed, THE Face_Recognition_Engine SHALL store data only in Vector_Database
5. THE Face_Recognition_Engine SHALL remove Main_Database connection configuration

**Tables to Remove:**
- `faces` таблица в Main_Database - дублирует данные из Vector_Database
- `events` таблица в Main_Database - legacy архитектура

**Code Changes:**
- Удалить `main_engine` из `core/database.py`
- Удалить `MainSessionLocal` и `get_main_db()`
- Удалить `models/face.py::Face` модель
- Удалить `models/event.py::Event` модель
- Обновить все endpoints для использования только `vector_db`

**Configuration Changes:**
- Удалить `MAIN_DB_HOST`, `MAIN_DB_PORT` из конфигурации
- Оставить только `VECTOR_DB_HOST`, `VECTOR_DB_PORT`
- Переименовать `VECTOR_POSTGRES_DB` в `POSTGRES_DB` для простоты

### Requirement 7: Упрощение конфигурации

**User Story:** Как DevOps инженер, я хочу иметь минимальную конфигурацию сервиса, чтобы упростить развертывание

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL require only essential configuration parameters
2. THE Face_Recognition_Engine SHALL NOT require Pixora-specific configuration
3. THE Face_Recognition_Engine SHALL use environment variables for all configuration
4. THE Face_Recognition_Engine SHALL provide sensible defaults for optional parameters
5. THE Face_Recognition_Engine SHALL validate configuration on startup

**Required Configuration (Minimal):**
```env
# Database
POSTGRES_USER=facepass
POSTGRES_PASSWORD=secret
POSTGRES_DB=facepass_vectors
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# S3 Storage (optional - only if indexing from S3)
S3_ENDPOINT=https://s3.beget.com
S3_ACCESS_KEY=key
S3_SECRET_KEY=secret
S3_BUCKET=photos

# Face Recognition
FACE_DETECTION_THRESHOLD=0.6
FACE_SIMILARITY_THRESHOLD=0.5
EMBEDDING_DIMENSION=512

# Redis (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Configuration to Remove:**
```env
# Pixora-specific (REMOVE)
MAIN_APP_DATABASE_URL
MAIN_API_URL
MAIN_URL
DOMAIN
STAGING_DOMAIN
MAIN_DB_HOST
MAIN_DB_PORT
```

### Requirement 8: API Authentication и Authorization

**User Story:** Как администратор безопасности, я хочу защитить API от несанкционированного доступа, чтобы только авторизованные клиенты могли индексировать и искать

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL require API key for all indexing operations
2. THE Face_Recognition_Engine SHALL validate API key on each request
3. WHEN invalid API key is provided, THE Face_Recognition_Engine SHALL return 401 Unauthorized
4. THE Face_Recognition_Engine SHALL support multiple API keys for different clients
5. THE Face_Recognition_Engine SHALL log all API requests with client identification

**Authentication Mechanism:**
- Header-based: `X-API-Key: <client_api_key>`
- Хранение ключей: environment variables или database
- Rate limiting: по API ключу

**Protected Endpoints:**
- `POST /api/v1/index` - требует API key
- `POST /api/v1/index/batch` - требует API key
- `DELETE /api/v1/index/{session_id}` - требует API key
- `POST /api/v1/search` - публичный (или опционально защищенный)

### Requirement 9: Observability и Monitoring

**User Story:** Как SRE инженер, я хочу мониторить работу сервиса, чтобы быстро обнаруживать проблемы

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL expose /health endpoint for health checks
2. THE Face_Recognition_Engine SHALL expose /metrics endpoint with Prometheus metrics
3. THE Face_Recognition_Engine SHALL log all errors with structured logging
4. THE Face_Recognition_Engine SHALL track indexing and search performance metrics
5. THE Face_Recognition_Engine SHALL provide database connection pool metrics

**Metrics to Track:**
- `facepass_search_requests_total` - количество поисковых запросов
- `facepass_search_duration_seconds` - время выполнения поиска
- `facepass_index_requests_total` - количество запросов на индексацию
- `facepass_index_duration_seconds` - время индексации
- `facepass_embeddings_total` - общее количество векторов в БД
- `facepass_db_connections_active` - активные подключения к БД

**Health Check:**
```json
{
  "status": "healthy",
  "database": "connected",
  "face_recognition_model": "loaded",
  "version": "2.0.0"
}
```


### Requirement 10: Документация нового API

**User Story:** Как внешний разработчик, я хочу иметь полную документацию API, чтобы легко интегрировать Facepass в свою систему

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL provide OpenAPI/Swagger documentation at /docs
2. THE Face_Recognition_Engine SHALL include request/response examples for all endpoints
3. THE Face_Recognition_Engine SHALL document all error codes and their meanings
4. THE Face_Recognition_Engine SHALL provide integration guide with code examples
5. THE Face_Recognition_Engine SHALL document rate limits and performance characteristics

**API Documentation Structure:**

**Indexing Endpoints:**
```
POST /api/v1/index
- Description: Index a single photo
- Request: multipart/form-data (photo_id, session_id, image file)
- Response: {indexed: true, photo_id: "...", confidence: 0.87}
- Errors: 400 (no face detected), 401 (unauthorized), 500 (processing error)

POST /api/v1/index/batch
- Description: Index multiple photos
- Request: JSON array of {photo_id, session_id, image_url}
- Response: {indexed: 15, failed: 2, errors: [...]}
```

**Search Endpoints:**
```
POST /api/v1/search
- Description: Search for similar faces
- Request: multipart/form-data (session_id, selfie image, threshold, limit)
- Response: {matches: [{photo_id, similarity}], query_time_ms: 123}
- Errors: 400 (no face in selfie), 404 (session not indexed)

GET /api/v1/search/status/{session_id}
- Description: Get indexing status for session
- Response: {indexed: true, photo_count: 150, last_indexed: "2024-01-15T10:30:00Z"}
```

### Requirement 11: Backward Compatibility Layer (Optional)

**User Story:** Как владелец продукта, я хочу иметь переходный период, чтобы Pixora могла мигрировать постепенно

#### Acceptance Criteria

1. WHERE backward compatibility is enabled, THE Face_Recognition_Engine SHALL support legacy endpoints
2. WHERE backward compatibility is enabled, THE Face_Recognition_Engine SHALL log deprecation warnings
3. THE Face_Recognition_Engine SHALL provide configuration flag to enable/disable legacy endpoints
4. THE Face_Recognition_Engine SHALL document migration path from legacy to new API
5. THE Face_Recognition_Engine SHALL set deprecation timeline for legacy endpoints

**Legacy Endpoints (Deprecated):**
- `POST /api/v1/faces/search-session` → `POST /api/v1/search`
- `POST /api/v1/faces/index-session/{session_id}` → `POST /api/v1/index/batch`

**Migration Guide:**
```markdown
# Migration from Legacy API to v2

## Breaking Changes
1. Removed automatic sync from Pixora API
2. Removed Pixora database dependency
3. Changed response format (no Pixora metadata)

## Migration Steps
1. Update client code to call /api/v1/index when uploading photos
2. Remove dependency on /remote-services endpoint
3. Update search calls to use new /api/v1/search endpoint
4. Handle photo metadata in client application (not in Facepass)
```

### Requirement 12: Performance Optimization

**User Story:** Как пользователь, я хочу получать результаты поиска быстро, чтобы не ждать долго

#### Acceptance Criteria

1. WHEN search is performed, THE Face_Recognition_Engine SHALL return results within 500ms for sessions with up to 1000 photos
2. THE Face_Recognition_Engine SHALL use connection pooling for database connections
3. THE Face_Recognition_Engine SHALL cache frequently accessed data
4. THE Face_Recognition_Engine SHALL use batch processing for multiple face embeddings
5. THE Face_Recognition_Engine SHALL optimize vector similarity queries with proper indexes

**Performance Targets:**
- Search latency: p50 < 200ms, p95 < 500ms, p99 < 1000ms
- Indexing throughput: > 10 photos/second
- Database connections: pool size 10-20
- Memory usage: < 2GB per worker

**Optimization Techniques:**
- pgvector IVFFlat index for large datasets (> 10k vectors)
- Normalized embeddings for consistent similarity calculation
- Batch embedding extraction (process multiple faces at once)
- Redis caching for session metadata

### Requirement 13: Testing Strategy

**User Story:** Как QA инженер, я хочу иметь comprehensive test suite, чтобы гарантировать качество сервиса

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL have unit tests for all core functions
2. THE Face_Recognition_Engine SHALL have integration tests for API endpoints
3. THE Face_Recognition_Engine SHALL have property-based tests for vector operations
4. THE Face_Recognition_Engine SHALL have performance tests for search operations
5. THE Face_Recognition_Engine SHALL achieve > 80% code coverage

**Test Categories:**

**Unit Tests:**
- Face embedding extraction
- Vector normalization
- Similarity calculation
- Configuration validation

**Integration Tests:**
- Index endpoint with real images
- Search endpoint with test dataset
- Database operations
- Error handling

**Property-Based Tests:**
- Embedding normalization (norm should be 1.0)
- Similarity symmetry (sim(A,B) == sim(B,A))
- Similarity bounds (0.0 <= similarity <= 1.0)
- Round-trip: index then search should find the same photo

**Performance Tests:**
- Search latency under load
- Concurrent indexing
- Database connection pool behavior
- Memory usage during batch processing

### Requirement 14: Deployment Strategy

**User Story:** Как DevOps инженер, я хочу иметь четкий план развертывания, чтобы минимизировать downtime

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL support zero-downtime deployment
2. THE Face_Recognition_Engine SHALL provide database migration scripts
3. THE Face_Recognition_Engine SHALL support rollback to previous version
4. THE Face_Recognition_Engine SHALL use health checks for readiness probes
5. THE Face_Recognition_Engine SHALL document deployment prerequisites

**Deployment Phases:**

**Phase 1: Preparation (Week 1)**
- Code review and testing
- Database migration scripts preparation
- Backup current production data
- Setup staging environment

**Phase 2: Staging Deployment (Week 2)**
- Deploy to staging
- Run migration scripts
- Perform integration testing
- Load testing with production-like data

**Phase 3: Production Deployment (Week 3)**
- Blue-green deployment strategy
- Deploy new version alongside old
- Gradually shift traffic (10% → 50% → 100%)
- Monitor metrics and errors
- Rollback plan ready

**Phase 4: Cleanup (Week 4)**
- Remove legacy endpoints
- Remove Pixora database connections
- Update documentation
- Decommission old version

### Requirement 15: Security Hardening

**User Story:** Как security engineer, я хочу защитить сервис от атак, чтобы обеспечить безопасность данных

#### Acceptance Criteria

1. THE Face_Recognition_Engine SHALL validate all input data
2. THE Face_Recognition_Engine SHALL prevent SQL injection attacks
3. THE Face_Recognition_Engine SHALL rate limit API requests
4. THE Face_Recognition_Engine SHALL sanitize file uploads
5. THE Face_Recognition_Engine SHALL use HTTPS for all communications

**Security Measures:**

**Input Validation:**
- File type validation (only images)
- File size limits (max 10MB)
- Image dimension limits (max 4096x4096)
- SQL parameter binding (no string concatenation)

**Rate Limiting:**
- 100 requests/minute per API key for indexing
- 1000 requests/minute per IP for search
- Exponential backoff for repeated failures

**File Upload Security:**
- Virus scanning (optional)
- Image format validation
- Metadata stripping
- Temporary file cleanup

**Network Security:**
- HTTPS only (no HTTP)
- CORS configuration
- Security headers (CSP, X-Frame-Options, etc.)
- API key rotation policy


## Correctness Properties

Данный раздел содержит свойства корректности, которые должны выполняться для валидации изоляции сервиса.

### Property 1: Database Isolation

**Property:** Сервис не должен иметь активных подключений к внешним базам данных

**Test:**
```python
def test_no_external_database_connections():
    """
    Проверяет, что сервис не создает подключения к Pixora БД
    """
    from core.database import Base
    
    # Должен быть только один engine (vector_engine)
    engines = [attr for attr in dir(database) if 'engine' in attr.lower()]
    assert len(engines) == 1, "Should have only vector_engine"
    assert 'pixora_engine' not in engines
    assert 'main_engine' not in engines
```

### Property 2: API Independence

**Property:** API endpoints не должны делать запросы к внешним сервисам

**Test:**
```python
@pytest.mark.property
def test_no_external_api_calls(monkeypatch):
    """
    Проверяет, что поиск не делает HTTP запросы к Pixora API
    """
    import httpx
    
    # Mock httpx to fail if any external call is made
    def mock_get(*args, **kwargs):
        raise AssertionError("External API call detected")
    
    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    
    # Search should work without external calls
    response = client.post("/api/v1/search", ...)
    assert response.status_code == 200
```

### Property 3: Configuration Minimalism

**Property:** Конфигурация не должна содержать Pixora-specific параметры

**Test:**
```python
def test_no_pixora_configuration():
    """
    Проверяет, что конфигурация не содержит Pixora параметров
    """
    from core.config import Settings
    
    settings = Settings()
    
    # These should not exist
    assert not hasattr(settings, 'MAIN_APP_DATABASE_URL')
    assert not hasattr(settings, 'MAIN_API_URL')
    assert not hasattr(settings, 'STAGING_DOMAIN')
    
    # These should exist
    assert hasattr(settings, 'POSTGRES_HOST')
    assert hasattr(settings, 'EMBEDDING_DIMENSION')
```

### Property 4: Vector Storage Completeness

**Property:** Все необходимые данные для поиска должны храниться в Vector_Database

**Test:**
```python
@pytest.mark.property
def test_search_without_external_data():
    """
    Проверяет, что поиск работает только с данными из Vector_Database
    """
    # Index a photo
    response = client.post("/api/v1/index", 
        data={"photo_id": "test-123", "session_id": "session-456"},
        files={"image": test_image}
    )
    assert response.status_code == 200
    
    # Search should find it without external DB
    response = client.post("/api/v1/search",
        data={"session_id": "session-456"},
        files={"image": test_selfie}
    )
    
    matches = response.json()["matches"]
    assert any(m["photo_id"] == "test-123" for m in matches)
```

### Property 5: Embedding Normalization

**Property:** Все векторы должны быть нормализованы (норма = 1.0)

**Test:**
```python
@given(st.binary(min_size=1000, max_size=100000))
def test_embedding_normalization(image_data):
    """
    Property: все сохраненные эмбеддинги должны быть нормализованы
    """
    from services.face_recognition import get_face_recognition_service
    import numpy as np
    
    service = get_face_recognition_service()
    
    try:
        embedding, confidence = service.extract_single_embedding(image_data)
        
        if embedding is not None:
            # Check normalization
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01, f"Embedding not normalized: {norm}"
    except:
        # Invalid image is acceptable
        pass
```

### Property 6: Similarity Symmetry

**Property:** Similarity(A, B) должна равняться Similarity(B, A)

**Test:**
```python
@given(st.binary(min_size=1000), st.binary(min_size=1000))
def test_similarity_symmetry(image_a, image_b):
    """
    Property: similarity должна быть симметричной
    """
    service = get_face_recognition_service()
    
    try:
        emb_a, _ = service.extract_single_embedding(image_a)
        emb_b, _ = service.extract_single_embedding(image_b)
        
        if emb_a is not None and emb_b is not None:
            sim_ab = service.calculate_similarity(emb_a, emb_b)
            sim_ba = service.calculate_similarity(emb_b, emb_a)
            
            assert abs(sim_ab - sim_ba) < 0.001
    except:
        pass
```

### Property 7: Round-Trip Indexing

**Property:** Фотография, проиндексированная и затем найденная, должна иметь высокую similarity

**Test:**
```python
def test_round_trip_indexing():
    """
    Property: индексация → поиск должны найти ту же фотографию с высокой similarity
    """
    # Index a photo
    photo_id = "round-trip-test"
    session_id = "test-session"
    
    response = client.post("/api/v1/index",
        data={"photo_id": photo_id, "session_id": session_id},
        files={"image": test_image}
    )
    assert response.status_code == 200
    
    # Search with the same image
    response = client.post("/api/v1/search",
        data={"session_id": session_id, "threshold": 0.5},
        files={"image": test_image}
    )
    
    matches = response.json()["matches"]
    
    # Should find itself with high similarity
    self_match = next((m for m in matches if m["photo_id"] == photo_id), None)
    assert self_match is not None
    assert self_match["similarity"] > 0.95
```

### Property 8: Idempotent Indexing

**Property:** Повторная индексация той же фотографии не должна создавать дубликаты

**Test:**
```python
def test_idempotent_indexing():
    """
    Property: индексация одной фотографии дважды не создает дубликаты
    """
    photo_id = "idempotent-test"
    session_id = "test-session"
    
    # Index once
    client.post("/api/v1/index",
        data={"photo_id": photo_id, "session_id": session_id},
        files={"image": test_image}
    )
    
    # Index again
    client.post("/api/v1/index",
        data={"photo_id": photo_id, "session_id": session_id},
        files={"image": test_image}
    )
    
    # Check database
    from core.database import VectorSessionLocal
    from models.face import FaceEmbedding
    
    db = VectorSessionLocal()
    count = db.query(FaceEmbedding).filter(
        FaceEmbedding.photo_id == photo_id,
        FaceEmbedding.session_id == session_id
    ).count()
    
    # Should have only one embedding (or update existing)
    assert count == 1
```

### Property 9: Search Performance Bounds

**Property:** Поиск должен завершаться в разумное время

**Test:**
```python
@pytest.mark.performance
def test_search_performance():
    """
    Property: поиск в сессии с 1000 фото должен занимать < 500ms
    """
    import time
    
    session_id = "perf-test-session"
    
    # Index 1000 photos (setup)
    for i in range(1000):
        client.post("/api/v1/index",
            data={"photo_id": f"photo-{i}", "session_id": session_id},
            files={"image": generate_test_image()}
        )
    
    # Measure search time
    start = time.time()
    response = client.post("/api/v1/search",
        data={"session_id": session_id},
        files={"image": test_selfie}
    )
    duration_ms = (time.time() - start) * 1000
    
    assert response.status_code == 200
    assert duration_ms < 500, f"Search took {duration_ms}ms, expected < 500ms"
```

### Property 10: No Data Leakage

**Property:** Поиск в одной сессии не должен возвращать результаты из другой сессии

**Test:**
```python
def test_no_session_data_leakage():
    """
    Property: поиск в session A не должен возвращать фото из session B
    """
    session_a = "session-a"
    session_b = "session-b"
    
    # Index photo in session A
    client.post("/api/v1/index",
        data={"photo_id": "photo-a", "session_id": session_a},
        files={"image": test_image_a}
    )
    
    # Index photo in session B
    client.post("/api/v1/index",
        data={"photo_id": "photo-b", "session_id": session_b},
        files={"image": test_image_b}
    )
    
    # Search in session A
    response = client.post("/api/v1/search",
        data={"session_id": session_a, "threshold": 0.0},  # Very low threshold
        files={"image": test_selfie}
    )
    
    matches = response.json()["matches"]
    
    # Should not contain photo-b
    assert not any(m["photo_id"] == "photo-b" for m in matches)
```

## Summary

Данный документ определяет 15 основных требований для изоляции Facepass микросервиса:

1. **Анализ зависимостей** - полная инвентаризация интеграций с Pixora
2. **Изоляция векторов** - автономное хранение в Vector_Database
3. **Чистый API** - простой интерфейс для внешних клиентов
4. **Удаление синхронизации** - отказ от автоматической синхронизации с Pixora
5. **Миграция данных** - сохранение существующих векторов
6. **Удаление Main DB** - использование только Vector_Database
7. **Упрощение конфигурации** - минимальный набор параметров
8. **Аутентификация** - защита API ключами
9. **Observability** - метрики и health checks
10. **Документация** - полное описание нового API
11. **Backward compatibility** - опциональная поддержка legacy endpoints
12. **Оптимизация** - производительность поиска и индексации
13. **Тестирование** - comprehensive test suite
14. **Развертывание** - zero-downtime deployment strategy
15. **Безопасность** - защита от атак и валидация входных данных

Correctness properties обеспечивают валидацию изоляции через property-based тесты.

Следующий шаг: создание design документа с детальной архитектурой нового API.
