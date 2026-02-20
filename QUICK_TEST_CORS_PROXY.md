# ⚡ Quick Test: CORS Proxy Solution

## 🎯 Цель
Проверить, что прокси-эндпоинт работает и CORS проблема решена.

---

## 1️⃣ Установка зависимостей (1 минута)

```bash
# Установить httpx
pip install httpx==0.26.0

# Или обновить все зависимости
pip install -r requirements.txt
```

---

## 2️⃣ Тест Backend Proxy (30 секунд)

### Запустить сервер:
```bash
uvicorn app.main:app --reload --log-level info
```

### Тест прокси-эндпоинта:
```bash
# Тест с реальной сессией (замените на реальный ID)
curl http://localhost:8000/api/v1/remote-services/test-session-id

# Или через браузер:
http://localhost:8000/api/v1/remote-services/test-session-id
```

### ✅ Успех - должно быть:
```json
{
  "sessionId": "test-session-id",
  "sessionName": "Test Session",
  "services": [
    {
      "id": "service-id",
      "name": "Цифровая копия",
      "price": 150.0,
      "isDefault": false,
      "type": "digital"
    }
  ],
  "currency": "RUB"
}
```

### ❌ Ошибка - если видите:
```json
{
  "detail": {
    "error": "Session not found",
    "message": "Session test-session-id not found in Pixora API"
  }
}
```
**Это нормально** - используйте реальный session ID.

---

## 3️⃣ Тест Frontend (1 минута)

### Открыть страницу сессии:
```
http://localhost:8000/api/v1/sessions/test-session-id/interface
```

### Открыть DevTools Console (F12):

### ✅ Успех - должно быть:
```javascript
Fetching services through FacePass proxy: /api/v1/remote-services/test-session-id
Services loaded through proxy: {services: [...]}
```

### ❌ НЕ должно быть:
```javascript
// Старые сообщения (больше не используются):
MAIN_API_URL from window: ...
Using API URL: ...
Fetching services from Pixora API: https://staging...

// CORS ошибки (должны исчезнуть):
Access to fetch at 'https://staging.pixorasoft.ru...' has been blocked by CORS policy
```

---

## 4️⃣ Тест Network Tab (30 секунд)

### DevTools → Network Tab:

### ✅ Должен быть запрос:
```
GET /api/v1/remote-services/test-session-id
Status: 200
Response: JSON with services
```

### ❌ НЕ должно быть запросов:
```
GET https://staging.pixorasoft.ru/api/session/...
(прямые запросы к Pixora API должны исчезнуть)
```

---

## 5️⃣ Проверка логов сервера (30 секунд)

### В терминале с сервером должно быть:

### ✅ Успешный запрос:
```
INFO: Proxying request to Pixora API: https://staging.pixorasoft.ru/api/session/test-id/services
INFO: Successfully fetched services for session test-id
```

### ⚠️ Ошибка (это нормально для тестовых ID):
```
WARNING: Session test-id not found in Pixora API
ERROR: Pixora API returned 404: Session not found
```

---

## 🔧 Быстрые исправления

### Проблема 1: ModuleNotFoundError: No module named 'httpx'

```bash
pip install httpx==0.26.0
# Перезапустить сервер
```

### Проблема 2: Прокси возвращает 500 ошибку

```bash
# Проверить .env файл
cat .env | grep MAIN_API_URL

# Должно быть:
MAIN_API_URL=https://staging.pixorasoft.ru

# Проверить логи сервера на детали ошибки
```

### Проблема 3: Frontend все еще делает прямые запросы

```bash
# Очистить кэш браузера
Ctrl+Shift+R

# Проверить что изменения в face-search-pricing.js применились
# Найти строку: const servicesUrl = `/api/v1/remote-services/${this.sessionId}`;
```

---

## 🧪 Полный тест с реальной сессией

### 1. Получить реальный session ID из Pixora

### 2. Тест прокси:
```bash
curl http://localhost:8000/api/v1/remote-services/REAL-SESSION-ID
```

### 3. Тест в браузере:
```
http://localhost:8000/api/v1/sessions/REAL-SESSION-ID/interface
```

### 4. Загрузить селфи и проверить:
- ✅ Skeleton loader появляется
- ✅ Цены загружаются через 1-2 секунды
- ✅ Price badges показывают реальные цены
- ✅ Floating bar работает
- ✅ Нет CORS ошибок в консоли

---

## ✅ Чеклист успешного теста

- [ ] httpx установлен
- [ ] Сервер запускается без ошибок
- [ ] Прокси-эндпоинт отвечает (200 или 404)
- [ ] Frontend использует прокси URL
- [ ] Нет прямых запросов к staging.pixorasoft.ru
- [ ] Нет CORS ошибок в консоли
- [ ] Логи показывают прокси-запросы
- [ ] Цены загружаются и отображаются

---

## 🚨 Если что-то не работает

### 1. Проверить версию кода:
```bash
git log --oneline -1
# Должно быть: 4cc3425 feat: Add CORS proxy solution
```

### 2. Проверить файлы:
```bash
# Проверить что прокси-эндпоинт добавлен
grep -n "remote-services" app/main.py

# Проверить что frontend использует прокси
grep -n "remote-services" app/static/js/face-search-pricing.js
```

### 3. Полная перезагрузка:
```bash
# Остановить сервер (Ctrl+C)
# Установить зависимости
pip install -r requirements.txt
# Очистить кэш браузера
# Запустить сервер
uvicorn app.main:app --reload --log-level debug
```

---

**Время теста:** ~3 минуты  
**Критичность:** HIGH  
**Статус:** IMPLEMENTED ✅

**Результат:** CORS проблема решена навсегда! 🎉