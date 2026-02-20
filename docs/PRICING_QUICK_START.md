# Быстрый старт: Интеграция ценообразования

## Что реализовано

✅ **Прямая загрузка цен с Pixora API** - всегда актуальные данные  
✅ Автоматическая загрузка при открытии страницы  
✅ Skeleton loader во время загрузки цен  
✅ Отображение ценников на каждой фотографии  
✅ Плавающая панель покупки внизу экрана  
✅ Подсчет итоговой стоимости в реальном времени  
✅ Две кнопки покупки: выбранные фото и весь архив  
✅ Редирект на корзину Pixora с параметрами  
✅ Graceful degradation при отсутствии услуг  

## Архитектура

### Client-Side Fetching (Прямое обращение к Pixora API)

```javascript
// Загрузка услуг напрямую с мейн-сервиса
async loadServicesFromPixora() {
    const mainApiUrl = window.MAIN_API_URL || 'https://staging.pixorasoft.ru';
    const servicesUrl = `${mainApiUrl}/api/session/${this.sessionId}/services`;
    
    const response = await fetch(servicesUrl);
    const data = await response.json();
    
    // Извлечение цен
    const prices = this.getServicePrices(data.services);
    this.photoPrice = prices.price_single;
    this.priceAll = prices.price_all;
}
```

### Mapping цен (getServicePrices)

```javascript
getServicePrices(services) {
    // price_all: услуга с isDefault === true
    const defaultService = services.find(s => s.isDefault === true);
    const price_all = defaultService ? defaultService.price : 0;
    
    // price_single: услуга типа 'digital' или первая в списке
    let singleService = services.find(s => 
        s.type === 'digital' || 
        s.name?.toLowerCase().includes('цифровая')
    );
    const price_single = singleService ? singleService.price : 0;
    
    return { price_single, price_all };
}
```

## Настройка

### 1. Переменные окружения (.env)

```env
# Main Pixora API URL - используется для прямых запросов с клиента
MAIN_API_URL=https://staging.pixorasoft.ru
MAIN_URL=https://staging.pixorasoft.ru
```

**Важно:** URL должен быть доступен с клиента (браузера), так как запросы идут напрямую к Pixora API.

### 2. CORS настройки на Pixora API

Убедитесь, что Pixora API разрешает CORS запросы с домена FacePass:

```
Access-Control-Allow-Origin: https://facepass.pixorasoft.ru
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Content-Type, Accept
```

### 3. Структура API ответа Pixora

**Endpoint:** `GET {MAIN_API_URL}/api/session/{sessionId}/services`

**Ожидаемый формат:**
```json
{
  "services": [
    {
      "id": 1,
      "name": "Цифровая копия",
      "description": "Одна фотография в цифровом формате",
      "price": 150.0,
      "isDefault": false,
      "type": "digital",
      "photoCount": 1,
      "isActive": true
    },
    {
      "id": 2,
      "name": "Весь архив",
      "description": "Все фотографии сессии",
      "price": 2500.0,
      "isDefault": true,
      "type": "archive",
      "photoCount": null,
      "isActive": true
    }
  ]
}
```

## Как это работает

### Пользовательский сценарий

1. **Пользователь открывает сессию** → Показывается skeleton loader на месте цен
2. **Загрузка услуг с Pixora API** → Прямой запрос к `{MAIN_API_URL}/api/session/{id}/services`
3. **Цены загружены** → Skeleton заменяется на реальные ценники
4. **Загружает селфи** → Система находит похожие фото
5. **Видит результаты** → На каждом фото отображается цена (например, "150 ₽")
6. **Выбирает фото** → Внизу появляется панель: "Выбрано: 5, Итого: 750 ₽"
7. **Нажимает "Купить выбранные"** → Редирект на корзину Pixora

### API Flow (Client-Side)

```
Page Load
    ↓
loadServicesFromPixora() - прямой запрос к Pixora API
    ↓
GET {MAIN_API_URL}/api/session/{sessionId}/services
    ↓
Response: { services: [...] }
    ↓
getServicePrices() - извлечение price_single и price_all
    ↓
updateUI() - отображение цен, показ floating bar
```

### Skeleton Loader

Во время загрузки услуг показывается анимированный placeholder:

```html
<div class="price-badge-skeleton bg-gray-300 animate-pulse rounded-full" 
     style="width: 60px; height: 28px;">
</div>
```

После загрузки заменяется на реальный ценник или скрывается, если услуги недоступны.

## URL для корзины

### Покупка выбранных фото

```
https://staging.pixorasoft.ru/session/{session_id}/cart?selected=1,2,3&source=facepass
```

### Покупка всего архива

```
https://staging.pixorasoft.ru/session/{session_id}/cart?package=digital&source=facepass
```

## UI Компоненты

### Price Badge (Ценник)

```html
<span class="price-badge bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
    150 ₽
</span>
```

**Расположение:** Левый верхний угол карточки фото

### Floating Bar (Панель покупки)

```html
<div id="floating-bar" class="fixed bottom-0 bg-white/70 backdrop-blur-md">
    <p>Выбрано фото: <span id="selected-count">5</span></p>
    <p>Итого: <span id="total-price">750</span> ₽</p>
    <button id="buy-selected-btn">Купить выбранные</button>
    <button id="buy-archive-btn">Купить весь архив</button>
</div>
```

**Расположение:** Зафиксирована внизу экрана

## Режим "только просмотр"

Если услуги недоступны (таблица packages пустая или не существует):

- ❌ Ценники не отображаются
- ❌ Floating bar скрыта
- ✅ Поиск фото работает нормально
- ✅ Можно просматривать результаты

## Тестирование

### 1. Проверка API

```bash
curl http://localhost:8000/api/v1/sessions/YOUR_SESSION_ID/services
```

**Ожидаемый ответ:**
```json
{
  "sessionId": "...",
  "services": [...],
  "defaultService": {...},
  "mainUrl": "https://staging.pixorasoft.ru"
}
```

### 2. Проверка UI

1. Откройте `/session/{session_id}`
2. Загрузите селфи
3. Проверьте наличие ценников на фото
4. Выберите несколько фото
5. Проверьте появление floating bar
6. Проверьте подсчет итоговой суммы

### 3. Проверка редиректа

1. Откройте DevTools → Network
2. Нажмите "Купить выбранные"
3. Проверьте URL: должен содержать `?selected=...&source=facepass`

## Troubleshooting

### Ценники не отображаются

**Причина 1:** Услуги не загрузились с Pixora API

**Решение:**
1. Откройте DevTools → Console
2. Проверьте ошибки загрузки: `Fetching services from Pixora API`
3. Проверьте CORS: должен быть разрешен доступ с домена FacePass
4. Проверьте URL: `{MAIN_API_URL}/api/session/{id}/services`

**Причина 2:** API вернул пустой массив услуг

**Решение:**
1. Проверьте, что услуги созданы для этой сессии в Pixora
2. Проверьте, что `isActive = true`
3. Проверьте формат ответа API

### CORS ошибки

**Симптомы:**
```
Access to fetch at 'https://staging.pixorasoft.ru/api/session/...' 
from origin 'https://facepass.pixorasoft.ru' has been blocked by CORS policy
```

**Решение:**
Настройте CORS на Pixora API:
```python
# В FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://facepass.pixorasoft.ru"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
```

### Skeleton loader не исчезает

**Причина:** Запрос к API завис или вернул ошибку

**Решение:**
1. Проверьте Network tab в DevTools
2. Проверьте timeout запроса
3. Проверьте, что `servicesLoading` меняется на `false`

### Floating bar не появляется

**Причина:** Одно из условий не выполнено

**Проверьте:**
```javascript
// Условия показа floating bar:
this.searchResults.length > 0 &&  // Есть результаты поиска
!this.servicesLoading &&          // Услуги загружены
this.photoPrice > 0 &&            // Есть цена для фото
!this.servicesError               // Нет ошибки загрузки
```

### Цены не обновляются

**Причина:** Кэширование браузера

**Решение:**
1. Очистите кэш браузера (Ctrl+Shift+Delete)
2. Откройте в режиме инкогнито
3. Проверьте, что запрос идет к правильному URL
4. Проверьте заголовки кэширования на Pixora API

## Дальнейшая разработка

### Добавление новых типов услуг

```sql
INSERT INTO packages (photo_session_id, name, price, type)
VALUES ('session-id', 'Печать 10x15', 50.00, 'print');
```

### Изменение цен

```sql
UPDATE packages 
SET price = 200.00 
WHERE type = 'digital' AND photo_session_id = 'session-id';
```

### Деактивация услуги

```sql
UPDATE packages 
SET is_active = false 
WHERE id = 123;
```

## Поддержка

Полная документация: `docs/PRICING_INTEGRATION.md`

Вопросы и проблемы: создайте issue в репозитории
