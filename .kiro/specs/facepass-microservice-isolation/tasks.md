# Implementation Plan: Facepass Microservice Isolation

## Overview

Данный план описывает пошаговую изоляцию Facepass микросервиса от зависимостей Pixora. Цель - создать автономный сервис распознавания лиц, который работает только с photo_id и векторами, предоставляя чистый API для индексации и поиска.

**Ключевые изменения:**
- Удаление подключений к Pixora БД и Main БД
- Удаление автоматической синхронизации с Pixora API
- Упрощение схемы БД (только face_embeddings)
- Новый чистый API для индексации и поиска
- API key authentication
- Observability (метрики, логирование)

**Технологический стек:** Python, FastAPI, PostgreSQL + pgvector, Redis, Prometheus

## Tasks

- [x] 1. Подготовка и анализ кодовой базы
  - Создать резервную копию текущей БД (face_embeddings таблица)
  - Документировать все файлы, которые будут изменены
  - Создать feature branch для изоляции
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Удаление зависимостей от Pixora Database
  - [x] 2.1 Удалить pixora_engine из core/database.py
    - Удалить MAIN_APP_DATABASE_URL из конфигурации
    - Удалить pixora_engine и PixoraSessionLocal
    - Удалить get_pixora_db() dependency
    - _Requirements: 1.1, 6.1, 6.5_
  
  - [x] 2.2 Удалить модель PhotoSession
    - Удалить файл models/photo_session.py
    - Удалить все импорты PhotoSession из других файлов
    - _Requirements: 1.5, 2.2_
  
  - [x] 2.3 Удалить CORS прокси эндпоинт
    - Удалить /api/v1/remote-services/{session_id} из app/main.py
    - Удалить связанные функции и зависимости
    - _Requirements: 1.2, 3.5_

- [x] 3. Удаление зависимостей от Main Database
  - [x] 3.1 Удалить main_engine из core/database.py
    - Удалить main_engine и MainSessionLocal
    - Удалить get_main_db() dependency
    - Оставить только vector_engine (переименовать в engine)
    - _Requirements: 6.1, 6.2, 6.3, 6.5_
  
  - [x] 3.2 Удалить модель Face
    - Удалить файл models/face.py (если существует)
    - Удалить все импорты Face из других файлов
    - _Requirements: 6.2_
  
  - [x] 3.3 Удалить модель Event
    - Удалить файл models/event.py (если существует)
    - Удалить все импорты Event из других файлов
    - _Requirements: 6.3_

- [x] 4. Удаление автоматической синхронизации с Pixora
  - [x] 4.1 Удалить sync_session_photos() функцию
    - Удалить функцию из app/api/v1/endpoints/faces.py
    - Удалить все вызовы background_tasks.add_task(sync_session_photos)
    - Удалить HTTP запросы к Pixora API
    - _Requirements: 1.3, 4.1, 4.2, 4.3_
  
  - [x] 4.2 Обновить search endpoint
    - Удалить автоматическую индексацию при первом поиске
    - Удалить проверку is_indexed с последующей синхронизацией
    - Поиск должен работать только с уже проиндексированными данными
    - _Requirements: 4.3, 4.5_

- [x] 5. Миграция схемы базы данных
  - [x] 5.1 Создать SQL скрипт миграции
    - Создать файл scripts/migration_v2.sql
    - Добавить создание backup таблицы
    - Добавить удаление колонок face_id и event_id
    - Добавить NOT NULL constraints для photo_id и session_id
    - Добавить unique constraint (photo_id, session_id)
    - Добавить пересоздание индексов
    - Добавить создание vector index (IVFFlat)
    - _Requirements: 2.1, 2.2, 2.3, 5.1, 5.2, 5.3_
  
  - [ ]* 5.2 Написать тесты для валидации миграции
    - Тест проверки целостности данных до и после миграции
    - Тест проверки уникальности (photo_id, session_id)
    - Тест проверки нормализации векторов
    - _Requirements: 5.2_
  
  - [x] 5.3 Создать rollback скрипт
    - Создать файл scripts/rollback_v2.sql
    - Восстановление из backup таблицы
    - _Requirements: 5.5_

- [x] 6. Checkpoint - Проверка удаления зависимостей
  - Убедиться, что все тесты проходят
  - Проверить, что нет импортов pixora_engine или main_engine
  - Проверить, что нет HTTP запросов к Pixora API
  - Спросить пользователя, если возникли вопросы

- [x] 7. Упрощение конфигурации
  - [x] 7.1 Обновить core/config.py
    - Удалить MAIN_APP_DATABASE_URL
    - Удалить MAIN_API_URL, MAIN_URL
    - Удалить DOMAIN, STAGING_DOMAIN
    - Удалить MAIN_DB_HOST, MAIN_DB_PORT
    - Переименовать VECTOR_POSTGRES_* в POSTGRES_*
    - Добавить API_KEYS параметр
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 7.2 Обновить .env.example
    - Удалить Pixora-specific параметры
    - Добавить минимальную конфигурацию
    - Добавить комментарии для каждого параметра
    - _Requirements: 7.1, 7.2_
  
  - [ ]* 7.3 Написать property тест для конфигурации
    - **Property 3: Configuration Minimalism**
    - **Validates: Requirements 7.2**
    - Проверить, что нет Pixora параметров в Settings
    - _Requirements: 7.2_

- [x] 8. Реализация нового API - Indexing Endpoints
  - [x] 8.1 Создать POST /api/v1/index endpoint
    - Принимать photo_id, session_id, image (multipart/form-data)
    - Опционально принимать s3_key вместо image
    - Извлекать embedding через FaceRecognitionService
    - Сохранять в face_embeddings таблицу
    - Возвращать {indexed, photo_id, confidence, faces_detected}
    - _Requirements: 3.1, 3.2_
  
  - [x] 8.2 Создать POST /api/v1/index/batch endpoint
    - Принимать session_id и массив {photo_id, s3_key}
    - Обрабатывать пакетно (batch processing)
    - Возвращать {indexed, failed, errors}
    - _Requirements: 3.1, 3.2_
  
  - [x] 8.3 Создать DELETE /api/v1/index/{session_id} endpoint
    - Удалять все embeddings для session_id
    - Возвращать {deleted, embeddings_removed}
    - _Requirements: 3.1_
  
  - [ ]* 8.4 Написать unit тесты для indexing endpoints
    - Тест успешной индексации
    - Тест индексации без лица (400 error)
    - Тест batch индексации
    - Тест удаления сессии
    - _Requirements: 3.2, 13.2_

- [x] 9. Реализация нового API - Search Endpoints
  - [x] 9.1 Создать POST /api/v1/search endpoint
    - Принимать session_id, image (selfie), threshold, limit
    - Извлекать query embedding из селфи
    - Выполнять vector similarity search в БД
    - Возвращать {matches: [{photo_id, similarity, confidence}], query_time_ms, total_matches}
    - _Requirements: 3.3, 3.4, 3.6_
  
  - [x] 9.2 Создать GET /api/v1/search/status/{session_id} endpoint
    - Проверять наличие индексов для session_id
    - Возвращать {indexed, photo_count, last_indexed, session_id}
    - _Requirements: 3.1_
  
  - [ ]* 9.3 Написать unit тесты для search endpoints
    - Тест успешного поиска
    - Тест поиска в пустой сессии (404 error)
    - Тест поиска без лица в селфи (400 error)
    - Тест статуса сессии
    - _Requirements: 3.4, 13.2_
  
  - [ ]* 9.4 Написать property тест для изоляции поиска
    - **Property 2: Search Without External Dependencies**
    - **Validates: Requirements 2.3, 4.1, 4.3**
    - Проверить, что поиск не делает внешних API вызовов
    - _Requirements: 2.3, 4.3_

- [x] 10. Checkpoint - Проверка нового API
  - Протестировать все новые endpoints вручную
  - Убедиться, что indexing и search работают корректно
  - Проверить обработку ошибок
  - Спросить пользователя, если возникли вопросы

- [x] 11. Реализация API Key Authentication
  - [x] 11.1 Создать APIKeyAuth middleware
    - Создать файл app/middleware/auth.py
    - Реализовать проверку X-API-Key header
    - Поддержка нескольких API keys из конфигурации
    - Логирование попыток с невалидными ключами
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [x] 11.2 Защитить indexing endpoints
    - Применить APIKeyAuth к POST /api/v1/index
    - Применить APIKeyAuth к POST /api/v1/index/batch
    - Применить APIKeyAuth к DELETE /api/v1/index/{session_id}
    - Оставить search endpoints публичными
    - _Requirements: 8.1, 8.2_
  
  - [ ]* 11.3 Написать тесты для authentication
    - Тест успешной аутентификации
    - Тест отклонения без API key (401)
    - Тест отклонения с невалидным API key (401)
    - Тест публичного доступа к search
    - _Requirements: 8.2, 8.3_
  
  - [ ]* 11.4 Написать property тест для API key validation
    - **Property 10: Invalid API Key Rejection**
    - **Validates: Requirements 8.2, 8.3**
    - Проверить отклонение всех невалидных ключей
    - _Requirements: 8.2, 8.3_

- [x] 12. Реализация Observability
  - [x] 12.1 Добавить structured logging
    - Настроить structlog в app/main.py
    - Логировать все API requests с контекстом
    - Логировать ошибки с exc_info
    - _Requirements: 8.5, 9.3_
  
  - [x] 12.2 Создать GET /health endpoint
    - Проверять подключение к БД
    - Проверять загрузку face recognition модели
    - Возвращать {status, database, face_recognition_model, version, uptime_seconds}
    - _Requirements: 9.1_
  
  - [x] 12.3 Создать GET /metrics endpoint
    - Интегрировать prometheus_client
    - Добавить метрики: search_requests_total, search_duration_seconds
    - Добавить метрики: index_requests_total, index_duration_seconds
    - Добавить метрики: embeddings_total, db_connections_active
    - _Requirements: 9.2, 9.4, 9.5_
  
  - [ ]* 12.4 Написать тесты для observability
    - Тест health endpoint
    - Тест metrics endpoint
    - Тест логирования запросов
    - _Requirements: 9.1, 9.2_

- [x] 13. Реализация Input Validation и Security
  - [x] 13.1 Создать валидацию file uploads
    - Проверка content type (только images)
    - Проверка размера файла (max 10MB)
    - Проверка формата изображения (PIL.Image.verify)
    - Проверка dimensions (max 4096x4096)
    - _Requirements: 15.1, 15.4_
  
  - [x] 13.2 Добавить Pydantic валидацию параметров
    - Валидация session_id (min_length=1, max_length=255)
    - Валидация threshold (ge=0.0, le=1.0)
    - Валидация limit (ge=1, le=1000)
    - Валидация photo_id (предотвращение SQL injection)
    - _Requirements: 15.1, 15.2_
  
  - [x] 13.3 Добавить rate limiting
    - Интегрировать fastapi-limiter с Redis
    - Лимит для indexing: 100 requests/minute per API key
    - Лимит для search: 1000 requests/minute per IP
    - _Requirements: 15.3_
  
  - [ ]* 13.4 Написать property тест для SQL injection prevention
    - **Property 15: SQL Injection Prevention**
    - **Validates: Requirements 15.2**
    - Проверить безопасную обработку malicious input
    - _Requirements: 15.2_
  
  - [ ]* 13.5 Написать тесты для input validation
    - Тест отклонения non-image файлов
    - Тест отклонения слишком больших файлов
    - Тест отклонения invalid параметров
    - Тест rate limiting
    - _Requirements: 15.1, 15.3, 15.4_

- [x] 14. Checkpoint - Проверка безопасности и observability
  - Проверить работу authentication
  - Проверить метрики в /metrics
  - Проверить health check
  - Проверить rate limiting
  - Спросить пользователя, если возникли вопросы

- [x] 15. Обновление Services
  - [x] 15.1 Обновить FaceRecognitionService
    - Убедиться, что extract_single_embedding нормализует векторы
    - Добавить extract_multiple_embeddings для групповых фото
    - Добавить calculate_similarity метод
    - _Requirements: 2.1, 2.4_
  
  - [x] 15.2 Создать IndexingService
    - Создать файл services/indexing.py
    - Реализовать index_photo(photo_id, session_id, image_data, db)
    - Реализовать index_batch(session_id, photos, db)
    - Реализовать delete_session(session_id, db)
    - _Requirements: 3.2, 6.4_
  
  - [x] 15.3 Создать SearchService
    - Создать файл services/search.py
    - Реализовать search_session(session_id, query_embedding, threshold, limit, db)
    - Реализовать get_session_status(session_id, db)
    - Использовать pgvector cosine distance operator (<=>)
    - _Requirements: 3.4, 4.3_
  
  - [ ]* 15.4 Написать unit тесты для services
    - Тест FaceRecognitionService.extract_single_embedding
    - Тест IndexingService.index_photo
    - Тест SearchService.search_session
    - _Requirements: 13.1_

- [ ] 16. Property-Based Tests - Core Properties
  - [ ]* 16.1 Написать property тест для database isolation
    - **Property 1: Database Isolation**
    - **Validates: Requirements 2.2, 2.3, 4.5, 6.1**
    - Проверить отсутствие подключений к внешним БД
    - _Requirements: 2.2, 2.3, 6.1_
  
  - [ ]* 16.2 Написать property тест для photo ID format support
    - **Property 3: Photo ID Format Support**
    - **Validates: Requirements 2.5**
    - Проверить поддержку UUID и timestamp-hash форматов
    - _Requirements: 2.5_
  
  - [ ]* 16.3 Написать property тест для API response format
    - **Property 4: API Response Format**
    - **Validates: Requirements 3.2, 3.6**
    - Проверить отсутствие Pixora-specific полей в ответах
    - _Requirements: 3.2, 3.6_
  
  - [ ]* 16.4 Написать property тест для search response format
    - **Property 5: Search Response Format**
    - **Validates: Requirements 3.4, 3.6**
    - Проверить корректный формат результатов поиска
    - _Requirements: 3.4, 3.6_

- [ ] 17. Property-Based Tests - Vector Operations
  - [ ]* 17.1 Написать property тест для embedding validation
    - **Property 7: Embedding Validation**
    - **Validates: Requirements 5.2**
    - Проверить валидность всех векторов после миграции
    - _Requirements: 5.2_
  
  - [ ]* 17.2 Написать property тест для embedding normalization
    - **Property 18: Embedding Normalization**
    - **Validates: Requirements 5.2**
    - Проверить нормализацию всех векторов (L2 norm = 1.0)
    - _Requirements: 5.2_
  
  - [ ]* 17.3 Написать property тест для similarity symmetry
    - **Property 19: Similarity Symmetry**
    - **Validates: Requirements 12.1**
    - Проверить симметричность cosine similarity
    - _Requirements: 12.1_
  
  - [ ]* 17.4 Написать property тест для round-trip indexing
    - **Property 20: Round-Trip Indexing**
    - **Validates: Requirements 3.2, 3.4**
    - Проверить, что индексация → поиск находит ту же фотографию
    - _Requirements: 3.2, 3.4_

- [ ] 18. Property-Based Tests - Data Isolation
  - [ ]* 18.1 Написать property тест для session isolation
    - **Property 21: Session Isolation**
    - **Validates: Requirements 2.1, 4.3**
    - Проверить, что поиск не возвращает фото из других сессий
    - _Requirements: 2.1, 4.3_
  
  - [ ]* 18.2 Написать property тест для idempotent indexing
    - **Property 22: Idempotent Indexing**
    - **Validates: Requirements 3.2**
    - Проверить, что повторная индексация не создает дубликаты
    - _Requirements: 3.2_
  
  - [ ]* 18.3 Написать property тест для single database operations
    - **Property 8: Single Database Operations**
    - **Validates: Requirements 6.2, 6.3, 6.4**
    - Проверить, что данные пишутся только в Vector Database
    - _Requirements: 6.2, 6.3, 6.4_
  
  - [ ]* 18.4 Написать property тест для no background sync
    - **Property 6: No Background Sync Tasks**
    - **Validates: Requirements 4.1, 4.2**
    - Проверить отсутствие фоновых задач синхронизации
    - _Requirements: 4.1, 4.2_

- [ ] 19. Property-Based Tests - Security & Performance
  - [ ]* 19.1 Написать property тест для API key authentication
    - **Property 9: API Key Authentication**
    - **Validates: Requirements 8.1, 8.2, 8.3**
    - Проверить требование API key для protected endpoints
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ]* 19.2 Написать property тест для request logging
    - **Property 11: Request Logging**
    - **Validates: Requirements 8.5, 9.3**
    - Проверить логирование всех запросов
    - _Requirements: 8.5, 9.3_
  
  - [ ]* 19.3 Написать property тест для performance metrics
    - **Property 12: Performance Metrics Tracking**
    - **Validates: Requirements 9.4**
    - Проверить обновление метрик для всех операций
    - _Requirements: 9.4_
  
  - [ ]* 19.4 Написать property тест для search performance bound
    - **Property 13: Search Performance Bound**
    - **Validates: Requirements 12.1**
    - Проверить, что поиск завершается за < 500ms (p95)
    - _Requirements: 12.1_
  
  - [ ]* 19.5 Написать property тест для input validation
    - **Property 14: Input Validation**
    - **Validates: Requirements 15.1**
    - Проверить отклонение invalid input с 400 error
    - _Requirements: 15.1_
  
  - [ ]* 19.6 Написать property тест для rate limiting
    - **Property 16: Rate Limiting**
    - **Validates: Requirements 15.3**
    - Проверить отклонение запросов при превышении лимита
    - _Requirements: 15.3_
  
  - [ ]* 19.7 Написать property тест для file upload validation
    - **Property 17: File Upload Validation**
    - **Validates: Requirements 15.4**
    - Проверить отклонение invalid файлов
    - _Requirements: 15.4_

- [ ] 20. Checkpoint - Проверка всех property tests
  - Запустить все property tests с pytest -m property
  - Убедиться, что все 22 properties проходят
  - Проверить coverage > 80%
  - Спросить пользователя, если возникли вопросы

- [x] 21. Обновление Docker конфигурации
  - [x] 21.1 Обновить docker-compose.yml
    - Удалить сервис db_main (Main Database)
    - Удалить сервис db_pixora (Pixora Database)
    - Оставить только db_vector, redis, facepass
    - Добавить сервис prometheus для метрик
    - Обновить environment variables
    - _Requirements: 6.1, 7.1, 14.5_
  
  - [x] 21.2 Создать prometheus.yml конфигурацию
    - Настроить scraping /metrics endpoint
    - _Requirements: 9.2_
  
  - [x] 21.3 Обновить Dockerfile
    - Убедиться, что все зависимости установлены
    - Добавить healthcheck
    - _Requirements: 14.4_

- [x] 22. Документация
  - [x] 22.1 Обновить README.md
    - Описать новую архитектуру (автономный микросервис)
    - Удалить упоминания Pixora integration
    - Добавить примеры использования нового API
    - Добавить инструкции по развертыванию
    - _Requirements: 10.1, 10.4, 10.5_
  
  - [x] 22.2 Создать API документацию
    - Настроить FastAPI автоматическую документацию (/docs)
    - Добавить примеры request/response для всех endpoints
    - Документировать error codes
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 22.3 Создать Migration Guide для Pixora
    - Создать файл docs/MIGRATION_GUIDE.md
    - Описать breaking changes
    - Предоставить примеры кода для интеграции
    - Описать ответственности клиента (индексация, метаданные)
    - _Requirements: 10.4, 11.4_

- [ ] 23. Integration Tests
  - [ ]* 23.1 Написать end-to-end тест полного workflow
    - Индексация нескольких фотографий
    - Проверка статуса сессии
    - Поиск по селфи
    - Удаление сессии
    - _Requirements: 13.2_
  
  - [ ]* 23.2 Написать тест для batch indexing
    - Индексация 100+ фотографий пакетом
    - Проверка обработки ошибок
    - _Requirements: 13.2_
  
  - [ ]* 23.3 Написать performance тест
    - Индексация 1000 фотографий
    - Поиск в сессии с 1000 фотографиями
    - Измерение latency (p50, p95, p99)
    - _Requirements: 12.1, 13.4_

- [-] 24. Подготовка к deployment
  - [x] 24.1 Создать deployment checklist
    - Создать файл docs/DEPLOYMENT_CHECKLIST.md
    - Описать prerequisites
    - Описать шаги deployment
    - Описать rollback процедуру
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ] 24.2 Подготовить staging environment
    - Развернуть новую версию на staging
    - Запустить миграцию БД на staging
    - Выполнить smoke tests
    - _Requirements: 14.1_
  
  - [ ] 24.3 Создать monitoring dashboard
    - Настроить Grafana dashboard для метрик
    - Добавить алерты для критических метрик
    - _Requirements: 9.2, 9.4_

- [x] 25. Final Checkpoint - Готовность к production
  - Все unit tests проходят
  - Все property tests проходят
  - Все integration tests проходят
  - Performance tests показывают приемлемые результаты
  - Документация обновлена
  - Staging deployment успешен
  - Спросить пользователя о готовности к production deployment

## Notes

- Задачи, помеченные `*`, являются опциональными (тесты) и могут быть пропущены для быстрого MVP
- Каждая задача ссылается на конкретные requirements для трассируемости
- Checkpoints обеспечивают инкрементальную валидацию
- Property tests валидируют универсальные свойства корректности (22 properties)
- Unit tests валидируют конкретные примеры и edge cases
- Integration tests валидируют end-to-end workflows
- Все задачи выполняются последовательно, каждая строится на предыдущих

## Migration Strategy

**Phase 1: Code Changes (Tasks 1-20)**
- Удаление зависимостей
- Реализация нового API
- Тестирование

**Phase 2: Database Migration (Task 5)**
- Выполняется на staging, затем на production
- Backup → Migration → Validation

**Phase 3: Deployment (Tasks 21-24)**
- Blue-green deployment
- Gradual traffic shift
- Monitoring

**Phase 4: Cleanup**
- Удаление legacy кода
- Обновление документации
- Decommission старой версии
