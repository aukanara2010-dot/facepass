# Быстрый старт: Интеграция ценообразования

## Что реализовано

✅ Автоматическая загрузка цен из API Pixora  
✅ Отображение ценников на каждой фотографии  
✅ Плавающая панель покупки внизу экрана  
✅ Подсчет итоговой стоимости в реальном времени  
✅ Две кнопки покупки: выбранные фото и весь архив  
✅ Редирект на корзину Pixora с параметрами  

## Настройка

### 1. Переменные окружения (.env)

```env
MAIN_API_URL=https://staging.pixorasoft.ru
MAIN_URL=https://staging.pixorasoft.ru
```

### 2. Структура таблицы packages (Pixora DB)

```sql
CREATE TABLE packages (
    id SERIAL PRIMARY KEY,
    photo_session_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    type VARCHAR(50),  -- 'digital', 'archive', etc.
    photo_count INTEGER,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 3. Пример данных

```sql
INSERT INTO packages (photo_session_id, name, description, price, is_default, type, photo_count, is_active)
VALUES 
    ('abc-123-def', 'Цифровая копия', 'Одна фотография', 150.00, false, 'digital', 1, true),
    ('abc-123-def', 'Весь архив', 'Все фотографии сессии', 2500.00, true, 'archive', null, true);
```

## Как это работает

### Пользовательский сценарий

1. **Пользователь открывает сессию** → Автоматически загружаются услуги и цены
2. **Загружает селфи** → Система находит похожие фото
3. **Видит результаты** → На каждом фото отображается цена (например, "150 ₽")
4. **Выбирает фото** → Внизу появляется панель: "Выбрано: 5, Итого: 750 ₽"
5. **Нажимает "Купить выбранные"** → Редирект на корзину Pixora

### API Flow

```
GET /api/v1/sessions/{session_id}/services
    ↓
Response: {
    "services": [
        {"name": "Цифровая копия", "price": 150, "type": "digital"},
        {"name": "Весь архив", "price": 2500, "isDefault": true}
    ],
    "mainUrl": "https://staging.pixorasoft.ru"
}
    ↓
Frontend отображает цены и кнопки покупки
```

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

**Причина:** Услуги не загрузились

**Решение:**
1. Проверьте `/api/v1/sessions/{id}/services`
2. Убедитесь, что таблица `packages` существует
3. Проверьте, что есть активные услуги для сессии

### Floating bar не появляется

**Причина:** `photoPrice = 0` или нет результатов поиска

**Решение:**
1. Проверьте, что услуга типа `digital` существует
2. Проверьте console.log в браузере
3. Убедитесь, что поиск вернул результаты

### Редирект не работает

**Причина:** Неверный `MAIN_URL`

**Решение:**
1. Проверьте `.env`: `MAIN_URL=https://staging.pixorasoft.ru`
2. Перезапустите сервер
3. Проверьте `this.mainUrl` в console

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
