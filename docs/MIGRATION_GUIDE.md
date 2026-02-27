# FacePass v2.0 Migration Guide для Pixora

## Обзор изменений

FacePass v2.0 - это полностью изолированный микросервис, который больше не имеет прямого доступа к базе данных Pixora и не выполняет автоматическую синхронизацию. Это breaking change, требующий обновления интеграции со стороны Pixora.

## Breaking Changes

### 1. Удалены автоматические операции

**Было (v1.x):**
- FacePass автоматически синхронизировал фото из Pixora при первом поиске
- FacePass имел прямой доступ к Pixora Database
- FacePass автоматически индексировал фото при поиске

**Стало (v2.0):**
- Pixora должна явно вызывать API индексации
- FacePass работает только с photo_id (без доступа к метаданным)
- Поиск работает только с уже проиндексированными фото

### 2. Изменения в API

#### Удаленные endpoints:
- `POST /api/v2/faces/search-session` (с auto-indexing)
- `GET /api/v2/remote-services/{session_id}` (CORS proxy)
- Все event-based endpoints

#### Новые endpoints:
- `POST /api/v2/index` - индексация одного фото
- `POST /api/v2/index/batch` - batch индексация
- `DELETE /api/v2/index/{session_id}` - удаление сессии
- `POST /api/v2/search` - поиск (без auto-indexing)
- `GET /api/v2/search/status/{session_id}` - статус индексации

### 3. Authentication

**Новое требование:**
- Indexing endpoints требуют `X-API-Key` header
- Search endpoints остаются публичными

## Новая архитектура интеграции

### Разделение ответственности

```
┌─────────────────────────────────────┐
│           Pixora                    │
│                                     │
│  ✅ Управление сессиями             │
│  ✅ Загрузка фото в S3              │
│  ✅ Вызов FacePass API              │
│  ✅ Получение метаданных фото       │
│  ✅ UI/UX для клиентов              │
│  ✅ Бизнес-логика                   │
└─────────────────────────────────────┘
              ↓ API calls
┌─────────────────────────────────────┐
│         FacePass v2.0               │
│                                     │
│  ✅ Face embedding extraction       │
│  ✅ Vector storage (pgvector)       │
│  ✅ Similarity search               │
│  ✅ API для индексации              │
│  ✅ API для поиска                  │
└─────────────────────────────────────┘
```

## Миграция: Пошаговая инструкция

### Шаг 1: Обновление конфигурации Pixora

Добавьте в конфигурацию Pixora:

```python
# config.py
FACEPASS_API_URL = "http://facepass:8000/api/v1"
FACEPASS_API_KEY = "your-secure-api-key"
```

### Шаг 2: Создание клиента FacePass

```python
# services/facepass_client.py
import requests
from typing import List, Dict, Optional

class FacePassClient:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
    
    def index_photo(
        self, 
        photo_id: str, 
        session_id: str, 
        s3_key: str
    ) -> Dict:
        """Индексация одного фото."""
        response = requests.post(
            f"{self.api_url}/index",
            headers=self.headers,
            json={
                "photo_id": photo_id,
                "session_id": session_id,
                "s3_key": s3_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    def index_batch(
        self, 
        session_id: str, 
        photos: List[Dict[str, str]]
    ) -> Dict:
        """Batch индексация фото."""
        response = requests.post(
            f"{self.api_url}/index/batch",
            headers=self.headers,
            json={
                "session_id": session_id,
                "photos": photos
            }
        )
        response.raise_for_status()
        return response.json()
    
    def search_faces(
        self, 
        session_id: str, 
        selfie_data: bytes,
        threshold: float = 0.7,
        limit: int = 1000
    ) -> Dict:
        """Поиск похожих лиц."""
        response = requests.post(
            f"{self.api_url}/search",
            files={"file": selfie_data},
            data={
                "session_id": session_id,
                "threshold": threshold,
                "limit": limit
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_session_status(self, session_id: str) -> Dict:
        """Проверка статуса индексации."""
        response = requests.get(
            f"{self.api_url}/search/status/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def delete_session(self, session_id: str) -> Dict:
        """Удаление всех embeddings для сессии."""
        response = requests.delete(
            f"{self.api_url}/index/{session_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
```

### Шаг 3: Обновление workflow создания сессии

**Старый workflow (v1.x):**
```python
# 1. Создать сессию в Pixora
session = create_photo_session(...)

# 2. Загрузить фото в S3
upload_photos_to_s3(session.id, photos)

# 3. FacePass автоматически индексирует при первом поиске
# (ничего не нужно делать)
```

**Новый workflow (v2.0):**
```python
# 1. Создать сессию в Pixora
session = create_photo_session(...)

# 2. Загрузить фото в S3
s3_keys = upload_photos_to_s3(session.id, photos)

# 3. НОВОЕ: Явно вызвать индексацию в FacePass
facepass = FacePassClient(FACEPASS_API_URL, FACEPASS_API_KEY)

photos_to_index = [
    {"photo_id": photo.id, "s3_key": s3_key}
    for photo, s3_key in zip(photos, s3_keys)
]

result = facepass.index_batch(
    session_id=session.id,
    photos=photos_to_index
)

print(f"Indexed: {result['indexed']}, Failed: {result['failed']}")
```

### Шаг 4: Обновление workflow поиска

**Старый workflow (v1.x):**
```python
# Поиск с автоматической индексацией
results = facepass_search(session_id, selfie)
```

**Новый workflow (v2.0):**
```python
# 1. Проверить статус индексации (опционально)
status = facepass.get_session_status(session_id)
if not status['indexed']:
    raise Exception("Session not indexed yet")

# 2. Выполнить поиск
results = facepass.search_faces(
    session_id=session_id,
    selfie_data=selfie_bytes,
    threshold=0.7
)

# 3. Получить метаданные фото из Pixora
photo_ids = [match['photo_id'] for match in results['matches']]
photos = get_photos_by_ids(photo_ids)  # Pixora API

# 4. Объединить результаты
for match, photo in zip(results['matches'], photos):
    match['url'] = photo.url
    match['metadata'] = photo.metadata
```

### Шаг 5: Обновление workflow удаления сессии

**Новый код:**
```python
# При удалении сессии в Pixora
def delete_photo_session(session_id: str):
    # 1. Удалить embeddings в FacePass
    facepass.delete_session(session_id)
    
    # 2. Удалить фото из S3
    delete_s3_photos(session_id)
    
    # 3. Удалить сессию из Pixora DB
    db.delete(PhotoSession, id=session_id)
```

## Примеры интеграции

### Пример 1: Создание новой сессии

```python
from services.facepass_client import FacePassClient

def create_and_index_session(photos: List[UploadFile]):
    # 1. Создать сессию
    session = PhotoSession.create(
        event_id=event.id,
        status="processing"
    )
    
    # 2. Загрузить в S3
    s3_keys = []
    for photo in photos:
        s3_key = f"sessions/{session.id}/{photo.filename}"
        upload_to_s3(photo.file, s3_key)
        s3_keys.append(s3_key)
        
        # Сохранить в Pixora DB
        Photo.create(
            id=generate_photo_id(),
            session_id=session.id,
            s3_key=s3_key,
            filename=photo.filename
        )
    
    # 3. Индексировать в FacePass
    facepass = FacePassClient(FACEPASS_API_URL, FACEPASS_API_KEY)
    
    photos_data = Photo.filter(session_id=session.id)
    result = facepass.index_batch(
        session_id=session.id,
        photos=[
            {"photo_id": p.id, "s3_key": p.s3_key}
            for p in photos_data
        ]
    )
    
    # 4. Обновить статус
    session.status = "ready" if result['failed'] == 0 else "partial"
    session.indexed_count = result['indexed']
    session.save()
    
    return session
```

### Пример 2: Поиск с обработкой результатов

```python
def search_user_photos(session_id: str, selfie: UploadFile):
    facepass = FacePassClient(FACEPASS_API_URL, FACEPASS_API_KEY)
    
    # 1. Проверить статус
    status = facepass.get_session_status(session_id)
    if not status['indexed']:
        raise HTTPException(
            status_code=400,
            detail="Session not indexed. Please wait."
        )
    
    # 2. Поиск в FacePass
    selfie_bytes = await selfie.read()
    results = facepass.search_faces(
        session_id=session_id,
        selfie_data=selfie_bytes,
        threshold=0.7,
        limit=100
    )
    
    if not results['matches']:
        return {"message": "No matches found", "matches": []}
    
    # 3. Получить метаданные из Pixora
    photo_ids = [m['photo_id'] for m in results['matches']]
    photos = Photo.filter(id__in=photo_ids)
    
    # 4. Создать карту photo_id -> photo
    photo_map = {p.id: p for p in photos}
    
    # 5. Обогатить результаты
    enriched_matches = []
    for match in results['matches']:
        photo = photo_map.get(match['photo_id'])
        if photo:
            enriched_matches.append({
                "photo_id": match['photo_id'],
                "similarity": match['similarity'],
                "confidence": match['confidence'],
                "url": generate_photo_url(photo.s3_key),
                "thumbnail_url": generate_thumbnail_url(photo.s3_key),
                "filename": photo.filename,
                "created_at": photo.created_at.isoformat()
            })
    
    return {
        "matches": enriched_matches,
        "total_matches": len(enriched_matches),
        "query_time_ms": results['query_time_ms']
    }
```

### Пример 3: Background индексация

```python
from celery import shared_task

@shared_task
def index_session_async(session_id: str):
    """Background task для индексации сессии."""
    facepass = FacePassClient(FACEPASS_API_URL, FACEPASS_API_KEY)
    
    # Получить фото из Pixora DB
    photos = Photo.filter(session_id=session_id)
    
    # Индексировать batch
    result = facepass.index_batch(
        session_id=session_id,
        photos=[
            {"photo_id": p.id, "s3_key": p.s3_key}
            for p in photos
        ]
    )
    
    # Обновить статус сессии
    session = PhotoSession.get(id=session_id)
    session.indexed_count = result['indexed']
    session.failed_count = result['failed']
    session.status = "ready" if result['failed'] == 0 else "partial"
    session.save()
    
    return result

# Использование
def create_session_with_background_indexing(photos):
    session = create_photo_session(photos)
    
    # Запустить индексацию в фоне
    index_session_async.delay(session.id)
    
    return session
```

## Error Handling

### Обработка ошибок индексации

```python
def safe_index_batch(session_id: str, photos: List[Dict]):
    facepass = FacePassClient(FACEPASS_API_URL, FACEPASS_API_KEY)
    
    try:
        result = facepass.index_batch(session_id, photos)
        
        if result['failed'] > 0:
            # Логировать ошибки
            logger.warning(
                f"Partial indexing failure for session {session_id}",
                extra={
                    "indexed": result['indexed'],
                    "failed": result['failed'],
                    "errors": result['errors']
                }
            )
        
        return result
        
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            logger.error("Invalid FacePass API key")
            raise Exception("Authentication failed")
        elif e.response.status_code == 429:
            logger.warning("Rate limit exceeded, retrying...")
            time.sleep(60)
            return safe_index_batch(session_id, photos)
        else:
            logger.error(f"FacePass API error: {e}")
            raise
    
    except requests.RequestException as e:
        logger.error(f"Network error calling FacePass: {e}")
        raise
```

## Performance Considerations

### Batch Size

Рекомендуемый размер batch для индексации: **100-300 фото**

```python
def index_large_session(session_id: str, photos: List[Dict]):
    """Индексация большой сессии с batching."""
    BATCH_SIZE = 200
    facepass = FacePassClient(FACEPASS_API_URL, FACEPASS_API_KEY)
    
    total_indexed = 0
    total_failed = 0
    
    for i in range(0, len(photos), BATCH_SIZE):
        batch = photos[i:i + BATCH_SIZE]
        result = facepass.index_batch(session_id, batch)
        
        total_indexed += result['indexed']
        total_failed += result['failed']
        
        logger.info(
            f"Batch {i//BATCH_SIZE + 1}: "
            f"indexed {result['indexed']}, "
            f"failed {result['failed']}"
        )
    
    return {
        "indexed": total_indexed,
        "failed": total_failed,
        "total": len(photos)
    }
```

### Caching

Кэшируйте результаты поиска для одинаковых селфи:

```python
from functools import lru_cache
import hashlib

def get_selfie_hash(selfie_data: bytes) -> str:
    return hashlib.sha256(selfie_data).hexdigest()

@lru_cache(maxsize=1000)
def cached_search(session_id: str, selfie_hash: str, threshold: float):
    # Реальный поиск выполняется только при cache miss
    pass
```

## Monitoring

### Метрики для отслеживания

1. **Indexing Success Rate**
```python
indexed_photos_total = result['indexed']
failed_photos_total = result['failed']
success_rate = indexed_photos_total / (indexed_photos_total + failed_photos_total)
```

2. **Search Performance**
```python
search_latency_ms = results['query_time_ms']
matches_found = len(results['matches'])
```

3. **API Errors**
```python
# Логировать все 4xx и 5xx ошибки
if response.status_code >= 400:
    logger.error(
        "FacePass API error",
        extra={
            "status_code": response.status_code,
            "endpoint": endpoint,
            "session_id": session_id
        }
    )
```

## Rollback Plan

Если возникли проблемы с v2.0:

1. **Откатить FacePass к v1.x**
```bash
docker-compose down
git checkout v1.x
docker-compose up -d
```

2. **Откатить изменения в Pixora**
```bash
git revert <migration-commit>
```

3. **Восстановить БД** (если выполнялась миграция)
```bash
docker-compose exec db_vector psql -U user -d db -f /code/scripts/rollback_v2.sql
```

## FAQ

### Q: Нужно ли переиндексировать существующие сессии?

**A:** Нет, если вы выполнили database migration. Существующие embeddings сохранятся. Но новые сессии должны индексироваться через новый API.

### Q: Что делать с сессиями, которые были частично проиндексированы?

**A:** Используйте `GET /api/v2/search/status/{session_id}` для проверки статуса и переиндексируйте при необходимости.

### Q: Как обрабатывать rate limiting?

**A:** Реализуйте exponential backoff и retry logic:

```python
import time

def call_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### Q: Можно ли использовать старый endpoint для поиска?

**A:** Да, legacy endpoint `/api/v2/faces/search-session` сохранен для обратной совместимости, но без auto-indexing. Рекомендуется мигрировать на новый API.

## Support

При возникновении вопросов:
1. Проверьте логи FacePass: `docker-compose logs -f app`
2. Проверьте health: `curl http://facepass:8000/api/v2/health`
3. Проверьте metrics: `curl http://facepass:8000/api/v2/metrics`

---

**Version**: 2.0.0  
**Last Updated**: 2024-02-26
