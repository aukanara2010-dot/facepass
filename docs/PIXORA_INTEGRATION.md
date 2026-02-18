# Интеграция с внешней базой данных Pixora

## Обзор

Данная интеграция позволяет FacePass приложению проверять существование фотосессий и статус FacePass в основной базе данных Pixora, расположенной на удаленном сервере.

## Архитектура

### Конфигурация базы данных

Приложение использует три отдельных подключения к базам данных:

1. **Основная база (main_database_url)** - локальная база для основных операций
2. **Векторная база (vector_database_url)** - локальная база для хранения векторов лиц
3. **База Pixora (MAIN_APP_DATABASE_URL)** - внешняя база для валидации сессий

### Переменные окружения

```env
# Внешняя база данных Pixora (только для чтения)
MAIN_APP_DATABASE_URL=postgresql://postgres:Gqmkcp2HUcgbeWlScZN1GUvkpxdqsTFX@155.212.216.176:5432/postgres
```

## Компоненты интеграции

### 1. Модель PhotoSession

**Файл:** `models/photo_session.py`

Модель для работы с таблицей `photo_sessions` из внешней базы Pixora:

```python
class PhotoSession(PixoraBase):
    __tablename__ = "photo_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    studio_id = Column(Integer, nullable=False)
    facepass_enabled = Column(Boolean, default=False, nullable=False)
```

### 2. Схемы данных

**Файл:** `app/schemas/photo_session.py`

Pydantic схемы для валидации API запросов и ответов:

- `PhotoSessionResponse` - данные сессии
- `SessionValidationResponse` - результат валидации сессии

### 3. API эндпоинты

**Файл:** `app/api/v1/endpoints/sessions.py`

#### Основные эндпоинты:

- `GET /api/v1/sessions/validate/{session_id}` - валидация сессии
- `GET /api/v1/sessions/{session_id}` - получение данных сессии
- `GET /api/v1/sessions/{session_id}/facepass-status` - статус FacePass
- `GET /api/v1/sessions/{session_id}/interface` - HTML интерфейс

### 4. HTML интерфейс

**Файл:** `app/static/session/index.html`

Веб-интерфейс для работы с FacePass:
- Валидация сессии при загрузке
- Активация камеры
- Сканирование лиц
- Отображение результатов поиска

## Логика работы

### 1. Валидация сессии

```python
# Проверка существования сессии
session = pixora_db.query(PhotoSession).filter(
    PhotoSession.id == session_id
).first()

# Проверка статуса FacePass
if not session or not session.is_facepass_active():
    return error_response
```

### 2. Безопасность

- **Только чтение**: Подключение к базе Pixora используется только для SELECT запросов
- **Изоляция**: Все операции записи выполняются в локальную базу данных
- **Валидация**: Проверка прав доступа на уровне сессии

### 3. Обработка ошибок

- Сессия не найдена → 404 ошибка
- FacePass не активен → 403 ошибка  
- Ошибка подключения → 500 ошибка

## Использование

### 1. Доступ к интерфейсу

```
GET /api/v1/sessions/{session_id}/interface
```

### 2. Программная валидация

```python
from core.database import get_pixora_db
from models.photo_session import PhotoSession

def validate_session(session_id: int, db: Session):
    session = db.query(PhotoSession).filter_by(id=session_id).first()
    return session and session.is_facepass_active()
```

### 3. API запросы

```javascript
// Валидация сессии
const response = await fetch(`/api/v1/sessions/validate/${sessionId}`);
const data = await response.json();

if (data.valid) {
    // Сессия валидна, показать интерфейс
} else {
    // Показать ошибку: data.error
}
```

## Тестирование

Для тестирования интеграции используйте:

```bash
python test_pixora_integration.py
```

Тест проверяет:
- Подключение к внешней базе
- Существование таблицы photo_sessions
- Работу модели PhotoSession
- Функциональность API эндпоинтов

## Мониторинг

### Логи подключения

Все операции с внешней базой логируются в стандартный вывод приложения.

### Метрики производительности

- Время ответа валидации сессии
- Количество успешных/неуспешных подключений
- Статистика использования FacePass по сессиям

## Устранение неполадок

### Проблемы подключения

1. Проверьте доступность сервера: `ping 155.212.216.176`
2. Проверьте порт: `telnet 155.212.216.176 5432`
3. Проверьте учетные данные в `.env`

### Ошибки валидации

1. Убедитесь, что таблица `photo_sessions` существует
2. Проверьте структуру таблицы (поля: id, name, studio_id, facepass_enabled)
3. Проверьте права доступа пользователя базы данных

### Проблемы производительности

1. Используйте пул соединений (уже настроен)
2. Мониторьте время ответа внешней базы
3. Рассмотрите кеширование для часто запрашиваемых сессий

## Безопасность

### Рекомендации

1. **Только чтение**: Никогда не выполняйте INSERT/UPDATE/DELETE в базе Pixora
2. **Изоляция сетей**: Используйте VPN или приватные сети для подключения
3. **Мониторинг**: Отслеживайте все запросы к внешней базе
4. **Резервное подключение**: Рассмотрите возможность резервного подключения

### Ограничения доступа

- Подключение только с разрешенных IP адресов
- Использование SSL/TLS для шифрования трафика
- Регулярная ротация паролей доступа

## Развитие

### Планируемые улучшения

1. **Кеширование**: Redis кеш для валидации сессий
2. **Мониторинг**: Интеграция с системами мониторинга
3. **Резервирование**: Множественные подключения для отказоустойчивости
4. **Синхронизация**: Периодическая синхронизация данных сессий