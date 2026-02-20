# Настройка CORS на Pixora API для FacePass

## Проблема

FacePass теперь загружает цены напрямую с клиента (браузера) через запросы к Pixora API. Браузер блокирует такие запросы из-за политики CORS (Cross-Origin Resource Sharing), если сервер не разрешает их явно.

## Симптомы

В консоли браузера (DevTools → Console) появляется ошибка:

```
Access to fetch at 'https://staging.pixorasoft.ru/api/session/abc-123/services' 
from origin 'https://facepass.pixorasoft.ru' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Решение

Необходимо настроить CORS на Pixora API для разрешения запросов с домена FacePass.

### Для FastAPI (Python)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://facepass.pixorasoft.ru",  # Production
        "http://localhost:8000",            # Local development
        "http://127.0.0.1:8000"             # Local development
    ],
    allow_credentials=False,  # FacePass не отправляет cookies
    allow_methods=["GET", "OPTIONS"],  # Только чтение
    allow_headers=["Accept", "Content-Type"],
    max_age=3600  # Кэширование preflight запросов на 1 час
)
```

### Для Express.js (Node.js)

```javascript
const express = require('express');
const cors = require('cors');

const app = express();

// CORS Configuration
app.use(cors({
    origin: [
        'https://facepass.pixorasoft.ru',
        'http://localhost:8000',
        'http://127.0.0.1:8000'
    ],
    methods: ['GET', 'OPTIONS'],
    allowedHeaders: ['Accept', 'Content-Type'],
    credentials: false,
    maxAge: 3600
}));
```

### Для Nginx (Reverse Proxy)

```nginx
server {
    listen 443 ssl;
    server_name staging.pixorasoft.ru;

    location /api/session/ {
        # CORS Headers
        add_header 'Access-Control-Allow-Origin' 'https://facepass.pixorasoft.ru' always;
        add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Accept, Content-Type' always;
        add_header 'Access-Control-Max-Age' '3600' always;

        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' 'https://facepass.pixorasoft.ru' always;
            add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Accept, Content-Type' always;
            add_header 'Access-Control-Max-Age' '3600' always;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' '0';
            return 204;
        }

        proxy_pass http://backend;
    }
}
```

### Для Apache (.htaccess)

```apache
<IfModule mod_headers.c>
    # CORS Headers
    Header set Access-Control-Allow-Origin "https://facepass.pixorasoft.ru"
    Header set Access-Control-Allow-Methods "GET, OPTIONS"
    Header set Access-Control-Allow-Headers "Accept, Content-Type"
    Header set Access-Control-Max-Age "3600"
    
    # Handle preflight requests
    RewriteEngine On
    RewriteCond %{REQUEST_METHOD} OPTIONS
    RewriteRule ^(.*)$ $1 [R=204,L]
</IfModule>
```

## Проверка настройки

### 1. Проверка через curl

```bash
curl -I -X OPTIONS \
  -H "Origin: https://facepass.pixorasoft.ru" \
  -H "Access-Control-Request-Method: GET" \
  https://staging.pixorasoft.ru/api/session/test-id/services
```

**Ожидаемый ответ:**
```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://facepass.pixorasoft.ru
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Accept, Content-Type
Access-Control-Max-Age: 3600
```

### 2. Проверка через браузер

1. Откройте FacePass: `https://facepass.pixorasoft.ru/session/{session_id}`
2. Откройте DevTools (F12) → Network tab
3. Найдите запрос к `/api/session/{id}/services`
4. Проверьте Response Headers:
   - `Access-Control-Allow-Origin: https://facepass.pixorasoft.ru`
   - `Access-Control-Allow-Methods: GET, OPTIONS`

### 3. Проверка через онлайн-инструмент

Используйте https://www.test-cors.org/:

- **URL:** `https://staging.pixorasoft.ru/api/session/test-id/services`
- **Origin:** `https://facepass.pixorasoft.ru`
- **Method:** GET

## Безопасность

### Рекомендации

1. **Ограничьте домены:** Разрешайте только конкретные домены FacePass
2. **Только GET:** Не разрешайте POST/PUT/DELETE для безопасности
3. **Без credentials:** FacePass не нужны cookies/auth headers
4. **Кэширование preflight:** Используйте `max-age` для производительности

### Что НЕ делать

❌ **НЕ используйте `allow_origins=["*"]`** - это небезопасно  
❌ **НЕ разрешайте все методы** - только GET и OPTIONS  
❌ **НЕ включайте credentials** - FacePass работает без авторизации  

## Тестирование

### Локальная разработка

Для тестирования на localhost добавьте в CORS:

```python
allow_origins=[
    "https://facepass.pixorasoft.ru",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]
```

### Production

Для production используйте только HTTPS домены:

```python
allow_origins=[
    "https://facepass.pixorasoft.ru"
]
```

## Troubleshooting

### Ошибка: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Причина:** CORS не настроен или настроен неправильно

**Решение:**
1. Проверьте, что middleware добавлен в приложение
2. Проверьте, что домен FacePass в списке `allow_origins`
3. Перезапустите сервер Pixora API

### Ошибка: "CORS policy: The value of the 'Access-Control-Allow-Origin' header must not be the wildcard '*'"

**Причина:** Используется `*` вместо конкретного домена

**Решение:**
Замените `allow_origins=["*"]` на конкретный список доменов

### Preflight запросы не проходят

**Причина:** OPTIONS метод не обрабатывается

**Решение:**
Убедитесь, что `allow_methods` включает `"OPTIONS"`

### Запросы работают в Postman, но не в браузере

**Причина:** Postman не проверяет CORS, браузер проверяет

**Решение:**
Настройте CORS на сервере - это обязательно для браузерных запросов

## Мониторинг

### Логирование CORS запросов

```python
import logging

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_cors_requests(request, call_next):
    origin = request.headers.get("origin")
    if origin:
        logger.info(f"CORS request from: {origin}")
    response = await call_next(request)
    return response
```

### Метрики

Отслеживайте:
- Количество CORS preflight запросов (OPTIONS)
- Количество отклоненных CORS запросов
- Источники запросов (origins)

## Дополнительные ресурсы

- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Express CORS](https://expressjs.com/en/resources/middleware/cors.html)

## Контакты

При проблемах с настройкой CORS обращайтесь к команде разработки Pixora.
