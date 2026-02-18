# 🌐 FacePass Routing & Domain Configuration

## 📋 Обзор изменений

FacePass теперь настроен для работы на домене `facepass.pixorasoft.ru` с красивыми URL и правильной интеграцией с основной системой Pixora.

## 🔗 URL Структура

### Публичные URL (для пользователей)
```
https://facepass.pixorasoft.ru/session/{session_id}
```

**Примеры:**
- `https://facepass.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee`
- `https://facepass.pixorasoft.ru/session/550e8400-e29b-41d4-a716-446655440000`

### API Endpoints (для разработчиков)
```
https://facepass.pixorasoft.ru/api/v1/sessions/{session_id}/validate
https://facepass.pixorasoft.ru/api/v1/sessions/{session_id}
https://facepass.pixorasoft.ru/api/v1/faces/search-session
```

### Статические файлы
```
https://facepass.pixorasoft.ru/static/js/face-search.js
https://facepass.pixorasoft.ru/static/images/facepass-logo.svg
https://facepass.pixorasoft.ru/static/images/favicon.svg
```

## 🎯 Интеграция с Pixora Store

### URL для покупки
После выбора фотографий пользователь перенаправляется на:
```
https://staging.pixorasoft.ru/session/{session_id}?selected={file_name1},{file_name2}
```

**Пример:**
```
https://staging.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee?selected=1769178641830-abc123,1769178641831-def456
```

### Логика формирования URL покупки
```javascript
const selectedFileNames = this.searchResults
    .filter(photo => this.selectedPhotos.has(photo.id))
    .map(photo => photo.file_name || photo.id)
    .join(',');

const purchaseUrl = `https://staging.pixorasoft.ru/session/${this.sessionId}?selected=${selectedFileNames}`;
```

## 🔒 CORS Configuration

### Разрешенные домены
```python
allow_origins=[
    "https://facepass.pixorasoft.ru",      # Основной домен FacePass
    "https://staging.pixorasoft.ru",       # Staging Pixora для покупок
    "https://pixorasoft.ru",               # Основной сайт Pixora
    "http://localhost:3000",               # Локальная разработка
    "http://localhost:8000",               # Локальная разработка
]
```

## 📱 OpenGraph & Social Media

### Мета-теги для социальных сетей
```html
<!-- OpenGraph -->
<meta property="og:title" content="Найти фото - {session_name} | FacePass">
<meta property="og:description" content="Найдите свои фотографии с фотосессии '{session_name}' с помощью технологии распознавания лиц FacePass">
<meta property="og:image" content="https://facepass.pixorasoft.ru/static/images/facepass-og.jpg">
<meta property="og:url" content="https://facepass.pixorasoft.ru/session/{session_id}">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Найти фото - {session_name} | FacePass">
<meta name="twitter:description" content="Найдите свои фотографии с фотосессии '{session_name}'">
<meta name="twitter:image" content="https://facepass.pixorasoft.ru/static/images/facepass-og.jpg">
```

### Динамическая подстановка данных
Сервер автоматически подставляет:
- `{session_name}` - название фотосессии из базы данных
- `{session_id}` - UUID сессии из URL

## 🛠️ Техническая реализация

### FastAPI Route Handler
```python
@app.get("/session/{session_id}")
async def public_session_interface(session_id: str):
    # 1. Валидация сессии в Pixora DB
    # 2. Проверка активности FacePass
    # 3. Инжекция мета-тегов в HTML
    # 4. Возврат готового интерфейса
```

### Обработка ошибок
- **404** - Сессия не найдена
- **403** - FacePass не активен для сессии
- **500** - Внутренняя ошибка сервера

### Статические файлы
```python
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

## 🔄 Миграция с localhost

### Изменения в JavaScript
```javascript
// Было:
fetch('http://localhost:8000/api/v1/sessions/validate/...')

// Стало:
fetch('/api/v1/sessions/validate/...')  // Относительный путь
```

### Изменения в URL покупки
```javascript
// Было:
const purchaseUrl = `https://staging.pixorasoft.ru/session/${this.sessionId}?selected=${selectedFileNames}`;

// Осталось то же самое (уже правильно)
```

## 📊 SEO Оптимизация

### Заголовки страниц
```html
<!-- Главная страница -->
<title>FacePass - Поиск фотографий</title>

<!-- Страница сессии -->
<title>Найти фото - {session_name} | FacePass</title>

<!-- Ошибка 404 -->
<title>Сессия не найдена - FacePass</title>
```

### Мета-описания
```html
<meta name="description" content="Найдите свои фотографии с фотосессии '{session_name}' с помощью технологии распознавания лиц FacePass от Pixora">
<meta name="keywords" content="фотосессия, поиск фото, распознавание лиц, FacePass, Pixora, {session_name}">
```

## 🚀 Развертывание

### Nginx конфигурация
```nginx
server {
    listen 443 ssl http2;
    server_name facepass.pixorasoft.ru;
    
    # SSL certificates
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static files caching
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker Compose
```yaml
version: '3.8'
services:
  facepass:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DOMAIN=facepass.pixorasoft.ru
      - STAGING_DOMAIN=staging.pixorasoft.ru
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.facepass.rule=Host(`facepass.pixorasoft.ru`)"
      - "traefik.http.routers.facepass.tls.certresolver=letsencrypt"
```

## 📈 Аналитика и мониторинг

### Метрики для отслеживания
- **Переходы по сессиям** - количество уникальных посещений `/session/{id}`
- **Конверсия в покупки** - переходы на `staging.pixorasoft.ru`
- **Время сессии** - время проведенное на странице
- **Успешность поиска** - процент успешных поисков лиц

### Google Analytics
```html
<!-- В head секции -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## 🔧 Тестирование

### Локальное тестирование
```bash
# Запуск сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Тестирование URL
curl -I http://localhost:8000/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee
```

### Продакшн тестирование
```bash
# Проверка доступности
curl -I https://facepass.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee

# Проверка API
curl https://facepass.pixorasoft.ru/api/v1/sessions/validate/1788875f-fc71-49d6-a9fa-a060e3ee6fee
```

## 🎨 Брендинг

### Логотип и иконки
- **Основной логотип**: `/static/images/facepass-logo.svg`
- **Favicon**: `/static/images/favicon.svg`
- **OpenGraph изображение**: `/static/images/facepass-og.jpg`

### Цветовая схема
```css
:root {
  --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --primary-color: #667eea;
  --secondary-color: #764ba2;
  --text-white: #ffffff;
  --glass-bg: rgba(255, 255, 255, 0.1);
}
```

## 📞 Поддержка и обратная связь

### Контактная информация
- **Email**: support@pixorasoft.ru
- **Telegram**: @pixora_support
- **Документация**: https://docs.pixorasoft.ru/facepass

### Отчеты об ошибках
Для сообщения об ошибках используйте:
1. **GitHub Issues** (для разработчиков)
2. **Email поддержки** (для пользователей)
3. **Telegram чат** (для срочных вопросов)

---

## ✅ Чек-лист миграции

- [x] Обновлены CORS настройки
- [x] Добавлен публичный роут `/session/{session_id}`
- [x] Обновлены относительные пути в JavaScript
- [x] Добавлены OpenGraph мета-теги
- [x] Создан favicon и логотип
- [x] Настроена интеграция с Pixora Store
- [x] Обновлена конфигурация доменов
- [x] Добавлена обработка ошибок
- [x] Создана документация

🎉 **FacePass готов к работе на facepass.pixorasoft.ru!**