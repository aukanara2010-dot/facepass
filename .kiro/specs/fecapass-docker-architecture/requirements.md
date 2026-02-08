# Requirements Document

## Introduction

Fecapass - это сервис распознавания лиц, который требует модульной Docker-архитектуры для поддержки масштабирования и расширения функциональности. Система должна обеспечивать обработку изображений с использованием AI, хранение векторных представлений лиц, асинхронную обработку задач и интеграцию с внешним S3-хранилищем.

## Glossary

- **System**: Fecapass Docker Infrastructure
- **Docker_Compose**: Конфигурационный файл для оркестрации контейнеров
- **Main_Database**: PostgreSQL база данных для основных данных приложения
- **Vector_Database**: PostgreSQL база данных с расширением pgvector для хранения векторных представлений
- **Redis_Cache**: Redis сервер для кэширования и очередей Celery
- **API_Container**: Docker контейнер с FastAPI приложением
- **Worker_Container**: Docker контейнер с Celery workers для асинхронной обработки
- **S3_Storage**: Beget S3 хранилище для изображений
- **Environment_Config**: Конфигурационный файл .env с секретами и настройками
- **Init_Script**: Скрипт инициализации базы данных

## Requirements

### Requirement 1: Docker Compose Configuration

**User Story:** Как DevOps инженер, я хочу иметь docker-compose.yml файл, чтобы легко развернуть все сервисы проекта одной командой.

#### Acceptance Criteria

1. THE Docker_Compose SHALL define a service named "db_main" using postgres:16 image
2. THE Docker_Compose SHALL define a service named "db_vector" using ankane/pgvector:latest image
3. THE Docker_Compose SHALL define a service named "redis" using official Redis image
4. THE Docker_Compose SHALL define a service named "app" for the FastAPI application
5. THE Docker_Compose SHALL define a service named "worker" for Celery tasks
6. WHEN the Worker_Container is created, THE System SHALL ensure it has access to the same dependencies as API_Container
7. THE Docker_Compose SHALL configure persistent volumes for both databases
8. THE Docker_Compose SHALL configure network connectivity between all services
9. THE Docker_Compose SHALL expose appropriate ports for external access to API_Container

### Requirement 2: Project Structure

**User Story:** Как разработчик, я хочу иметь четкую модульную структуру папок, чтобы легко ориентироваться в проекте и поддерживать его расширение.

#### Acceptance Criteria

1. THE System SHALL create a directory "/app" for API logic and routes
2. THE System SHALL create a directory "/core" for configuration and database connections
3. THE System SHALL create a directory "/services" for AI processing and vector operations
4. THE System SHALL create a directory "/workers" for Celery task definitions
5. THE System SHALL create a directory "/models" for SQLAlchemy and Pydantic schemas
6. WHEN new modules are added, THE System SHALL maintain separation of concerns between directories

### Requirement 3: Python Dependencies

**User Story:** Как разработчик, я хочу иметь requirements.txt со всеми необходимыми зависимостями, чтобы обеспечить воспроизводимость окружения.

#### Acceptance Criteria

1. THE System SHALL include fastapi in requirements.txt
2. THE System SHALL include uvicorn in requirements.txt for ASGI server
3. THE System SHALL include sqlalchemy in requirements.txt for ORM
4. THE System SHALL include pgvector in requirements.txt for vector operations
5. THE System SHALL include boto3 in requirements.txt for S3 integration
6. THE System SHALL include insightface in requirements.txt for face recognition
7. THE System SHALL include onnxruntime in requirements.txt for AI model inference
8. THE System SHALL include celery in requirements.txt for task queue
9. THE System SHALL include redis in requirements.txt for Celery broker
10. THE System SHALL include psycopg2-binary in requirements.txt for PostgreSQL connectivity
11. THE System SHALL include python-dotenv in requirements.txt for environment variable management

### Requirement 4: Configuration Management

**User Story:** Как системный администратор, я хочу централизованное управление конфигурацией через .env файл, чтобы безопасно управлять секретами и настройками окружения.

#### Acceptance Criteria

1. THE System SHALL create a core/config.py file for configuration management
2. WHEN core/config.py is loaded, THE System SHALL read S3_KEY from Environment_Config
3. WHEN core/config.py is loaded, THE System SHALL read S3_SECRET from Environment_Config
4. WHEN core/config.py is loaded, THE System SHALL read S3_ENDPOINT from Environment_Config
5. WHEN core/config.py is loaded, THE System SHALL read S3_BUCKET from Environment_Config
6. WHEN core/config.py is loaded, THE System SHALL read MAIN_DB_URL from Environment_Config
7. WHEN core/config.py is loaded, THE System SHALL read VECTOR_DB_URL from Environment_Config
8. WHEN core/config.py is loaded, THE System SHALL read REDIS_URL from Environment_Config
9. WHEN core/config.py is loaded, THE System SHALL read CELERY_BROKER_URL from Environment_Config
10. THE System SHALL provide default values for non-sensitive configuration parameters
11. THE System SHALL validate that all required configuration parameters are present

### Requirement 5: Database Initialization

**User Story:** Как администратор базы данных, я хочу иметь скрипт инициализации, чтобы автоматически настроить расширение pgvector в векторной базе данных.

#### Acceptance Criteria

1. THE System SHALL create an init_db.py script
2. WHEN init_db.py is executed, THE System SHALL connect to Vector_Database
3. WHEN connected to Vector_Database, THE System SHALL execute "CREATE EXTENSION IF NOT EXISTS vector"
4. IF the pgvector extension already exists, THEN THE System SHALL continue without errors
5. IF the connection to Vector_Database fails, THEN THE System SHALL log an error message and exit with non-zero status
6. WHEN init_db.py completes successfully, THE System SHALL log a confirmation message

### Requirement 6: Container Dependencies and Build

**User Story:** Как DevOps инженер, я хочу чтобы контейнеры правильно собирались и имели все необходимые зависимости, чтобы приложение работало корректно.

#### Acceptance Criteria

1. THE System SHALL create a Dockerfile for API_Container
2. THE System SHALL create a Dockerfile for Worker_Container
3. WHEN API_Container is built, THE System SHALL install all dependencies from requirements.txt
4. WHEN Worker_Container is built, THE System SHALL install all dependencies from requirements.txt
5. THE System SHALL use the same base Python image for both API_Container and Worker_Container
6. THE System SHALL copy application code into both containers
7. THE System SHALL set appropriate working directories in both containers

### Requirement 7: Service Health and Startup Order

**User Story:** Как DevOps инженер, я хочу чтобы сервисы запускались в правильном порядке, чтобы избежать ошибок подключения при старте.

#### Acceptance Criteria

1. WHEN Docker_Compose starts services, THE API_Container SHALL wait for Main_Database to be ready
2. WHEN Docker_Compose starts services, THE API_Container SHALL wait for Vector_Database to be ready
3. WHEN Docker_Compose starts services, THE API_Container SHALL wait for Redis_Cache to be ready
4. WHEN Docker_Compose starts services, THE Worker_Container SHALL wait for Redis_Cache to be ready
5. WHEN Docker_Compose starts services, THE Worker_Container SHALL wait for both databases to be ready

### Requirement 8: Environment Variables Template

**User Story:** Как разработчик, я хочу иметь шаблон .env файла, чтобы понимать какие переменные окружения необходимо настроить.

#### Acceptance Criteria

1. THE System SHALL create a .env.example file
2. THE System SHALL document all required S3 configuration variables in .env.example
3. THE System SHALL document all required database connection variables in .env.example
4. THE System SHALL document all required Redis configuration variables in .env.example
5. THE System SHALL document all required Celery configuration variables in .env.example
6. THE System SHALL include comments explaining the purpose of each variable

### Requirement 9: Modularity and Extensibility

**User Story:** Как архитектор системы, я хочу чтобы архитектура была модульной, чтобы легко добавлять новые функции без изменения существующего кода.

#### Acceptance Criteria

1. WHEN new API endpoints are added, THE System SHALL allow adding them without modifying core configuration
2. WHEN new Celery tasks are added, THE System SHALL allow adding them in /workers directory without affecting existing tasks
3. WHEN new AI models are integrated, THE System SHALL allow adding them in /services directory
4. THE System SHALL maintain clear separation between API layer, business logic, and data access layers
5. THE System SHALL use dependency injection patterns where appropriate for loose coupling
