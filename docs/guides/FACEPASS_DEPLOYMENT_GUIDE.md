# 🚀 FacePass - Руководство по развертыванию

## 📋 Обзор системы

FacePass - это интерактивная система поиска фотографий по лицу, интегрированная с базой данных Pixora. Система состоит из:

- **Backend API** (FastAPI + Python)
- **Интерактивный веб-интерфейс** (HTML + JavaScript + Tailwind CSS)
- **Интеграция с Pixora DB** (PostgreSQL)
- **Векторный поиск** (pgvector)
- **Распознавание лиц** (InsightFace)

## 🛠️ Предварительные требования

### Системные требования
- Python 3.8+
- PostgreSQL 12+ с расширением pgvector
- Redis (для Celery)
- Доступ к S3-совместимому хранилищу

### Зависимости Python
```bash
pip install -r requirements.txt
```

## ⚙️ Конфигурация

### 1. Переменные окружения (.env)

```env
# Основные настройки приложения
APP_NAME=Facepass
APP_VERSION=1.0.0
DEBUG=False

# Основная база данных (локальная)
POSTGRES_USER=facepass_admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=fecapass_main
MAIN_DB_HOST=localhost
MAIN_DB_PORT=5432

# Векторная база данных (локальная)
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=5432
VECTOR_POSTGRES_DB=facepass_vector

# Внешняя база данных Pixora
MAIN_APP_DATABASE_URL=postgresql://postgres:Gqmkcp2HUcgbeWlScZN1GUvkpxdqsTFX@155.212.216.176:5432/postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# S3 Storage (Beget)
S3_ENDPOINT=https://s3.beget.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=your_bucket
S3_REGION=ru-1

# Face Recognition
FACE_DETECTION_THRESHOLD=0.6
FACE_SIMILARITY_THRESHOLD=0.7
EMBEDDING_DIMENSION=512
```

### 2. Структура проекта

```
facepass/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── sessions.py      # Эндпоинты сессий
│   │   ├── faces.py         # Поиск лиц
│   │   └── ...
│   ├── static/
│   │   ├── session/
│   │   │   └── index.html   # Основной интерфейс
│   │   └── js/
│   │       └── face-search.js # JavaScript логика
│   └── main.py              # FastAPI приложение
├── core/
│   ├── config.py            # Конфигурация
│   ├── database.py          # Подключения к БД
│   └── s3.py               # S3 интеграция
├── models/
│   ├── photo_session.py     # Модель сессий Pixora
│   └── ...
├── services/
│   └── face_recognition.py  # InsightFace сервис
└── requirements.txt
```

## 🚀 Запуск системы

### 1. Подготовка окружения

```bash
# Клонирование и переход в директорию
cd facepass

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка базы данных

```bash
# Создание локальных баз данных
createdb fecapass_main
createdb facepass_vector

# Установка расширения pgvector
psql -d facepass_vector -c "CREATE EXTENSION vector;"

# Инициализация схемы
python scripts/init_db.py
```

### 3. Запуск сервисов

```bash
# Запуск Redis (в отдельном терминале)
redis-server

# Запуск Celery worker (в отдельном терминале)
celery -A workers.celery_app worker --loglevel=info

# Запуск FastAPI сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Проверка работоспособности

```bash
# Тест подключения к Pixora DB
python test_db_connection.py

# Тест API эндпоинтов
python test_session_endpoints_simple.py

# Тест интерфейса
python test_facepass_interface.py
```

## 🌐 Доступ к интерфейсу

### URL для доступа
```
http://localhost:8000/api/v1/sessions/{session_id}/interface
```

### Пример с реальной сессией
```
http://localhost:8000/api/v1/sessions/1788875f-fc71-49d6-a9fa-a060e3ee6fee/interface
```

## 🔧 API Эндпоинты

### Валидация сессий
```http
GET /api/v1/sessions/validate/{session_id}
GET /api/v1/sessions/{session_id}
GET /api/v1/sessions/{session_id}/facepass-status
GET /api/v1/sessions/{session_id}/interface
```

### Поиск лиц
```http
POST /api/v1/faces/search-session
Content-Type: multipart/form-data

session_id: UUID сессии
file: Файл изображения
threshold: Порог схожести (0.0-1.0)
limit: Максимум результатов
```

### Статические файлы
```http
GET /static/js/face-search.js
GET /static/session/index.html
```

## 🐳 Docker развертывание

### 1. Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. docker-compose.yml
```yaml
version: '3.8'
services:
  facepass:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/facepass
    depends_on:
      - db
      - redis
  
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: facepass
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:alpine
    
volumes:
  postgres_data:
```

### 3. Запуск с Docker
```bash
docker-compose up -d
```

## 🔒 Безопасность

### 1. Настройки CORS
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://facepass.pixorasoft.ru",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### 2. Валидация файлов
- Проверка типов файлов (только изображения)
- Ограничение размера файлов
- Валидация UUID сессий

### 3. Ограничения доступа
- Только чтение из внешней БД Pixora
- Валидация FacePass статуса
- Rate limiting для API

## 📊 Мониторинг

### 1. Логирование
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. Метрики производительности
- Время поиска лиц
- Количество успешных поисков
- Использование памяти и CPU
- Статистика по сессиям

### 3. Health checks
```http
GET /api/v1/health
```

## 🚨 Устранение неполадок

### Частые проблемы

#### 1. Ошибка подключения к Pixora DB
```bash
# Проверка доступности
ping 155.212.216.176
telnet 155.212.216.176 5432

# Проверка учетных данных
python test_db_connection.py
```

#### 2. Ошибки InsightFace
```bash
# Установка дополнительных зависимостей
pip install onnxruntime-gpu  # Для GPU
pip install opencv-python-headless

# Проверка моделей
python -c "import insightface; print('OK')"
```

#### 3. Проблемы с камерой в браузере
- Убедитесь, что сайт использует HTTPS (для продакшена)
- Проверьте разрешения браузера на доступ к камере
- Тестируйте в разных браузерах

#### 4. Статические файлы не загружаются
```python
# Проверка конфигурации в app/main.py
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

### Логи для диагностики
```bash
# Логи FastAPI
tail -f /var/log/facepass/app.log

# Логи Celery
tail -f /var/log/facepass/celery.log

# Логи PostgreSQL
tail -f /var/log/postgresql/postgresql.log
```

## 📈 Оптимизация производительности

### 1. База данных
```sql
-- Индексы для быстрого поиска
CREATE INDEX idx_face_embeddings_session ON face_embeddings(session_id);
CREATE INDEX idx_photos_session ON photos(photo_session_id);
```

### 2. Кеширование
```python
# Redis кеш для сессий
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
```

### 3. Оптимизация изображений
- Сжатие JPEG до 95% качества
- Ресайз больших изображений
- Lazy loading в интерфейсе

## 🔄 Обновления и миграции

### 1. Обновление кода
```bash
git pull origin main
pip install -r requirements.txt
systemctl restart facepass
```

### 2. Миграции базы данных
```bash
# Создание миграции
alembic revision --autogenerate -m "Add new field"

# Применение миграций
alembic upgrade head
```

### 3. Обновление моделей InsightFace
```bash
# Скачивание новых моделей
python scripts/update_models.py
```

## 📞 Поддержка

### Контакты
- **Техническая поддержка**: support@pixorasoft.ru
- **Документация**: https://docs.pixorasoft.ru/facepass
- **GitHub Issues**: https://github.com/pixora/facepass/issues

### Полезные ссылки
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [InsightFace Documentation](https://insightface.ai/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Tailwind CSS Documentation](https://tailwindcss.com/)

---

## ✅ Чек-лист развертывания

- [ ] Установлены все зависимости
- [ ] Настроены переменные окружения
- [ ] Созданы и настроены базы данных
- [ ] Запущены все сервисы (FastAPI, Redis, Celery)
- [ ] Проверено подключение к Pixora DB
- [ ] Протестированы API эндпоинты
- [ ] Проверен веб-интерфейс
- [ ] Настроен мониторинг и логирование
- [ ] Проведено нагрузочное тестирование
- [ ] Настроены резервные копии

🎉 **Система готова к использованию!**