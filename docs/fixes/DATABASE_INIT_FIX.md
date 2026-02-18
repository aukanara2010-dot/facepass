# 🔧 Исправление ошибки "type vector does not exist"

## 🐛 Проблема

При выполнении `scripts/init_db.py` возникала ошибка:
```
type "vector" does not exist
```

Хотя расширение `pgvector` было установлено в базе `facepass_vector`.

### Причина:
SQLAlchemy пытался создать **все таблицы** на **обоих engines** (main и vector), включая таблицу `face_embeddings` с типом `vector` в main database, где этот тип не существует.

---

## ✅ Решение

Разделить создание таблиц:
1. **Event и Face** → создаются в `main_engine` (база `fecapass_main`)
2. **FaceEmbedding** → создается в `vector_engine` (база `facepass_vector`)

---

## 📝 Исправленный скрипт

### Ключевые изменения:

#### 1. Раздельное создание таблиц
```python
def create_main_tables():
    """Create Event and Face tables in main database"""
    main_metadata = MetaData()
    Event.__table__.to_metadata(main_metadata)
    Face.__table__.to_metadata(main_metadata)
    main_metadata.create_all(bind=main_engine)

def create_vector_tables():
    """Create FaceEmbedding table in vector database"""
    vector_metadata = MetaData()
    FaceEmbedding.__table__.to_metadata(vector_metadata)
    vector_metadata.create_all(bind=vector_engine)
```

#### 2. Установка search_path
```python
def create_vector_tables():
    with vector_engine.connect() as conn:
        conn.execute(text("SET search_path TO public"))
        conn.commit()
    # ... create tables
```

#### 3. Проверка конфигурации
```python
def verify_configuration():
    logger.info(f"Main DB URL: {settings.main_database_url}")
    logger.info(f"Vector DB URL: {settings.vector_database_url}")
```

---

## 🗄️ Структура баз данных

### Main Database (fecapass_main)
```
db_main (postgres:16)
└── fecapass_main
    ├── events
    └── faces
```

### Vector Database (facepass_vector)
```
db_vector (ankane/pgvector:latest)
└── facepass_vector
    ├── [pgvector extension]
    └── face_embeddings (with vector type)
```

---

## 🚀 Как использовать

### 1. Проверить переменные окружения

Убедитесь, что в `.env` файле правильно указаны базы данных:

```bash
# Main Database
POSTGRES_USER=fecapass_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=fecapass_main
MAIN_DB_HOST=db_main
MAIN_DB_PORT=5432

# Vector Database
VECTOR_DB_HOST=db_vector
VECTOR_DB_PORT=5432
VECTOR_POSTGRES_DB=facepass_vector
```

### 2. Запустить инициализацию

```bash
docker-compose exec app python scripts/init_db.py
```

### Ожидаемый вывод:

```
============================================================
FacePass Database Initialization
============================================================
Database configuration:
  Main DB URL: postgresql://fecapass_user:***@db_main:5432/fecapass_main
  Vector DB URL: postgresql://fecapass_user:***@db_vector:5432/facepass_vector

Step 1: Initialize pgvector extension...
✓ pgvector extension initialized successfully

Step 2: Create main database tables...
✓ Main database tables created successfully (events, faces)

Step 3: Create vector database tables...
✓ Vector database tables created successfully (face_embeddings)

============================================================
✓ Database initialization completed successfully!
============================================================
```

---

## 🔍 Проверка результата

### 1. Проверить таблицы в main database

```bash
docker-compose exec db_main psql -U fecapass_user -d fecapass_main -c "\dt"
```

**Ожидаемый результат:**
```
         List of relations
 Schema |  Name  | Type  |     Owner
--------+--------+-------+---------------
 public | events | table | fecapass_user
 public | faces  | table | fecapass_user
```

### 2. Проверить таблицы в vector database

```bash
docker-compose exec db_vector psql -U fecapass_user -d facepass_vector -c "\dt"
```

**Ожидаемый результат:**
```
              List of relations
 Schema |      Name       | Type  |     Owner
--------+-----------------+-------+---------------
 public | face_embeddings | table | fecapass_user
```

### 3. Проверить расширение pgvector

```bash
docker-compose exec db_vector psql -U fecapass_user -d facepass_vector -c "\dx"
```

**Ожидаемый результат:**
```
                          List of installed extensions
  Name   | Version |   Schema   |                Description
---------+---------+------------+--------------------------------------------
 plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
 vector  | 0.5.1   | public     | vector data type and ivfflat access method
```

### 4. Проверить структуру face_embeddings

```bash
docker-compose exec db_vector psql -U fecapass_user -d facepass_vector -c "\d face_embeddings"
```

**Ожидаемый результат:**
```
                Table "public.face_embeddings"
   Column   |           Type            | Nullable | Default
------------+---------------------------+----------+---------
 id         | integer                   | not null | nextval(...)
 face_id    | integer                   | not null |
 event_id   | integer                   | not null |
 embedding  | vector(512)               | not null |
 created_at | timestamp with time zone  |          | now()
```

Обратите внимание на тип `vector(512)` - это подтверждает, что pgvector работает!

---

## ⚠️ Troubleshooting

### Ошибка: "extension vector does not exist"

**Решение:**
```bash
# Вручную установить расширение
docker-compose exec db_vector psql -U fecapass_user -d facepass_vector -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Ошибка: "relation already exists"

**Решение:** Удалить существующие таблицы
```bash
# Main database
docker-compose exec db_main psql -U fecapass_user -d fecapass_main -c "DROP TABLE IF EXISTS faces CASCADE;"
docker-compose exec db_main psql -U fecapass_user -d fecapass_main -c "DROP TABLE IF EXISTS events CASCADE;"

# Vector database
docker-compose exec db_vector psql -U fecapass_user -d facepass_vector -c "DROP TABLE IF EXISTS face_embeddings CASCADE;"

# Запустить init_db.py снова
docker-compose exec app python scripts/init_db.py
```

### Ошибка: "could not connect to server"

**Решение:** Убедиться, что контейнеры запущены
```bash
docker-compose ps
docker-compose up -d db_main db_vector
sleep 5
docker-compose exec app python scripts/init_db.py
```

---

## 📊 Сравнение: До и После

### ❌ До (неправильно):
```python
def create_tables():
    # Пытается создать ВСЕ таблицы в ОБЕИХ базах
    Base.metadata.create_all(bind=main_engine)  # ❌ Пытается создать face_embeddings с vector
    Base.metadata.create_all(bind=vector_engine)  # ❌ Создает лишние таблицы
```

### ✅ После (правильно):
```python
def create_main_tables():
    # Создает ТОЛЬКО Event и Face в main database
    main_metadata = MetaData()
    Event.__table__.to_metadata(main_metadata)
    Face.__table__.to_metadata(main_metadata)
    main_metadata.create_all(bind=main_engine)  # ✅

def create_vector_tables():
    # Создает ТОЛЬКО FaceEmbedding в vector database
    vector_metadata = MetaData()
    FaceEmbedding.__table__.to_metadata(vector_metadata)
    vector_metadata.create_all(bind=vector_engine)  # ✅
```

---

## 🎯 Ключевые моменты

1. ✅ **Event и Face** - в main database (без vector типа)
2. ✅ **FaceEmbedding** - в vector database (с vector типом)
3. ✅ **search_path** установлен в public
4. ✅ **pgvector extension** инициализируется перед созданием таблиц
5. ✅ **Раздельные MetaData** для каждой базы

---

## 📚 Дополнительная информация

### Почему раздельные базы данных?

1. **Масштабируемость** - векторная БД может быть на отдельном сервере
2. **Производительность** - pgvector оптимизирован для векторного поиска
3. **Изоляция** - проблемы с векторной БД не влияют на основную
4. **Backup** - можно делать backup раздельно

### Альтернативный подход (одна БД)

Если хотите использовать одну базу данных:

```bash
# В .env
POSTGRES_DB=fecapass_main
VECTOR_POSTGRES_DB=fecapass_main  # Та же база
```

Но это **не рекомендуется** для production!

---

**Проблема решена! Таблицы создаются в правильных базах данных!** ✅
