# FacePass v2.0 - Isolated Face Recognition Microservice

FacePass - автономный микросервис распознавания лиц с векторным поиском на базе PostgreSQL + pgvector и InsightFace.

## 🎯 Описание

FacePass v2.0 - это полностью изолированный микросервис для индексации и поиска лиц на фотографиях. Сервис работает только с `photo_id` и векторными представлениями лиц, предоставляя чистый REST API для интеграции.

### Ключевые возможности

- ✅ Извлечение face embeddings с помощью InsightFace
- ✅ Векторный поиск с использованием pgvector (cosine similarity)
- ✅ Batch индексация для высокой производительности
- ✅ API Key authentication для защищенных endpoints
- ✅ Rate limiting (100 req/min для индексации, 1000 req/min для поиска)
- ✅ Structured logging (JSON format)
- ✅ Health checks и Prometheus metrics
- ✅ Input validation и security headers
- ✅ Идемпотентные операции

## 🏗️ Архитектура

```
┌─────────────────────────────────────┐
│         FacePass v2.0               │
│                                     │
│  ✅ Face embedding extraction       │
│  ✅ Vector storage (pgvector)       │
│  ✅ Similarity search               │
│  ✅ API для индексации              │
│  ✅ API для поиска                  │
│  ✅ API Key authentication          │
│  ✅ Observability (metrics, logs)   │
└─────────────────────────────────────┘
```

### Технологический стек

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL 16 + pgvector
- **Face Recognition**: InsightFace (buffalo_l model)
- **Cache**: Redis 7
- **Monitoring**: Prometheus
- **Deployment**: Docker, Docker Compose

## 🚀 Быстрый старт

### Требования

- Docker и Docker Compose
- 4GB+ RAM
- 10GB+ свободного места

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd facepass
```

2. Создайте `.env` файл:
```bash
cp .env.example .env
```

3. Настройте переменные окружения в `.env`:
```env
# Application
APP_NAME=FacePass
APP_VERSION=2.0.0
DEBUG=False

# Database
POSTGRES_USER=facepass_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=facepass_vector
POSTGRES_HOST=db_vector
POSTGRES_PORT=5432

# S3 Storage
S3_ENDPOINT=https://s3.beget.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=facepass-images
S3_REGION=ru-1

# Security
API_KEYS=key1_abc123,key2_def456,key3_ghi789
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Face Recognition
FACE_SIMILARITY_THRESHOLD=0.5
FACE_DETECTION_THRESHOLD=0.6
EMBEDDING_DIMENSION=512
```

4. Запустите сервисы:
```bash
docker-compose up -d
```

5. Проверьте health:
```bash
curl http://localhost:8000/api/v1/health
```

## 📋 API Endpoints

### Protected Endpoints (требуют X-API-Key)

#### POST /api/v1/index
Индексация одного фото.

```bash
curl -X POST "http://localhost:8000/api/v1/index" \
  -H "X-API-Key: your-api-key" \
  -F "photo_id=photo123" \
  -F "session_id=session-uuid" \
  -F "file=@photo.jpg"
```

**Response:**
```json
{
  "indexed": true,
  "photo_id": "photo123",
  "confidence": 0.98,
  "faces_detected": 1
}
```

#### POST /api/v1/index/batch
Batch индексация нескольких фото.

```bash
curl -X POST "http://localhost:8000/api/v1/index/batch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "photos": [
      {"photo_id": "photo1", "s3_key": "sessions/uuid/photo1.jpg"},
      {"photo_id": "photo2", "s3_key": "sessions/uuid/photo2.jpg"}
    ]
  }'
```

**Response:**
```json
{
  "indexed": 98,
  "failed": 2,
  "total": 100,
  "errors": ["photo3.jpg: No face detected"]
}
```

#### DELETE /api/v1/index/{session_id}
Удаление всех embeddings для сессии.

```bash
curl -X DELETE "http://localhost:8000/api/v1/index/session-uuid" \
  -H "X-API-Key: your-api-key"
```

### Public Endpoints

#### POST /api/v1/search
Поиск похожих лиц.

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -F "session_id=session-uuid" \
  -F "file=@selfie.jpg" \
  -F "threshold=0.7" \
  -F "limit=100"
```

**Response:**
```json
{
  "matches": [
    {"photo_id": "photo1", "similarity": 0.95, "confidence": 0.98},
    {"photo_id": "photo5", "similarity": 0.87, "confidence": 0.96}
  ],
  "query_time_ms": 123.45,
  "total_matches": 2,
  "indexed_photos": 98
}
```

#### GET /api/v1/search/status/{session_id}
Проверка статуса индексации.

```bash
curl "http://localhost:8000/api/v1/search/status/session-uuid"
```

**Response:**
```json
{
  "indexed": true,
  "session_id": "session-uuid",
  "photo_count": 98,
  "last_indexed": "2024-02-26T10:30:00Z"
}
```

#### GET /api/v1/health
Health check endpoint.

```bash
curl "http://localhost:8000/api/v1/health"
```

#### GET /api/v1/metrics
Prometheus metrics.

```bash
curl "http://localhost:8000/api/v1/metrics"
```

## 📊 Monitoring

### Prometheus

Prometheus доступен по адресу: `http://localhost:9090`

Метрики:
- `search_requests_total` - количество поисковых запросов
- `search_duration_seconds` - длительность поиска
- `index_requests_total` - количество запросов индексации
- `index_duration_seconds` - длительность индексации
- `embeddings_total` - общее количество embeddings
- `db_connections_active` - активные подключения к БД

### Logs

Просмотр логов:
```bash
docker-compose logs -f app
```

Логи в JSON формате с structured logging.

## 🔒 Безопасность

### API Key Authentication

Защищенные endpoints требуют `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" ...
```

Настройка в `.env`:
```env
API_KEYS=key1,key2,key3
```

### Rate Limiting

- Indexing endpoints: 100 requests/minute per API key
- Search endpoints: 1000 requests/minute per IP

### Input Validation

- File size limit: 10MB
- Image dimensions: 10x10 min, 4096x4096 max
- Allowed formats: JPEG, PNG, WebP, HEIC
- SQL injection prevention
- Parameter validation (Pydantic)

## 🗄️ Database Migration

### Миграция на v2.0

1. Создайте backup:
```bash
./scripts/backup_database.sh
```

2. Выполните миграцию:
```bash
docker-compose exec db_vector psql -U facepass_user -d facepass_vector -f /code/scripts/migration_v2.sql
```

3. Проверьте результат:
```bash
docker-compose exec db_vector psql -U facepass_user -d facepass_vector -c "\d face_embeddings"
```

### Rollback

```bash
docker-compose exec db_vector psql -U facepass_user -d facepass_vector -f /code/scripts/rollback_v2.sql
```

## 🧪 Тестирование

### Manual Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Index test photo
curl -X POST "http://localhost:8000/api/v1/index" \
  -H "X-API-Key: test-key" \
  -F "photo_id=test1" \
  -F "session_id=test-session" \
  -F "file=@test.jpg"

# Search
curl -X POST "http://localhost:8000/api/v1/search" \
  -F "session_id=test-session" \
  -F "file=@selfie.jpg"
```

## 📖 API Documentation

Интерактивная документация доступна по адресу:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔧 Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

См. `.env.example` для полного списка переменных окружения.

## 📦 Deployment

### Production Checklist

- [ ] Настроить production `.env`
- [ ] Сгенерировать secure API keys
- [ ] Настроить CORS origins
- [ ] Выполнить database migration
- [ ] Настроить backup strategy
- [ ] Настроить monitoring (Prometheus + Grafana)
- [ ] Настроить log aggregation
- [ ] Провести load testing
- [ ] Настроить SSL/TLS
- [ ] Настроить firewall rules

### Docker Compose Production

```bash
docker-compose -f docker-compose.yml up -d
```

## 🤝 Integration Example

### Python Client

```python
import requests

API_URL = "http://localhost:8000/api/v1"
API_KEY = "your-api-key"

# Index photos
def index_photos(session_id, photos):
    response = requests.post(
        f"{API_URL}/index/batch",
        headers={"X-API-Key": API_KEY},
        json={
            "session_id": session_id,
            "photos": [
                {"photo_id": p["id"], "s3_key": p["s3_key"]}
                for p in photos
            ]
        }
    )
    return response.json()

# Search faces
def search_faces(session_id, selfie_path):
    with open(selfie_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/search",
            files={"file": f},
            data={"session_id": session_id, "threshold": 0.7}
        )
    return response.json()
```

## 📝 License

[Your License]

## 👥 Authors

[Your Team]

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Version**: 2.0.0  
**Status**: Production Ready  
**Last Updated**: 2024-02-26
