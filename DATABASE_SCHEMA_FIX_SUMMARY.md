# ✅ Database Schema Fix - Summary

## Проблема

FacePass использовал неправильную структуру таблиц для получения услуг и цен:
- ❌ Запрос к несуществующей таблице `packages`
- ❌ Неправильная связь `packages.photo_session_id`

## Решение

Обновлен SQL-запрос для работы с правильной структурой базы данных Pixora:

### Старый запрос (неправильный)

```sql
SELECT 
    p.id, p.name, p.description, p.price, 
    p.is_default, p.type, p.photo_count, p.is_active
FROM public.packages p
WHERE p.photo_session_id = :session_id
    AND p.is_active = true
ORDER BY p.is_default DESC, p.price ASC
```

### Новый запрос (правильный)

```sql
SELECT 
    s.id, s.name, s.description, s.price,
    sps.is_default, s.type, s.photo_count, s.is_active
FROM public.photo_sessions ps
INNER JOIN public.service_packages sp ON ps.service_package_id = sp.id
INNER JOIN public.service_package_services sps ON sp.id = sps.service_package_id
INNER JOIN public.services s ON sps.service_id = s.id
WHERE ps.id = :session_id
    AND s.is_active = true
ORDER BY sps.is_default DESC, s.price ASC
```

## Структура таблиц

```
photo_sessions
    ↓ (service_package_id)
service_packages
    ↓ (id)
service_package_services (junction table)
    ↓ (service_id)
services
```

### Ключевые изменения:

1. **photo_sessions** имеет поле `service_package_id` (не наоборот)
2. **service_package_services** - связующая таблица (many-to-many)
3. **is_default** хранится в `service_package_services`, а не в `services`
4. **services** содержит информацию об услуге (name, price, type)

## Измененные файлы

### Код
- ✅ `app/api/v1/endpoints/sessions.py` - обновлен SQL-запрос

### Документация
- ✅ `docs/DATABASE_SCHEMA_SERVICES.md` - новый файл с полным описанием схемы
- ✅ `docs/REAL_TIME_PRICING_SUMMARY.md` - обновлена диаграмма архитектуры
- ✅ `docs/PRICING_INTEGRATION.md` - исправлены упоминания packages
- ✅ `docs/PRICING_QUICK_START.md` - обновлены SQL примеры
- ✅ `docs/PRICING_TESTING_CHECKLIST.md` - обновлены требования к БД

## Пример данных

### Создание услуг для сессии

```sql
-- 1. Создать пакет услуг
INSERT INTO service_packages (id, name, description, studio_id, is_active)
VALUES (
    gen_random_uuid(),
    'Standard Package',
    'Standard photo package',
    'studio-uuid',
    true
);

-- 2. Создать услуги
INSERT INTO services (id, name, description, price, type, is_active)
VALUES 
    (gen_random_uuid(), 'Цифровая копия', 'Одна фотография', 150.00, 'digital', true),
    (gen_random_uuid(), 'Весь архив', 'Все фотографии', 2500.00, 'package', true);

-- 3. Связать услуги с пакетом
INSERT INTO service_package_services (id, service_package_id, service_id, is_default)
SELECT 
    gen_random_uuid(),
    sp.id,
    s.id,
    CASE WHEN s.type = 'package' THEN true ELSE false END
FROM service_packages sp
CROSS JOIN services s
WHERE sp.name = 'Standard Package';

-- 4. Назначить пакет сессии
UPDATE photo_sessions
SET service_package_id = (SELECT id FROM service_packages WHERE name = 'Standard Package')
WHERE id = 'session-uuid';
```

## Тестирование

### Проверка структуры

```sql
-- Проверить, что сессия имеет пакет
SELECT id, name, service_package_id 
FROM photo_sessions 
WHERE id = 'session-uuid';

-- Проверить услуги в пакете
SELECT 
    ps.name as session_name,
    sp.name as package_name,
    s.name as service_name,
    s.price,
    sps.is_default,
    s.type
FROM photo_sessions ps
JOIN service_packages sp ON ps.service_package_id = sp.id
JOIN service_package_services sps ON sp.id = sps.service_package_id
JOIN services s ON sps.service_id = s.id
WHERE ps.id = 'session-uuid';
```

### Ожидаемый результат API

```json
{
  "sessionId": "session-uuid",
  "sessionName": "Wedding Photoshoot",
  "services": [
    {
      "id": "service-uuid-1",
      "name": "Весь архив",
      "description": "Все фотографии",
      "price": 2500.0,
      "isDefault": true,
      "type": "package",
      "photoCount": null,
      "isActive": true
    },
    {
      "id": "service-uuid-2",
      "name": "Цифровая копия",
      "description": "Одна фотография",
      "price": 150.0,
      "isDefault": false,
      "type": "digital",
      "photoCount": 1,
      "isActive": true
    }
  ],
  "defaultService": {
    "id": "service-uuid-1",
    "name": "Весь архив",
    "price": 2500.0,
    "isDefault": true
  },
  "currency": "RUB",
  "mainUrl": "https://staging.pixorasoft.ru"
}
```

## Что нужно проверить

### 1. База данных Pixora

- [ ] Таблица `service_packages` существует
- [ ] Таблица `services` существует
- [ ] Таблица `service_package_services` существует
- [ ] Тестовая сессия имеет `service_package_id`
- [ ] Пакет имеет связанные услуги
- [ ] Хотя бы одна услуга имеет `is_default = true` в `service_package_services`

### 2. API Endpoint

```bash
# Тест запроса
curl http://localhost:8000/api/v1/sessions/{session-id}/services

# Должен вернуть массив services
```

### 3. Frontend

- [ ] Открыть страницу сессии
- [ ] Проверить консоль браузера на ошибки
- [ ] Убедиться, что цены загружаются
- [ ] Проверить, что price badges отображаются

## Возможные проблемы

### Проблема: "Services not available"

**Причины:**
1. Сессия не имеет `service_package_id`
2. Пакет не существует
3. Пакет не имеет связанных услуг
4. Все услуги `is_active = false`

**Решение:**
```sql
-- Проверить service_package_id
SELECT service_package_id FROM photo_sessions WHERE id = 'session-uuid';

-- Если NULL, назначить пакет
UPDATE photo_sessions 
SET service_package_id = 'package-uuid' 
WHERE id = 'session-uuid';
```

### Проблема: SQL ошибка при запросе

**Причины:**
1. Таблицы не существуют
2. Неправильные имена полей
3. Отсутствуют индексы

**Решение:**
Проверить структуру таблиц в базе Pixora и убедиться, что она соответствует описанию в `docs/DATABASE_SCHEMA_SERVICES.md`

## Миграция данных (если нужно)

Если в Pixora уже есть данные в старом формате, может потребоваться миграция:

```sql
-- Создать пакет для каждой студии
INSERT INTO service_packages (id, name, studio_id, is_active)
SELECT DISTINCT 
    gen_random_uuid(),
    'Default Package',
    studio_id,
    true
FROM photo_sessions;

-- Создать стандартные услуги
INSERT INTO services (id, name, price, type, is_active)
VALUES 
    (gen_random_uuid(), 'Цифровая копия', 150.00, 'digital', true),
    (gen_random_uuid(), 'Весь архив', 2500.00, 'package', true);

-- Связать услуги с пакетами
-- (детали зависят от конкретной структуры данных)
```

## Документация

Полная документация по схеме базы данных:
- `docs/DATABASE_SCHEMA_SERVICES.md` - структура таблиц, примеры, SQL-запросы

Документация по интеграции:
- `docs/REAL_TIME_PRICING_SUMMARY.md` - архитектура интеграции
- `docs/PRICING_TESTING_CHECKLIST.md` - чеклист тестирования
- `docs/PRICING_QUICK_START.md` - быстрый старт

## Статус

✅ **Код обновлен и закоммичен**  
✅ **Документация обновлена**  
⏳ **Требуется тестирование с реальной БД Pixora**

---

**Дата:** 2026-02-20  
**Версия:** 1.0  
**Коммит:** df5c8aa
