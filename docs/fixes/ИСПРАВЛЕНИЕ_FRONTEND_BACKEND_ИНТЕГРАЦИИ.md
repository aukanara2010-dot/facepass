# Исправление интеграции фронтенда и бэкенда - Отчет

## Проблема
После успешного поиска лиц (71% сходство) фронтенд делал запрос на `GET /session/undefined`, что вызывало ошибку `InvalidTextRepresentation` в базе данных.

## Причины проблемы

### 1. Неправильные поля базы данных в API
- **Проблема**: API возвращал несуществующие поля `url_preview` и `url_original`
- **Результат**: Фронтенд не мог получить правильные URL изображений

### 2. Неправильные поля в фронтенд коде
- **Проблема**: JavaScript код ожидал поля `url_preview` и `url_original`
- **Результат**: Изображения не отображались корректно

### 3. Перезапись session_id из API ответа
- **Проблема**: Фронтенд перезаписывал правильный `session_id` значением из API
- **Результат**: Если API возвращал некорректный `session_id`, он становился `undefined`

## Исправления

### 1. Исправлены поля базы данных в API
**Файл**: `app/api/v1/endpoints/faces.py`

**SQL запрос**:
```sql
-- Было:
SELECT id, file_name, url_preview, url_original, created_at

-- Стало:
SELECT id, file_name, preview_path, file_path, created_at
```

**Формирование ответа**:
```python
# Было:
"url_preview": photo_info["url_preview"],
"url_original": photo_info["url_original"]

# Стало:
"preview_path": photo_info["preview_path"],
"file_path": photo_info["file_path"]
```

### 2. Исправлены поля в фронтенд коде
**Файл**: `app/static/js/face-search.js`

**Отображение изображений**:
```javascript
// Было:
<img src="${photo.url_preview || photo.url}">

// Стало:
<img src="${photo.preview_path || photo.file_path}">
```

**Модальное окно**:
```javascript
// Было:
this.modalImage.src = photo.url_preview || photo.url;

// Стало:
this.modalImage.src = photo.preview_path || photo.file_path;
```

### 3. Исправлена обработка session_id
**Убрана перезапись session_id**:
```javascript
// Было:
if (result.session_id) {
    this.sessionId = result.session_id;
}

// Стало:
// Убрано - session_id берется только из URL
```

**Добавлена валидация session_id**:
```javascript
if (!this.sessionId || this.sessionId === 'undefined') {
    this.showToast('Ошибка: ID сессии не найден. Обновите страницу.', 'error');
    return;
}
```

### 4. Добавлено отладочное логирование
**Получение session_id из URL**:
```javascript
console.log('URL pathname:', window.location.pathname);
console.log('Final session ID:', sessionId);
```

**Покупка фотографий**:
```javascript
console.log('Current session ID for purchase:', this.sessionId);
console.log('Purchase URL:', purchaseUrl);
```

**API ответ**:
```javascript
console.log('Search API response:', {
    session_id: result.session_id,
    matches_count: result.matches ? result.matches.length : 0
});
```

## Структура исправленного API ответа

### Эндпоинт: `POST /api/v1/faces/search-session`
```json
{
    "matches": [
        {
            "id": 12345,
            "file_name": "1771443713337-photo2025...",
            "preview_path": "/path/to/preview.jpg",
            "file_path": "/path/to/original.jpg",
            "similarity": 0.71,
            "created_at": "2025-01-15T10:30:00"
        }
    ],
    "session_id": "1788875f-fc71-49d6-a9fa-a060e3ee6fee",
    "session_name": "Фотосессия в студии",
    "total_matches": 1,
    "query_time_ms": 1234.56,
    "search_threshold": 0.6,
    "indexing_status": "completed"
}
```

## Поток данных после исправления

### 1. Инициализация
```
URL: /session/1788875f-fc71-49d6-a9fa-a060e3ee6fee
↓
JavaScript: this.sessionId = "1788875f-fc71-49d6-a9fa-a060e3ee6fee"
```

### 2. Поиск лиц
```
POST /api/v1/faces/search-session
FormData: session_id = "1788875f-fc71-49d6-a9fa-a060e3ee6fee"
↓
API Response: { session_id: "1788875f-fc71-49d6-a9fa-a060e3ee6fee", matches: [...] }
↓
JavaScript: НЕ перезаписывает this.sessionId (остается правильным)
```

### 3. Отображение результатов
```
photo.preview_path → <img src="/path/to/preview.jpg">
photo.file_path → fallback для preview_path
```

### 4. Покупка фотографий
```
this.sessionId = "1788875f-fc71-49d6-a9fa-a060e3ee6fee" (правильный)
↓
URL: https://staging.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee?selected=...
```

## Отладочная информация

### В консоли браузера будет видно:
```
URL pathname: /session/1788875f-fc71-49d6-a9fa-a060e3ee6fee
Final session ID: 1788875f-fc71-49d6-a9fa-a060e3ee6fee
Search API response: { session_id: "1788875f...", matches_count: 5 }
Current session ID for purchase: 1788875f-fc71-49d6-a9fa-a060e3ee6fee
Purchase URL: https://staging.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee?selected=...
```

### Если есть проблемы:
```
// Если session_id стал undefined:
"Ошибка: ID сессии не найден. Обновите страницу."

// Если изображения не загружаются:
// Проверить в Network tab запросы к preview_path и file_path
```

## Проверка исправлений

Создан тест `test_frontend_backend_integration.py`:
- ✅ API использует правильные поля базы данных
- ✅ Фронтенд использует правильные поля
- ✅ Session ID обрабатывается корректно
- ✅ API возвращает правильную структуру ответа

## Ожидаемый результат

### До исправления:
- ❌ `GET /session/undefined` → ошибка базы данных
- ❌ Изображения не отображаются (неправильные поля)
- ❌ Покупка не работает (неправильный session_id)

### После исправления:
- ✅ `GET /session/1788875f-fc71-49d6-a9fa-a060e3ee6fee` → корректный запрос
- ✅ Изображения отображаются (правильные поля preview_path, file_path)
- ✅ Покупка работает (правильный session_id)
- ✅ Отладочная информация в консоли для диагностики

## Заключение

Все проблемы интеграции фронтенда и бэкенда исправлены:

1. **Поля базы данных**: Используются существующие поля `preview_path` и `file_path`
2. **Session ID**: Берется только из URL, не перезаписывается из API
3. **Отладка**: Добавлено логирование для диагностики проблем
4. **Валидация**: Проверка на `undefined` значения

**Теперь система работает корректно от поиска до покупки фотографий!**