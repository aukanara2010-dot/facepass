# Сводка: Интеграция реального времени с Pixora API

## 🎯 Что изменилось

### До (старая версия)
- ❌ Цены загружались через локальный proxy endpoint FacePass
- ❌ Данные могли быть устаревшими
- ❌ Требовалась синхронизация между базами данных
- ❌ Задержка в обновлении цен

### После (новая версия)
- ✅ **Прямые запросы к Pixora API с клиента**
- ✅ **Всегда актуальные цены в реальном времени**
- ✅ **Нет необходимости в синхронизации**
- ✅ **Мгновенное отражение изменений**

## 🔄 Архитектура

```
┌─────────────┐
│   Browser   │
│  (FacePass) │
└──────┬──────┘
       │
       │ Direct fetch()
       │ GET /api/session/{id}/services
       │
       ↓
┌─────────────┐
│  Pixora API │
│   (Main)    │
└──────┬──────┘
       │
       │ Query database
       │ photo_sessions → service_package_id
       │ → service_package_services → services
       │
       ↓
┌─────────────────────────────┐
│  Database Schema:           │
│  • photo_sessions           │
│  • service_packages         │
│  • service_package_services │
│  • services                 │
└─────────────────────────────┘
```

## 📋 Ключевые изменения

### 1. Client-Side Fetching

**Файл:** `app/static/js/face-search-pricing.js`

```javascript
async loadServicesFromPixora() {
    const mainApiUrl = window.MAIN_API_URL || 'https://staging.pixorasoft.ru';
    const servicesUrl = `${mainApiUrl}/api/session/${this.sessionId}/services`;
    
    const response = await fetch(servicesUrl);
    const data = await response.json();
    
    const prices = this.getServicePrices(data.services);
    this.photoPrice = prices.price_single;
    this.priceAll = prices.price_all;
}
```

### 2. Price Mapping Function

```javascript
getServicePrices(services) {
    // price_all: услуга с isDefault === true
    const defaultService = services.find(s => s.isDefault === true);
    const price_all = defaultService ? defaultService.price : 0;
    
    // price_single: услуга типа 'digital'
    const singleService = services.find(s => 
        s.type === 'digital' || 
        s.name?.toLowerCase().includes('цифровая')
    );
    const price_single = singleService ? singleService.price : 0;
    
    return { price_single, price_all };
}
```

### 3. Skeleton Loader

**Во время загрузки:**
```html
<div class="price-badge-skeleton bg-gray-300 animate-pulse"></div>
```

**После загрузки:**
```html
<span class="price-badge">150 ₽</span>
```

### 4. View-Only Mode

Если услуги недоступны:
- Скрываются ценники
- Скрывается floating bar
- Остается только просмотр фото

## 🔧 Настройка

### 1. Environment Variables

```env
MAIN_API_URL=https://staging.pixorasoft.ru
MAIN_URL=https://staging.pixorasoft.ru
```

### 2. CORS на Pixora API

**Обязательно настроить!** См. `docs/CORS_SETUP_FOR_PIXORA.md`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://facepass.pixorasoft.ru"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)
```

### 3. API Endpoint на Pixora

**URL:** `GET /api/session/{sessionId}/services`

**Response:**
```json
{
  "services": [
    {
      "id": 1,
      "name": "Цифровая копия",
      "price": 150.0,
      "isDefault": false,
      "type": "digital"
    },
    {
      "id": 2,
      "name": "Весь архив",
      "price": 2500.0,
      "isDefault": true,
      "type": "archive"
    }
  ]
}
```

## ✅ Преимущества

### Для пользователей
- 🚀 Всегда актуальные цены
- ⚡ Быстрая загрузка (прямой запрос)
- 🎨 Плавная анимация загрузки
- 📱 Работает на всех устройствах

### Для разработчиков
- 🔄 Нет синхронизации баз данных
- 🐛 Меньше точек отказа
- 📊 Единый источник правды (Pixora API)
- 🔧 Легко обновлять цены

### Для бизнеса
- 💰 Мгновенное изменение цен
- 📈 A/B тестирование цен
- 🎯 Динамическое ценообразование
- 📊 Централизованное управление

## 🧪 Тестирование

### 0. Проверка Template Variable Injection

**Важно!** Убедитесь, что `window.MAIN_API_URL` правильно подставляется backend'ом:

```javascript
// Откройте DevTools → Console на странице сессии
console.log(window.MAIN_API_URL);
// Должно быть: "https://staging.pixorasoft.ru"
// НЕ должно быть: "{{ MAIN_API_URL }}"
```

**Если видите `{{ MAIN_API_URL }}`:**
- Backend не заменяет template variable
- Проверьте `app/api/v1/endpoints/sessions.py` (строки 265-285)
- Проверьте логи сервера на наличие warnings

**Fallback механизм:**
JavaScript автоматически использует fallback если template не заменен:
```javascript
let mainApiUrl = window.MAIN_API_URL || 'https://staging.pixorasoft.ru';
if (mainApiUrl.includes('{{') || mainApiUrl.includes('}}')) {
    mainApiUrl = 'https://staging.pixorasoft.ru';
}
```

### 1. Проверка загрузки услуг

```bash
# Откройте DevTools → Console
# Должно быть:
Fetching services from Pixora API: https://staging.pixorasoft.ru/api/session/...
Services loaded from Pixora: {...}
Pricing configured: {photoPrice: 150, priceAll: 2500}
```

### 2. Проверка CORS

```bash
curl -I -X OPTIONS \
  -H "Origin: https://facepass.pixorasoft.ru" \
  https://staging.pixorasoft.ru/api/session/test/services
```

### 3. Проверка UI

1. Откройте сессию
2. Проверьте skeleton loader (серый пульсирующий badge)
3. Дождитесь загрузки цен
4. Проверьте отображение реальных ценников
5. Выполните поиск фото
6. Проверьте floating bar

## 🚨 Важные моменты

### Template Variable Injection

Backend должен заменять `{{ MAIN_API_URL }}` в HTML на реальное значение из `.env`:

**Файл:** `app/api/v1/endpoints/sessions.py` (строки 265-285)
```python
# Inject MAIN_API_URL from settings
main_api_url = settings.MAIN_API_URL

# Replace all possible template variations
replacements = [
    ("'{{ MAIN_API_URL }}'", f"'{main_api_url}'"),
    ('"{{ MAIN_API_URL }}"', f'"{main_api_url}"'),
    ('{{ MAIN_API_URL }}', main_api_url),
]

for old, new in replacements:
    if old in html_content:
        html_content = html_content.replace(old, new)
        logger.info(f"Replaced '{old}' with '{new}'")
```

**Проверка:** Откройте исходный код страницы (Ctrl+U) и найдите `window.MAIN_API_URL`. Должно быть:
```html
<script>
    window.MAIN_API_URL = "https://staging.pixorasoft.ru";
</script>
```

### CORS обязателен!

Без настройки CORS на Pixora API запросы будут блокироваться браузером.

### Fallback на view-only

Если услуги недоступны, интерфейс автоматически переключается в режим просмотра.

### Кэширование

Цены загружаются при каждом открытии страницы - кэширование не используется для актуальности.

### Безопасность

- Только GET запросы
- Нет передачи credentials
- Публичный API endpoint

## 📚 Документация

- `docs/PRICING_INTEGRATION.md` - Полная техническая документация
- `docs/PRICING_QUICK_START.md` - Быстрый старт
- `docs/CORS_SETUP_FOR_PIXORA.md` - Настройка CORS

## 🔄 Миграция

### Что нужно сделать на Pixora

1. ✅ Создать endpoint `/api/session/{id}/services`
2. ✅ Настроить CORS для домена FacePass
3. ✅ Убедиться, что формат ответа соответствует спецификации
4. ✅ Протестировать endpoint

### Что уже сделано на FacePass

1. ✅ Реализован client-side fetching
2. ✅ Добавлен skeleton loader
3. ✅ Реализован view-only mode
4. ✅ Обновлена документация

## 📞 Поддержка

При возникновении проблем:

1. Проверьте консоль браузера (F12)
2. Проверьте Network tab для запросов
3. Проверьте CORS настройки
4. См. troubleshooting в документации

## 🎉 Результат

Теперь FacePass показывает актуальные цены в реальном времени, загружая их напрямую с Pixora API. Любые изменения цен на стороне Pixora мгновенно отражаются в интерфейсе FacePass без необходимости синхронизации или обновления кода.
