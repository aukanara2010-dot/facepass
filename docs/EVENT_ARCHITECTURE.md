# 🎉 FacePass Event Architecture

## 📋 Обзор изменений

FacePass переделан для работы с **мероприятиями** вместо пользователей.

### Основная концепция:
1. **Фотограф** создает мероприятие и загружает фотографии
2. **Участники** ищут свои фотографии по селфи в рамках конкретного мероприятия
3. **Поиск изолирован** - участник видит только фотографии своего мероприятия

---

## 🔄 Изменения в моделях данных

### 1. User → Event
**Было:** `models/user.py` с полями `email`, `full_name`
**Стало:** `models/event.py` с полями:
- `event_uuid` (UUID) - уникальный идентификатор мероприятия
- `name` - название мероприятия
- `description` - описание
- `location` - место проведения
- `event_date` - дата мероприятия
- `is_active` - активно ли мероприятие

### 2. Face.user_id → Face.event_id
**Было:** `Face.user_id` - ссылка на пользователя
**Стало:** `Face.event_id` - ссылка на мероприятие

### 3. FaceEmbedding + event_id
**Добавлено:** `FaceEmbedding.event_id` для быстрой фильтрации при поиске

---

## 🌐 API Endpoints

### Events (Мероприятия)

#### POST /api/v1/events/
Создать мероприятие (фотограф)

**Request:**
```json
{
  "event_uuid": "550e8400-e29b-41d4-a716-446655440000",  // optional
  "name": "Свадьба Иван и Мария",
  "description": "Свадебная церемония",
  "location": "Москва, Парк Горького",
  "event_date": "2024-06-15T15:00:00Z"
}
```

**Response:**
```json
{
  "id": 1,
  "event_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Свадьба Иван и Мария",
  "description": "Свадебная церемония",
  "location": "Москва, Парк Горького",
  "event_date": "2024-06-15T15:00:00Z",
  "is_active": true,
  "created_at": "2024-02-08T10:00:00Z"
}
```

#### GET /api/v1/events/
Список всех мероприятий

#### GET /api/v1/events/uuid/{event_uuid}
Получить мероприятие по UUID (для участников)

#### GET /api/v1/events/{event_id}
Получить мероприятие по ID

#### PATCH /api/v1/events/{event_id}
Обновить мероприятие

#### DELETE /api/v1/events/{event_id}
Удалить мероприятие

---

### Faces (Фотографии)

#### POST /api/v1/faces/upload
Загрузить фотографию (фотограф)

**Request (multipart/form-data):**
- `event_id`: integer - ID мероприятия
- `file`: image file - фотография

**Response:**
```json
{
  "face_id": 123,
  "image_url": "https://s3.beget.com/bucket/events/1/uuid.jpg",
  "confidence": 0.85,
  "task_id": "celery-task-uuid"
}
```

#### GET /api/v1/faces/event/{event_id}
Получить все фотографии мероприятия (фотограф)

#### POST /api/v1/faces/search ⭐ ГЛАВНЫЙ ENDPOINT
Поиск фотографий по селфи (участник)

**Request (multipart/form-data):**
- `event_id`: integer - ID мероприятия
- `file`: image file - селфи участника
- `threshold`: float (optional, default: 0.7) - порог схожести
- `limit`: integer (optional, default: 10) - макс. результатов

**Response:**
```json
{
  "results": [
    {
      "face_id": 123,
      "event_id": 1,
      "similarity": 0.95,
      "image_url": "https://s3.beget.com/bucket/events/1/photo1.jpg"
    },
    {
      "face_id": 124,
      "event_id": 1,
      "similarity": 0.88,
      "image_url": "https://s3.beget.com/bucket/events/1/photo2.jpg"
    }
  ],
  "query_time_ms": 45.2,
  "task_id": "celery-task-uuid"
}
```

**ВАЖНО:** Поиск происходит **ТОЛЬКО** в рамках указанного `event_id`!

---

## 🔧 Celery Tasks

### process_face_embedding(face_id, s3_key, event_id)
Обработка загруженной фотографии:
1. Скачивает изображение из S3
2. Детектирует лицо (InsightFace)
3. Извлекает эмбеддинг (512-мерный вектор)
4. Сохраняет в векторную БД **с event_id**
5. Обновляет confidence в Face

### search_similar_faces_task(image_data, event_id, threshold, limit)
Поиск похожих лиц:
1. Извлекает эмбеддинг из селфи
2. Ищет похожие эмбеддинги **только в event_id**
3. Возвращает топ-N совпадений

**КРИТИЧНО:** Фильтрация по `event_id` обязательна!

---

## 🗄️ Структура БД

### Main Database (db_main)

#### Table: events
```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_uuid UUID UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    location VARCHAR,
    event_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_events_uuid ON events(event_uuid);
CREATE INDEX idx_events_active ON events(is_active);
```

#### Table: faces
```sql
CREATE TABLE faces (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,  -- NO FOREIGN KEY
    image_url VARCHAR NOT NULL,
    s3_key VARCHAR NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_faces_event_id ON faces(event_id);
```

### Vector Database (db_vector)

#### Table: face_embeddings
```sql
CREATE TABLE face_embeddings (
    id SERIAL PRIMARY KEY,
    face_id INTEGER NOT NULL,     -- NO FOREIGN KEY
    event_id INTEGER NOT NULL,    -- Denormalized for fast filtering
    embedding VECTOR(512) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_face_embeddings_face_id ON face_embeddings(face_id);
CREATE INDEX idx_face_embeddings_event_id ON face_embeddings(event_id);

-- Vector similarity index (for fast search)
CREATE INDEX idx_face_embeddings_vector ON face_embeddings 
USING ivfflat (embedding vector_cosine_ops);
```

---

## 🔍 Пример использования

### Сценарий: Свадьба

#### 1. Фотограф создает мероприятие
```bash
curl -X POST "http://localhost:8000/api/v1/events/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Свадьба Иван и Мария",
    "location": "Москва",
    "event_date": "2024-06-15T15:00:00Z"
  }'

# Response: {"id": 1, "event_uuid": "550e8400-...", ...}
```

#### 2. Фотограф загружает фотографии
```bash
# Загрузить 100 фотографий
for i in {1..100}; do
  curl -X POST "http://localhost:8000/api/v1/faces/upload" \
    -F "event_id=1" \
    -F "file=@photo_$i.jpg"
done
```

#### 3. Участник ищет свои фотографии
```bash
# Участник загружает селфи
curl -X POST "http://localhost:8000/api/v1/faces/search" \
  -F "event_id=1" \
  -F "file=@my_selfie.jpg" \
  -F "threshold=0.7" \
  -F "limit=20"

# Response: список фотографий, где участник найден
```

---

## 🔒 Безопасность и изоляция

### Изоляция по мероприятиям
- ✅ Каждый поиск фильтруется по `event_id`
- ✅ Участник мероприятия А не может видеть фотографии мероприятия Б
- ✅ Даже если UUID мероприятия известен, поиск ограничен

### Рекомендации
1. **Аутентификация фотографов** - добавить JWT токены
2. **Rate limiting** - ограничить количество поисков
3. **Валидация event_uuid** - проверять права доступа
4. **Логирование** - записывать все поиски для аудита

---

## 📊 Производительность

### Оптимизация поиска

#### 1. Индексы
```sql
-- Обязательные индексы
CREATE INDEX idx_face_embeddings_event_id ON face_embeddings(event_id);
CREATE INDEX idx_face_embeddings_vector ON face_embeddings 
  USING ivfflat (embedding vector_cosine_ops);
```

#### 2. Денормализация
`FaceEmbedding.event_id` - денормализованное поле для быстрой фильтрации без JOIN

#### 3. Партиционирование (опционально)
Для больших объемов можно партиционировать `face_embeddings` по `event_id`:
```sql
CREATE TABLE face_embeddings (
    ...
) PARTITION BY HASH (event_id);
```

---

## 🚀 Миграция данных

Если у вас уже есть данные с `user_id`:

```sql
-- 1. Создать таблицу events
CREATE TABLE events (...);

-- 2. Мигрировать users в events
INSERT INTO events (event_uuid, name, description, created_at)
SELECT 
    gen_random_uuid(),
    CONCAT('Event for user ', email),
    full_name,
    created_at
FROM users;

-- 3. Обновить faces.user_id -> faces.event_id
ALTER TABLE faces RENAME COLUMN user_id TO event_id;

-- 4. Обновить face_embeddings
ALTER TABLE face_embeddings ADD COLUMN event_id INTEGER;
UPDATE face_embeddings fe
SET event_id = f.event_id
FROM faces f
WHERE fe.face_id = f.id;

-- 5. Удалить старую таблицу users
DROP TABLE users;
```

---

## ✅ Checklist для запуска

- [ ] Пересоздать таблицы: `docker-compose exec app python scripts/init_db.py`
- [ ] Проверить индексы в векторной БД
- [ ] Создать тестовое мероприятие
- [ ] Загрузить тестовые фотографии
- [ ] Протестировать поиск с селфи
- [ ] Проверить изоляцию между мероприятиями
- [ ] Настроить мониторинг производительности

---

## 📚 Дополнительные ресурсы

- **pgvector документация**: https://github.com/pgvector/pgvector
- **InsightFace**: https://github.com/deepinsight/insightface
- **FastAPI**: https://fastapi.tiangolo.com/

---

## 🎯 Следующие шаги

1. **Интеграция InsightFace** - реальное извлечение эмбеддингов
2. **Векторный поиск** - реализация с pgvector операторами
3. **Аутентификация** - JWT для фотографов
4. **Frontend** - интерфейс для участников
5. **Аналитика** - статистика по мероприятиям

---

**FacePass Event Architecture готова к использованию!** 🎉
