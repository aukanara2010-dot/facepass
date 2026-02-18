# 🎭 InsightFace Integration Guide

## Обзор

InsightFace интегрирован в FacePass для распознавания лиц и извлечения эмбеддингов. Используется модель `buffalo_l` для высокой точности.

---

## 📦 Установленные зависимости

### requirements.txt
```
insightface==0.7.3
onnxruntime==1.16.3
opencv-python-headless==4.9.0.80
```

### Dockerfile
Системные зависимости для InsightFace:
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1
```

---

## 🔧 Архитектура

### 1. Face Recognition Service (`services/face_recognition.py`)

**Singleton сервис** для работы с InsightFace:

```python
from services.face_recognition import get_face_recognition_service

face_service = get_face_recognition_service()
```

#### Методы:

**`get_embeddings(image_data: bytes) -> List[Tuple[np.ndarray, float]]`**
- Находит ВСЕ лица на фото
- Возвращает список (embedding, confidence) для каждого лица
- Возвращает пустой список, если лиц нет

**`extract_single_embedding(image_data: bytes) -> Tuple[Optional[np.ndarray], float]`**
- Извлекает embedding для ОДНОГО лица
- Возвращает (None, 0.0) если лиц нет
- Предупреждает, если найдено несколько лиц

**`compare_embeddings(emb1, emb2) -> float`**
- Сравнивает два эмбеддинга
- Возвращает similarity score (0.0 - 1.0)

---

## 🔄 Celery Tasks

### Task 1: `process_face_embedding`

**Назначение:** Обработка загруженного фото фотографом

**Workflow:**
1. Скачивает фото из S3
2. Извлекает embedding с помощью InsightFace
3. Сохраняет embedding в vector database
4. Обновляет Face.confidence

**Обработка ошибок:**
- Если лиц не найдено → `confidence=0.0`, статус `no_face_detected`
- Если несколько лиц → использует первое, логирует предупреждение
- При ошибке → retry (max 3 раза)

**Пример результата:**
```python
{
    "face_id": 123,
    "event_id": 1,
    "confidence": 0.95,
    "status": "success",
    "faces_detected": 1
}
```

---

### Task 2: `search_similar_faces_task`

**Назначение:** Поиск фотографий участника по селфи

**Workflow:**
1. Извлекает embedding из селфи участника
2. Выполняет векторный поиск в pgvector
3. Фильтрует ТОЛЬКО по event_id (изоляция мероприятий)
4. Возвращает совпадения выше threshold

**Обработка ошибок:**
- Если лицо не найдено → возвращает пустой результат с сообщением
- Использует pgvector оператор `<->` для cosine distance

**SQL запрос:**
```sql
SELECT 
    face_id,
    event_id,
    1 - (embedding <-> '[query_embedding]') as similarity
FROM face_embeddings
WHERE event_id = :event_id
    AND (1 - (embedding <-> '[query_embedding]')) >= :threshold
ORDER BY embedding <-> '[query_embedding]'
LIMIT :limit
```

**Пример результата:**
```python
{
    "results": [
        {
            "face_id": 456,
            "event_id": 1,
            "similarity": 0.92,
            "image_url": "https://s3.../photo.jpg"
        }
    ],
    "count": 1,
    "event_id": 1,
    "status": "success",
    "query_confidence": 0.88
}
```

---

## 🚀 Использование

### 1. Загрузка фото фотографом

```bash
curl -X POST "http://localhost:8000/api/v1/faces/upload" \
  -F "event_id=1" \
  -F "file=@photo.jpg"
```

**Что происходит:**
1. API загружает фото в S3
2. Создаёт запись Face в БД
3. Запускает Celery task `process_face_embedding`
4. Task извлекает embedding и сохраняет в vector DB

---

### 2. Поиск фото участником

```bash
curl -X POST "http://localhost:8000/api/v1/faces/search" \
  -F "event_id=1" \
  -F "file=@selfie.jpg" \
  -F "threshold=0.7" \
  -F "limit=10"
```

**Что происходит:**
1. API запускает Celery task `search_similar_faces_task`
2. Task извлекает embedding из селфи
3. Ищет похожие лица в vector DB (только в event_id=1)
4. Возвращает совпадения выше 70% similarity

---

## 🎯 Модель buffalo_l

### Характеристики:
- **Размер embedding:** 512 измерений
- **Точность:** Высокая (state-of-the-art)
- **Скорость:** Средняя (оптимизирована для точности)
- **Устойчивость:** Хорошо работает с разными углами, освещением

### Инициализация:
```python
from insightface.app import FaceAnalysis

app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1, det_size=(640, 640))
```

**Параметры:**
- `name='buffalo_l'` - модель высокой точности
- `providers=['CPUExecutionProvider']` - работа на CPU
- `ctx_id=-1` - CPU режим
- `det_size=(640, 640)` - размер детекции

---

## ⚠️ Обработка ошибок

### 1. InsightFace не инициализирован
```python
if not self.initialized:
    raise RuntimeError("InsightFace is not initialized")
```

**Причины:**
- Не установлены зависимости
- Ошибка загрузки модели
- Недостаточно памяти

**Решение:**
- Проверить логи при старте воркера
- Убедиться, что все зависимости установлены
- Проверить доступную память

---

### 2. Лицо не найдено

**В process_face_embedding:**
- Устанавливает `confidence=0.0`
- Возвращает статус `no_face_detected`
- НЕ создаёт запись в vector DB

**В search_similar_faces_task:**
- Возвращает пустой список результатов
- Статус `no_face_detected`
- Сообщение для пользователя

---

### 3. Несколько лиц на фото

**В process_face_embedding:**
- Использует первое лицо
- Логирует предупреждение
- Продолжает обработку

**В search_similar_faces_task:**
- Использует первое лицо
- Логирует предупреждение
- Продолжает поиск

---

## 🔍 Логирование

### Уровни логов:

**INFO:**
- Инициализация InsightFace
- Начало обработки задач
- Количество найденных лиц
- Результаты поиска

**WARNING:**
- Несколько лиц на фото
- Лицо не найдено
- Использование первого лица из нескольких

**ERROR:**
- Ошибка инициализации InsightFace
- Ошибка обработки изображения
- Ошибка в Celery task

**DEBUG:**
- Confidence score каждого лица
- Детали векторного поиска

---

## 📊 Производительность

### CPU режим (текущий):
- **Обработка 1 фото:** ~2-5 секунд
- **Поиск по 1000 лиц:** ~100-500 мс (с pgvector)
- **Память:** ~500 MB на воркер

### GPU режим (опционально):
Для использования GPU:
1. Заменить `onnxruntime` на `onnxruntime-gpu`
2. Установить CUDA
3. Изменить provider на `CUDAExecutionProvider`

```python
app = FaceAnalysis(
    name='buffalo_l', 
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)
app.prepare(ctx_id=0, det_size=(640, 640))  # ctx_id=0 для GPU
```

**Ускорение:** 5-10x быстрее

---

## 🧪 Тестирование

### Проверка инициализации:

```python
from services.face_recognition import get_face_recognition_service

service = get_face_recognition_service()
print(f"Initialized: {service.initialized}")
```

### Тест на реальном фото:

```python
with open('test_photo.jpg', 'rb') as f:
    image_data = f.read()

embeddings = service.get_embeddings(image_data)
print(f"Found {len(embeddings)} faces")

for i, (emb, conf) in enumerate(embeddings):
    print(f"Face {i+1}: confidence={conf:.3f}, embedding_dim={len(emb)}")
```

### Тест Celery task:

```bash
# Запустить воркер
docker-compose exec worker celery -A workers.celery_app worker --loglevel=info

# В другом терминале - загрузить фото
curl -X POST "http://localhost:8000/api/v1/faces/upload" \
  -F "event_id=1" \
  -F "file=@test_photo.jpg"

# Проверить логи воркера
docker-compose logs -f worker
```

---

## 🎉 Результат

**InsightFace полностью интегрирован!**

✅ Автоматическое извлечение эмбеддингов при загрузке фото
✅ Векторный поиск с фильтрацией по мероприятиям
✅ Обработка ошибок (нет лица, несколько лиц)
✅ Логирование всех операций
✅ Готово к production использованию

---

## 📚 Дополнительные ресурсы

- [InsightFace GitHub](https://github.com/deepinsight/insightface)
- [InsightFace Documentation](https://insightface.ai/)
- [ONNX Runtime](https://onnxruntime.ai/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

---

**FacePass теперь полностью функционален для распознавания лиц!** 🚀
