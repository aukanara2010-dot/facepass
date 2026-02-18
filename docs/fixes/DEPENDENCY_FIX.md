# 🔧 Исправление ошибки AttributeError: 'generator' object has no attribute 'query'

## 🐛 Проблема

В файле `app/api/deps.py` функции `get_db()` и `get_vector_db_session()` **возвращали генераторы** вместо того, чтобы **быть генераторами**.

### Неправильный код (ДО):
```python
def get_db() -> Generator[Session, None, None]:
    """Dependency for getting main database session"""
    return get_main_db()  # ❌ Возвращает генератор, а не yield
```

Это приводило к ошибке:
```
AttributeError: 'generator' object has no attribute 'query'
```

Потому что FastAPI получал объект-генератор, а не Session.

---

## ✅ Решение

Функции должны **сами быть генераторами** (использовать `yield`), а не возвращать генераторы.

### Правильный код (ПОСЛЕ):
```python
def get_db() -> Generator[Session, None, None]:
    """Dependency for getting main database session"""
    db = MainSessionLocal()
    try:
        yield db  # ✅ Yield Session напрямую
    finally:
        db.close()
```

---

## 📝 Исправленные файлы

### 1. `app/api/deps.py` - ИСПРАВЛЕН ✅

**Было:**
```python
from core.database import get_main_db, get_vector_db

def get_db() -> Generator[Session, None, None]:
    return get_main_db()  # ❌ Неправильно

def get_vector_db_session() -> Generator[Session, None, None]:
    return get_vector_db()  # ❌ Неправильно
```

**Стало:**
```python
from core.database import MainSessionLocal, VectorSessionLocal

def get_db() -> Generator[Session, None, None]:
    db = MainSessionLocal()
    try:
        yield db  # ✅ Правильно
    finally:
        db.close()

def get_vector_db_session() -> Generator[Session, None, None]:
    db = VectorSessionLocal()
    try:
        yield db  # ✅ Правильно
    finally:
        db.close()
```

### 2. `app/api/v1/endpoints/health.py` - ОБНОВЛЕН ✅

Изменен импорт для консистентности:

**Было:**
```python
from core.database import get_main_db

@router.get("/health")
async def health_check(db: Session = Depends(get_main_db)):
```

**Стало:**
```python
from app.api.deps import get_db

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
```

### 3. Все остальные endpoints - ПРОВЕРЕНЫ ✅

Файлы уже были правильными:
- ✅ `app/api/v1/endpoints/users.py` - использует `Depends(get_db)`
- ✅ `app/api/v1/endpoints/faces.py` - использует `Depends(get_db)` и `Depends(get_vector_db_session)`

---

## 🔍 Проверка правильности

### Все endpoints должны использовать этот паттерн:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db

@router.get("/example")
async def example_endpoint(db: Session = Depends(get_db)):
    # Теперь db - это Session объект, а не generator
    users = db.query(User).all()  # ✅ Работает!
    return users
```

### Ключевые моменты:

1. ✅ **Импорт Depends**: `from fastapi import Depends`
2. ✅ **Импорт Session**: `from sqlalchemy.orm import Session`
3. ✅ **Импорт get_db**: `from app.api.deps import get_db`
4. ✅ **Использование в параметрах**: `db: Session = Depends(get_db)`
5. ✅ **get_db - это генератор**: использует `yield`, а не `return`

---

## 🧪 Тестирование

### Запустить тестовый скрипт:
```bash
docker-compose exec app python test_endpoints.py
```

Этот скрипт проверит:
- ✅ Все импорты работают
- ✅ Функции зависимостей являются генераторами
- ✅ Все endpoints имеют правильные сигнатуры

### Проверить вручную:
```bash
# 1. Перезапустить контейнеры
docker-compose restart app worker

# 2. Проверить health endpoint
curl http://localhost:8000/api/v1/health

# 3. Создать пользователя
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "full_name": "Test User"}'

# 4. Получить список пользователей
curl http://localhost:8000/api/v1/users/
```

---

## 📊 Сводка изменений

| Файл | Статус | Изменение |
|------|--------|-----------|
| `app/api/deps.py` | ✅ ИСПРАВЛЕН | Функции теперь генераторы (yield вместо return) |
| `app/api/v1/endpoints/health.py` | ✅ ОБНОВЛЕН | Использует get_db из deps |
| `app/api/v1/endpoints/users.py` | ✅ ПРОВЕРЕН | Уже был правильным |
| `app/api/v1/endpoints/faces.py` | ✅ ПРОВЕРЕН | Уже был правильным |
| `test_endpoints.py` | ✅ СОЗДАН | Скрипт для проверки |

---

## 🎯 Результат

Теперь все endpoints работают правильно:
- ✅ `db` - это `Session` объект, а не generator
- ✅ Можно использовать `db.query()`, `db.add()`, `db.commit()` и т.д.
- ✅ Сессии автоматически закрываются после каждого запроса
- ✅ Нет утечек соединений к базе данных

**Ошибка `AttributeError: 'generator' object has no attribute 'query'` полностью устранена!** ✨
