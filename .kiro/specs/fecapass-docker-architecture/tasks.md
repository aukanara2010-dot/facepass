# Implementation Plan: Fecapass Docker Architecture

## Overview

Этот план реализации описывает пошаговый процесс создания Docker-архитектуры для сервиса распознавания лиц Fecapass. Реализация будет выполнена инкрементально, начиная с базовой инфраструктуры и заканчивая полной интеграцией всех компонентов.

## Tasks

- [x] 1. Создать базовую структуру проекта и конфигурационные файлы
  - Создать директории: /app, /core, /services, /workers, /models, /scripts, /tests
  - Создать requirements.txt со всеми необходимыми зависимостями
  - Создать .env.example с документированными переменными окружения
  - Создать .gitignore для Python/Docker проектов
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1-3.11, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 1.1 Написать property тест для структуры проекта
  - **Property 5: Project Directory Structure Completeness**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

- [x] 1.2 Написать property тест для requirements.txt
  - **Property 6: Python Dependencies Completeness**
  - **Validates: Requirements 3.1-3.11**

- [-] 1.3 Написать property тест для .env.example
  - **Property 11: Environment Template Documentation**
  - **Validates: Requirements 8.6**

- [x] 2. Создать модуль конфигурации (core/config.py)
  - Реализовать класс Settings с использованием pydantic-settings
  - Добавить все необходимые поля конфигурации (БД, S3, Redis, Celery)
  - Реализовать computed properties для database_url, redis_url
  - Добавить валидацию обязательных параметров
  - Реализовать функцию get_settings() с кэшированием через lru_cache
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11_

- [x] 2.1 Написать unit тесты для Settings класса
  - Тест загрузки переменных окружения
  - Тест значений по умолчанию
  - Тест построения database URLs
  - _Requirements: 4.1-4.11_

- [x] 2.2 Написать property тест для атрибутов конфигурации
  - **Property 7: Configuration Attribute Completeness**
  - **Validates: Requirements 4.2-4.9**

- [x] 2.3 Написать property тест для значений по умолчанию
  - **Property 8: Configuration Default Values**
  - **Validates: Requirements 4.10**

- [x] 2.4 Написать property тест для валидации конфигурации
  - **Property 9: Configuration Validation**
  - **Validates: Requirements 4.11**

- [x] 3. Создать модули подключения к базам данных и S3
  - [x] 3.1 Реализовать core/database.py
    - Создать engine для main database
    - Создать engine для vector database
    - Реализовать SessionLocal для обеих БД
    - Создать Base класс для моделей
    - Реализовать dependency функции get_main_db() и get_vector_db()
    - _Requirements: 4.6, 4.7_

  - [x] 3.2 Реализовать core/s3.py
    - Создать функцию get_s3_client() с конфигурацией для Beget S3
    - Реализовать функцию upload_image()
    - Реализовать функцию download_image()
    - Добавить обработку ошибок S3
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 3.3 Написать unit тесты для database.py
  - Тест создания engine с правильными параметрами
  - Тест dependency функций с mock БД
  - _Requirements: 4.6, 4.7_

- [x] 3.4 Написать unit тесты для s3.py
  - Тест инициализации S3 клиента
  - Тест upload_image с mock boto3
  - Тест download_image с mock boto3
  - Тест обработки ошибок
  - _Requirements: 4.3, 4.4, 4.5_

- [-] 4. Создать модели данных (SQLAlchemy и Pydantic)
  - [x] 4.1 Реализовать models/user.py
    - Создать SQLAlchemy модель User
    - Добавить поля: id, email, full_name, is_active, timestamps
    - _Requirements: 2.5_

  - [x] 4.2 Реализовать models/face.py
    - Создать SQLAlchemy модель Face для main database
    - Создать SQLAlchemy модель FaceEmbedding для vector database
    - Добавить Vector column с pgvector
    - Настроить relationships
    - _Requirements: 2.5, 3.4_

  - [x] 4.3 Реализовать app/schemas/face.py
    - Создать Pydantic схемы: FaceUploadRequest, FaceUploadResponse
    - Создать схемы: FaceSearchRequest, FaceSearchResult, FaceSearchResponse
    - Добавить валидацию полей
    - _Requirements: 2.5_

- [-] 4.4 Написать unit тесты для моделей
  - Тест создания экземпляров моделей
  - Тест Pydantic валидации
  - Тест сериализации/десериализации
  - _Requirements: 2.5_

- [-] 5. Создать скрипт инициализации базы данных
  - Реализовать scripts/init_db.py
  - Добавить функцию init_vector_extension() для создания pgvector extension
  - Добавить функцию create_tables() для создания всех таблиц
  - Добавить обработку ошибок с логированием
  - Добавить функцию main() для оркестрации
  - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6_

- [ ] 5.1 Написать unit тесты для init_db.py
  - Тест наличия SQL команды CREATE EXTENSION
  - Тест логирования при успехе
  - Тест логирования и exit code при ошибке
  - _Requirements: 5.3, 5.5, 5.6_

- [-] 6. Создать Celery конфигурацию
  - Реализовать workers/celery_app.py
  - Настроить Celery с broker и backend из конфигурации
  - Настроить сериализацию, таймауты, timezone
  - Добавить include для автоматического обнаружения задач
  - Создать заглушку workers/tasks.py для будущих задач
  - _Requirements: 2.4, 4.8, 4.9_

- [ ] 6.1 Написать unit тесты для celery_app.py
  - Тест конфигурации Celery
  - Тест правильности broker URL
  - _Requirements: 4.8, 4.9_

- [ ] 7. Создать базовое FastAPI приложение
  - [x] 7.1 Реализовать app/main.py
    - Создать FastAPI приложение
    - Добавить metadata (title, version, description)
    - Подключить роутеры
    - Добавить CORS middleware
    - _Requirements: 2.1_

  - [x] 7.2 Создать health check endpoint
    - Реализовать app/api/v1/endpoints/health.py
    - Добавить GET /health endpoint
    - Добавить проверку подключения к БД и Redis
    - _Requirements: 2.1_

  - [x] 7.3 Создать структуру для API роутеров
    - Создать app/api/v1/router.py для объединения endpoints
    - Создать app/api/deps.py для dependency injection
    - Создать заглушку app/api/v1/endpoints/faces.py для будущих endpoints
    - _Requirements: 2.1_

- [ ] 7.4 Написать unit тесты для FastAPI приложения
  - Тест создания приложения
  - Тест health check endpoint
  - _Requirements: 2.1_

- [x] 8. Checkpoint - Проверка базовой структуры кода
  - Убедиться, что все модули импортируются без ошибок
  - Проверить, что конфигурация загружается корректно
  - Задать вопросы пользователю, если что-то неясно

- [-] 9. Создать Dockerfile
  - Использовать python:3.11-slim как базовый образ
  - Установить системные зависимости для face recognition библиотек
  - Скопировать и установить requirements.txt
  - Скопировать код приложения
  - Создать non-root пользователя для безопасности
  - Установить WORKDIR /code
  - Добавить CMD по умолчанию
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 9.1 Написать тесты для Dockerfile
  - Тест наличия FROM с Python образом
  - Тест наличия COPY requirements.txt
  - Тест наличия RUN pip install
  - Тест наличия WORKDIR
  - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7_

- [-] 10. Создать docker-compose.yml
  - Определить service db_main с postgres:16
  - Определить service db_vector с ankane/pgvector:latest
  - Определить service redis с redis:7-alpine
  - Определить service app с build из Dockerfile
  - Определить service worker с build из Dockerfile
  - Настроить volumes для всех БД и Redis
  - Настроить health checks для всех сервисов
  - Настроить depends_on с условиями health checks
  - Настроить environment variables через env_file
  - Экспонировать порт 8000 для app
  - Создать named network fecapass-network
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 10.1 Написать property тест для docker-compose.yml
  - **Property 1: Docker Compose Service Configuration Completeness**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

- [ ] 10.2 Написать property тест для паритета зависимостей контейнеров
  - **Property 2: Container Dependency Parity**
  - **Validates: Requirements 1.6**

- [ ] 10.3 Написать property тест для volumes БД
  - **Property 3: Database Volume Persistence**
  - **Validates: Requirements 1.7**

- [ ] 10.4 Написать property тест для экспонирования портов
  - **Property 4: API Port Exposure**
  - **Validates: Requirements 1.9**

- [ ] 10.5 Написать property тест для health check зависимостей
  - **Property 10: Service Health Check Dependencies**
  - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

- [x] 11. Создать документацию для запуска
  - Создать README.md с инструкциями по запуску
  - Добавить примеры команд docker-compose
  - Документировать процесс инициализации БД
  - Добавить примеры API запросов
  - Документировать структуру проекта

- [x] 12. Final Checkpoint - Проверка полной интеграции
  - Запустить docker-compose up и убедиться, что все контейнеры стартуют
  - Выполнить init_db.py для инициализации БД
  - Проверить health check endpoint
  - Убедиться, что все тесты проходят
  - Задать вопросы пользователю, если возникли проблемы

## Notes

- Все задачи являются обязательными для комплексной реализации с тестированием
- Каждая задача ссылается на конкретные требования для отслеживаемости
- Checkpoints обеспечивают инкрементальную валидацию
- Property тесты валидируют универсальные свойства корректности
- Unit тесты валидируют конкретные примеры и граничные случаи
- Все property тесты должны выполняться минимум 100 итераций
