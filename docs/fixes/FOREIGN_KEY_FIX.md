# 🔧 Исправление ошибки sqlalchemy.exc.NoReferencedTableError

## 🐛 Проблема

SQLAlchemy не может разрешить Foreign Key между `faces.user_id` и `users.id`, потому что:
1. Модели `Face` и `User` используют один `Base`
2. Но они могут быть в **разных физических базах данных**
3. SQLAlchemy не поддерживает Foreign Keys между разными базами данных

### Ошибка:
```
sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column 'faces.user_id' 
could not find table 'users' with which to generate a foreign key to target column 'id'
```

---

## ✅ Решение

Убрать Foreign Key и relationship из моделей. Связывать данные **вручную на уровне сервисов**.

---

## 📝 Исправленные файлы

### 1. `models/face.py` - ИСПРАВЛЕН ✅

**Было:**
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

class Face(Base):
    __tablename__ = "faces"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # ❌ ForeignKey
    # ...
    
    user = relationship("User", backref="faces")  # ❌ Relationship
```

**Стало:**
```python
from sqlalchemy import Column, Integer, String, DateTime, Float
# Убрали: ForeignKey, relationship

class Face(Base):
    """
    Face model for main database
    
    Note: user_id is a simple integer reference to User.id.
    We don't use ForeignKey because Face and User might be in different databases
    in some deployment scenarios. The relationship is maintained at the application level.
    """
    __tablename__ = "faces"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # ✅ Просто Integer
    # ...
    
    # No relationship - we handle joins manually at the service layer
```

### 2. `models/user.py` - ПРОВЕРЕН ✅

Модель User уже не имела ссылок на Face. Все в порядке.

### 3. `app/api/v1/endpoints/users.py` - ПРОВЕРЕН ✅

Импортирует только `User`, без `Face`. Все в порядке.

### 4. `app/api/v1/endpoints/faces.py` - ПРОВЕРЕН ✅

Не использует `.user` или `.faces` relationships. Все в порядке.

---

## 🔗 Как связывать данные вручную

### Вариант 1: В endpoint (простой случай)

```python
@router.get("/faces/{face_id}/with-user")
async def get_face_with_user(face_id: int, db: Session = Depends(get_db)):
    """Get face with user information"""
    
    # Получить Face
    face = db.query(Face).filter(Face.id == face_id).first()
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")
    
    # Получить User вручную по user_id
    user = db.query(User).filter(User.id == face.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "face": {
            "id": face.id,
            "image_url": face.image_url,
            "confidence": face.confidence
        },
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }
```

### Вариант 2: В сервисном слое (рекомендуется)

Создайте файл `services/face_service.py`:

```python
from sqlalchemy.orm import Session
from models.face import Face
from models.user import User
from typing import Optional, Dict, Any


class FaceService:
    """Service for Face-related operations with manual joins"""
    
    @staticmethod
    def get_face_with_user(db: Session, face_id: int) -> Optional[Dict[str, Any]]:
        """
        Get face with user information
        
        Args:
            db: Database session
            face_id: Face ID
            
        Returns:
            Dictionary with face and user data, or None if not found
        """
        face = db.query(Face).filter(Face.id == face_id).first()
        if not face:
            return None
        
        user = db.query(User).filter(User.id == face.user_id).first()
        
        return {
            "face": {
                "id": face.id,
                "user_id": face.user_id,
                "image_url": face.image_url,
                "s3_key": face.s3_key,
                "confidence": face.confidence,
                "created_at": face.created_at
            },
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active
            } if user else None
        }
    
    @staticmethod
    def get_user_faces(db: Session, user_id: int) -> list:
        """
        Get all faces for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of Face objects
        """
        return db.query(Face).filter(Face.user_id == user_id).all()
```

Использование в endpoint:

```python
from services.face_service import FaceService

@router.get("/faces/{face_id}/with-user")
async def get_face_with_user(face_id: int, db: Session = Depends(get_db)):
    """Get face with user information"""
    result = FaceService.get_face_with_user(db, face_id)
    if not result:
        raise HTTPException(status_code=404, detail="Face not found")
    return result
```

### Вариант 3: SQL JOIN (для производительности)

Если нужна высокая производительность, используйте SQL JOIN:

```python
from sqlalchemy import select

@router.get("/faces-with-users")
async def get_faces_with_users(db: Session = Depends(get_db)):
    """Get all faces with user information using JOIN"""
    
    # Ручной JOIN через SQL
    query = db.query(Face, User).join(
        User, Face.user_id == User.id
    ).all()
    
    results = []
    for face, user in query:
        results.append({
            "face": {
                "id": face.id,
                "image_url": face.image_url,
                "confidence": face.confidence
            },
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name
            }
        })
    
    return results
```

---

## 🧪 Тестирование

### 1. Пересоздать таблицы

```bash
# Удалить старые таблицы (если есть)
docker-compose exec db_main psql -U $POSTGRES_USER -d $POSTGRES_DB -c "DROP TABLE IF EXISTS faces CASCADE;"
docker-compose exec db_main psql -U $POSTGRES_USER -d $POSTGRES_DB -c "DROP TABLE IF EXISTS users CASCADE;"

# Пересоздать таблицы
docker-compose exec app python scripts/init_db.py
```

### 2. Проверить структуру таблиц

```bash
# Проверить таблицу users
docker-compose exec db_main psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\d users"

# Проверить таблицу faces
docker-compose exec db_main psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\d faces"

# Убедиться, что нет Foreign Key
docker-compose exec db_main psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_name = 'faces';
"
# Должно вернуть пустой результат
```

### 3. Тестовые запросы

```bash
# 1. Создать пользователя
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "full_name": "Test User"}'

# 2. Загрузить лицо
curl -X POST "http://localhost:8000/api/v1/faces/upload" \
  -F "user_id=1" \
  -F "file=@face.jpg"

# 3. Получить лица пользователя
curl "http://localhost:8000/api/v1/faces/user/1"
```

---

## 📊 Сводка изменений

| Файл | Изменение | Статус |
|------|-----------|--------|
| `models/face.py` | Убран `ForeignKey` и `relationship` | ✅ ИСПРАВЛЕН |
| `models/user.py` | Проверен (нет ссылок на Face) | ✅ ПРОВЕРЕН |
| `app/api/v1/endpoints/users.py` | Проверен (импортирует только User) | ✅ ПРОВЕРЕН |
| `app/api/v1/endpoints/faces.py` | Проверен (не использует relationships) | ✅ ПРОВЕРЕН |

---

## ✨ Преимущества нового подхода

1. ✅ **Работает с разными БД**: Face и User могут быть в разных базах
2. ✅ **Гибкость**: Можно легко изменить схему связей
3. ✅ **Явность**: Связи видны в коде, а не скрыты в ORM
4. ✅ **Производительность**: Можно оптимизировать JOIN запросы вручную
5. ✅ **Простота**: Нет магии SQLAlchemy relationships

## ⚠️ Важно помнить

1. **Целостность данных**: Проверяйте существование user_id вручную в коде
2. **Каскадное удаление**: Реализуйте вручную, если нужно
3. **Индексы**: Убедитесь, что user_id имеет индекс для быстрых JOIN

---

## 🎯 Результат

**Ошибка `sqlalchemy.exc.NoReferencedTableError` полностью устранена!**

Теперь:
- ✅ Таблицы создаются без ошибок
- ✅ Face.user_id - это простой Integer с индексом
- ✅ Связи управляются вручную на уровне сервисов
- ✅ Система готова к работе с разными базами данных
