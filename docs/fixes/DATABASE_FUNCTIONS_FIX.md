# Исправление функций базы данных

## Проблема
В проекте есть два места с функциями для получения сессий БД:

1. **`core/database.py`** - содержит:
   - `get_main_db()` - для основной БД
   - `get_vector_db()` - для векторной БД  
   - `get_pixora_db()` - для внешней БД Pixora

2. **`app/api/deps.py`** - содержит:
   - `get_db()` - для основной БД
   - `get_vector_db_session()` - для векторной БД

## Решение
Используем функции из `app/api/deps.py` для совместимости с существующими эндпоинтами:

### Правильные импорты:
```python
from app.api.deps import get_db, get_vector_db_session
from core.database import get_pixora_db  # Только для Pixora БД
```

### Правильное использование в эндпоинтах:
```python
async def some_endpoint(
    db: Session = Depends(get_db),                    # Основная БД
    vector_db: Session = Depends(get_vector_db_session),  # Векторная БД
    pixora_db: Session = Depends(get_pixora_db)       # Pixora БД
):
```

## Исправленные файлы

### ✅ `app/api/v1/endpoints/faces.py`
- Импорт: `from app.api.deps import get_db, get_vector_db_session`
- Все эндпоинты используют правильные функции

### ✅ `test_auto_indexing_flow.py`  
- Импорт: `from app.api.deps import get_db, get_vector_db_session`
- Импорт: `from core.database import get_pixora_db`
- Все тесты используют правильные функции

### ✅ `services/photo_indexing.py`
- Сервис работает с переданными сессиями БД
- Не требует изменений импортов

## Статус
Все функции БД исправлены и используют правильные имена из существующей архитектуры проекта.