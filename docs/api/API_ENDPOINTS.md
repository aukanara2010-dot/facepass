# FacePass API Endpoints

## 🚀 Доступные URL после интеграции

### Базовые endpoints

#### Root
- **GET** `/` - Корневой endpoint с информацией о версии API

#### Документация
- **GET** `/docs` - Swagger UI (интерактивная документация)
- **GET** `/redoc` - ReDoc (альтернативная документация)
- **GET** `/openapi.json` - OpenAPI спецификация

---

### Health Check

#### Проверка здоровья системы
- **GET** `/api/v1/health` - Проверка подключения к БД и Redis
  - Возвращает статус: `healthy` или `unhealthy`
  - Проверяет: main database, Redis

---

### Users (Пользователи)

#### Создание пользователя
- **POST** `/api/v1/users/`
  - Body: `{"email": "user@example.com", "full_name": "John Doe"}`
  - Response: `UserResponse` с ID и данными пользователя

#### Список пользователей
- **GET** `/api/v1/users/`
  - Query params: `skip` (default: 0), `limit` (default: 100)
  - Response: Массив `UserResponse`

#### Получить пользователя
- **GET** `/api/v1/users/{user_id}`
  - Response: `UserResponse` с данными пользователя

#### Удалить пользователя
- **DELETE** `/api/v1/users/{user_id}`
  - Response: 204 No Content

---

### Faces (Лица)

#### Загрузить лицо
- **POST** `/api/v1/faces/upload`
  - Content-Type: `multipart/form-data`
  - Form fields:
    - `user_id`: integer (ID пользователя)
    - `file`: image file (JPG, PNG)
  - Response: `FaceUploadResponse`
    ```json
    {
      "face_id": 1,
      "image_url": "https://s3.beget.com/bucket/faces/1/uuid.jpg",
      "confidence": 0.85,
      "task_id": "celery-task-uuid"
    }
    ```
  - Действия:
    1. Загружает изображение в S3
    2. Создает запись Face в БД
    3. Запускает Celery задачу для извлечения эмбеддинга

#### Получить лица пользователя
- **GET** `/api/v1/faces/user/{user_id}`
  - Response: Массив `FaceUploadResponse` со всеми лицами пользователя

#### Получить информацию о лице
- **GET** `/api/v1/faces/{face_id}`
  - Response: Детальная информация о лице
    ```json
    {
      "id": 1,
      "user_id": 1,
      "image_url": "https://...",
      "s3_key": "faces/1/uuid.jpg",
      "confidence": 0.85,
      "created_at": "2024-02-08T10:00:00Z"
    }
    ```

#### Удалить лицо
- **DELETE** `/api/v1/faces/{face_id}`
  - Response: 204 No Content

#### Поиск похожих лиц
- **POST** `/api/v1/faces/search`
  - Content-Type: `multipart/form-data`
  - Form fields:
    - `file`: image file (лицо для поиска)
    - `threshold`: float (default: 0.7) - порог схожести
    - `limit`: integer (default: 10) - максимум результатов
  - Response: `FaceSearchResponse`
    ```json
    {
      "results": [
        {
          "face_id": 1,
          "user_id": 1,
          "similarity": 0.95,
          "image_url": "https://..."
        }
      ],
      "query_time_ms": 45.2
    }
    ```
  - **Примечание**: Полная реализация требует интеграции InsightFace

---

## 🔧 Celery Tasks (Фоновые задачи)

### Зарегистрированные задачи

1. **workers.tasks.test_task**
   - Тестовая задача для проверки работы Celery
   - Параметры: `message` (string)

2. **workers.tasks.process_face_embedding**
   - Обработка лица: извлечение эмбеддинга и сохранение в векторную БД
   - Параметры: `face_id` (int), `s3_key` (string)
   - Действия:
     1. Скачивает изображение из S3
     2. Детектирует лицо (TODO: InsightFace)
     3. Извлекает эмбеддинг (512-мерный вектор)
     4. Сохраняет в векторную БД
     5. Обновляет confidence в Face записи

3. **workers.tasks.search_similar_faces**
   - Поиск похожих лиц по эмбеддингу
   - Параметры: `embedding` (list), `threshold` (float), `limit` (int)
   - Использует pgvector для векторного поиска

---

## 📊 Примеры использования

### 1. Создать пользователя
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "full_name": "John Doe"}'
```

### 2. Загрузить лицо
```bash
curl -X POST "http://localhost:8000/api/v1/faces/upload" \
  -F "user_id=1" \
  -F "file=@/path/to/face.jpg"
```

### 3. Получить лица пользователя
```bash
curl "http://localhost:8000/api/v1/faces/user/1"
```

### 4. Поиск похожих лиц
```bash
curl -X POST "http://localhost:8000/api/v1/faces/search" \
  -F "file=@/path/to/query_face.jpg" \
  -F "threshold=0.7" \
  -F "limit=10"
```

### 5. Проверить здоровье системы
```bash
curl "http://localhost:8000/api/v1/health"
```

---

## 🔍 Проверка Celery задач

### Просмотр зарегистрированных задач
```bash
docker-compose exec worker celery -A workers.celery_app inspect registered
```

### Просмотр активных задач
```bash
docker-compose exec worker celery -A workers.celery_app inspect active
```

### Запуск тестовой задачи
```bash
docker-compose exec app python -c "
from workers.tasks import test_task
result = test_task.delay('Hello World')
print(f'Task ID: {result.id}')
print(f'Result: {result.get(timeout=10)}')
"
```

---

## 📝 Схемы данных (Pydantic Models)

### UserCreate
```json
{
  "email": "user@example.com",
  "full_name": "John Doe"  // optional
}
```

### UserResponse
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true
}
```

### FaceUploadResponse
```json
{
  "face_id": 1,
  "image_url": "https://s3.beget.com/bucket/faces/1/uuid.jpg",
  "confidence": 0.85,
  "task_id": "celery-task-uuid"
}
```

### FaceSearchResult
```json
{
  "face_id": 1,
  "user_id": 1,
  "similarity": 0.95,
  "image_url": "https://..."
}
```

### FaceSearchResponse
```json
{
  "results": [FaceSearchResult, ...],
  "query_time_ms": 45.2
}
```

---

## ⚠️ Важные замечания

1. **Foreign Key между базами**: FaceEmbedding.face_id НЕ использует ForeignKey, так как это разные базы данных
2. **InsightFace интеграция**: Пока используются dummy embeddings. Для production нужно интегрировать InsightFace
3. **S3 credentials**: Убедитесь, что в .env файле указаны правильные credentials для Beget S3
4. **Векторный поиск**: Требует полной реализации с pgvector операторами (<->, <#>, <=>)

---

## 🚀 Быстрый старт

```bash
# 1. Запустить все сервисы
docker-compose up -d

# 2. Инициализировать БД
docker-compose exec app python scripts/init_db.py

# 3. Проверить health
curl http://localhost:8000/api/v1/health

# 4. Открыть документацию
open http://localhost:8000/docs

# 5. Проверить Celery задачи
docker-compose logs -f worker
```
