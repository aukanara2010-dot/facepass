# 🔄 CORS Proxy Solution

## Проблема

Pixora API не настроен для CORS, поэтому браузер блокирует прямые запросы от FacePass к Pixora API:

```
Access to fetch at 'https://staging.pixorasoft.ru/api/session/abc123/services' 
from origin 'https://facepass.pixorasoft.ru' has been blocked by CORS policy
```

## Решение: Server-to-Server Proxy

Создан прокси-эндпоинт в FastAPI, который делает запросы от сервера к серверу (CORS не применяется).

---

## 🔧 Архитектура

### До (с CORS проблемой):
```
Browser (FacePass) ──X──> Pixora API
                   CORS блокирует
```

### После (с прокси):
```
Browser (FacePass) ──✅──> FacePass API ──✅──> Pixora API
                    Same-origin      Server-to-server
                                    (CORS не проверяется)
```

---

## 📝 Реализация

### 1. Backend: Прокси-эндпоинт (main.py)

```python
@app.get("/api/v1/remote-services/{session_id}")
async def get_remote_services(session_id: str):
    """
    Proxy endpoint to fetch services from Pixora API.
    Bypasses CORS by making server-to-server requests.
    """
    settings = get_settings()
    pixora_url = f"{settings.MAIN_API_URL}/api/session/{session_id}/services"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(pixora_url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, ...)
```

**Особенности:**
- ✅ Использует `httpx.AsyncClient` для асинхронных запросов
- ✅ Timeout 30 секунд
- ✅ Подробная обработка ошибок
- ✅ Логирование всех запросов
- ✅ Возвращает оригинальный JSON от Pixora

---

### 2. Frontend: Обновленный запрос (face-search-pricing.js)

```javascript
async loadServicesFromPixora() {
    // БЫЛО: Прямой запрос к Pixora (блокируется CORS)
    // const servicesUrl = `${mainApiUrl}/api/session/${this.sessionId}/services`;
    
    // СТАЛО: Запрос через прокси (same-origin, CORS не проверяется)
    const servicesUrl = `/api/v1/remote-services/${this.sessionId}`;
    
    const response = await fetch(servicesUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        credentials: 'same-origin'  // Локальный запрос
    });
}
```

**Изменения:**
- ✅ URL изменен на локальный прокси-эндпоинт
- ✅ `credentials: 'same-origin'` вместо `'omit'`
- ✅ Убрано формирование внешнего URL
- ✅ Сохранена вся логика обработки ответа

---

## 🧪 Тестирование

### 1. Проверка прокси-эндпоинта

```bash
# Прямой тест прокси
curl http://localhost:8000/api/v1/remote-services/test-session-id

# Должен вернуть:
{
  "services": [...],
  "sessionId": "test-session-id",
  "currency": "RUB"
}

# Или ошибку:
{
  "detail": {
    "error": "Session not found",
    "message": "Session test-session-id not found in Pixora API"
  }
}
```

### 2. Проверка в браузере

**DevTools Console:**
```javascript
// Должно быть:
Fetching services through FacePass proxy: /api/v1/remote-services/abc123
Services loaded through proxy: {services: [...]}

// НЕ должно быть:
CORS policy blocked...
Network error...
```

**DevTools Network:**
```
✅ GET /api/v1/remote-services/abc123  Status: 200
✅ Response: JSON with services

❌ НЕ должно быть запросов к staging.pixorasoft.ru
```

---

## 🔍 Обработка ошибок

### 1. Pixora API недоступен

```json
{
  "detail": {
    "error": "Network error",
    "message": "Unable to connect to Pixora API",
    "suggestion": "Check your internet connection or try again later"
  }
}
```

### 2. Сессия не найдена

```json
{
  "detail": {
    "error": "Session not found", 
    "message": "Session abc123 not found in Pixora API",
    "session_id": "abc123"
  }
}
```

### 3. Timeout

```json
{
  "detail": {
    "error": "Request timeout",
    "message": "Pixora API did not respond within 30 seconds",
    "suggestion": "Try again later or contact support"
  }
}
```

### 4. Frontend обработка

```javascript
if (!response.ok) {
    console.warn(`Proxy API returned ${response.status}, running in view-only mode`);
    
    // Показать детали ошибки
    const errorData = await response.json();
    console.error('Proxy API error details:', errorData);
    
    // Переключиться в view-only режим
    this.updateUIForViewOnlyMode();
}
```

---

## 📊 Преимущества решения

### 1. Надежность
- ✅ Нет зависимости от CORS настроек Pixora
- ✅ Работает из любого браузера
- ✅ Не требует изменений в Pixora API

### 2. Безопасность
- ✅ Все запросы проходят через FacePass сервер
- ✅ Можно добавить аутентификацию/авторизацию
- ✅ Логирование всех запросов

### 3. Производительность
- ✅ Асинхронные запросы с httpx
- ✅ Timeout 30 секунд
- ✅ Подробная обработка ошибок

### 4. Мониторинг
- ✅ Все запросы логируются в FacePass
- ✅ Детальная информация об ошибках
- ✅ Легко добавить метрики

---

## 🔄 Миграция

### Что изменилось:

**Frontend:**
```javascript
// БЫЛО:
const servicesUrl = `${mainApiUrl}/api/session/${this.sessionId}/services`;

// СТАЛО:
const servicesUrl = `/api/v1/remote-services/${this.sessionId}`;
```

**Backend:**
- ✅ Добавлен новый эндпоинт `/api/v1/remote-services/{session_id}`
- ✅ Добавлен `httpx==0.26.0` в requirements.txt

**Что НЕ изменилось:**
- ✅ Формат ответа остался тот же
- ✅ Логика обработки цен не изменилась
- ✅ UI компоненты работают как прежде

---

## 🚀 Развертывание

### 1. Установить зависимости

```bash
pip install httpx==0.26.0
# или
pip install -r requirements.txt
```

### 2. Перезапустить сервер

```bash
uvicorn app.main:app --reload
```

### 3. Проверить работу

```bash
# Тест прокси
curl http://localhost:8000/api/v1/remote-services/test-id

# Открыть FacePass в браузере
# Проверить DevTools Console на отсутствие CORS ошибок
```

---

## 📈 Мониторинг

### Логи сервера

```bash
# Успешный запрос
INFO: Proxying request to Pixora API: https://staging.pixorasoft.ru/api/session/abc123/services
INFO: Successfully fetched services for session abc123

# Ошибка
ERROR: Pixora API returned 404: Session not found
WARNING: Session abc123 not found in Pixora API
```

### Метрики (можно добавить)

```python
# Счетчики запросов
proxy_requests_total = 0
proxy_requests_success = 0
proxy_requests_error = 0

# Время ответа
proxy_response_time_avg = 0
```

---

## 🔧 Настройка

### Environment Variables

```env
# .env
MAIN_API_URL=https://staging.pixorasoft.ru
```

### Timeout настройки

```python
# В main.py можно изменить timeout
async with httpx.AsyncClient(timeout=30.0) as client:
    # 30 секунд по умолчанию
    # Можно увеличить для медленных API
```

---

## 🧪 Тестовые сценарии

### Сценарий 1: Нормальная работа

```
1. Frontend делает запрос: GET /api/v1/remote-services/abc123
2. FacePass прокси делает запрос: GET https://staging.pixorasoft.ru/api/session/abc123/services
3. Pixora возвращает: 200 OK + JSON
4. FacePass возвращает: 200 OK + тот же JSON
5. Frontend получает данные и отображает цены
```

### Сценарий 2: Сессия не найдена

```
1. Frontend: GET /api/v1/remote-services/invalid-id
2. FacePass прокси: GET https://staging.pixorasoft.ru/api/session/invalid-id/services
3. Pixora: 404 Not Found
4. FacePass: 404 + подробная ошибка
5. Frontend: view-only режим
```

### Сценарий 3: Pixora API недоступен

```
1. Frontend: GET /api/v1/remote-services/abc123
2. FacePass прокси: Timeout/Network Error
3. FacePass: 503 Service Unavailable + ошибка
4. Frontend: view-only режим + сообщение об ошибке
```

---

## 📋 Чеклист развертывания

- [x] Добавлен httpx в requirements.txt
- [x] Создан прокси-эндпоинт в main.py
- [x] Обновлен JavaScript для использования прокси
- [x] Добавлена обработка всех типов ошибок
- [x] Добавлено логирование
- [x] Протестирован локально
- [ ] Развернуто на staging
- [ ] Протестировано с реальными сессиями
- [ ] Развернуто на production

---

## 🎯 Результат

✅ **CORS проблема решена навсегда**  
✅ **Не требует изменений в Pixora API**  
✅ **Работает из любого браузера**  
✅ **Подробная обработка ошибок**  
✅ **Полное логирование**  

**Система готова к работе!**

---

**Дата:** 2026-02-20  
**Версия:** 1.0  
**Статус:** Implemented ✅