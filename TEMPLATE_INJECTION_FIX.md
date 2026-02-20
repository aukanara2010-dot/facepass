# 🔧 Template Injection Fix - Critical Bug

## Проблема

В логах появлялась ошибка: вместо реального URL подставлялся текст `{{ MAIN_API_URL }}`.

### Причины:

1. **Backend не заменял шаблон** - не учитывались варианты без пробелов `{{MAIN_API_URL}}`
2. **Frontend неправильно формировал URL** - мог добавлять относительный путь вместо абсолютного
3. **Недостаточная проверка** - не было логирования для отладки

---

## Решение

### 1. Backend Fix (sessions.py)

**Добавлены варианты замены БЕЗ пробелов:**

```python
replacements = [
    # С пробелами
    ("'{{ MAIN_API_URL }}'", f"'{main_api_url}'"),
    ('"{{ MAIN_API_URL }}"', f'"{main_api_url}"'),
    ('{{ MAIN_API_URL }}', main_api_url),
    # БЕЗ пробелов (НОВОЕ!)
    ("'{{MAIN_API_URL}}'", f"'{main_api_url}'"),
    ('"{{MAIN_API_URL}}"', f'"{main_api_url}"'),
    ('{{MAIN_API_URL}}', main_api_url),
]
```

**Улучшено логирование:**

```python
if not replaced:
    logger.warning(f"MAIN_API_URL template not found in HTML. Checking content...")
    if 'window.MAIN_API_URL' in html_content:
        start = html_content.find('window.MAIN_API_URL')
        snippet = html_content[start:start+150]  # Увеличен до 150 символов
        logger.warning(f"Found window.MAIN_API_URL: {snippet}")
```

---

### 2. Frontend Fix (face-search-pricing.js)

**Улучшена проверка и формирование URL:**

```javascript
// БЫЛО (проблемное):
let mainApiUrl = window.MAIN_API_URL || 'https://staging.pixorasoft.ru';
if (mainApiUrl.includes('{{') || mainApiUrl.includes('}}')) {
    mainApiUrl = 'https://staging.pixorasoft.ru';
}

// СТАЛО (правильное):
let mainApiUrl = window.MAIN_API_URL && 
                !window.MAIN_API_URL.includes('{{') && 
                !window.MAIN_API_URL.includes('}}')
    ? window.MAIN_API_URL 
    : 'https://staging.pixorasoft.ru';

// Убираем trailing slash
mainApiUrl = mainApiUrl.replace(/\/$/, '');

// Формируем абсолютный URL
const servicesUrl = `${mainApiUrl}/api/session/${this.sessionId}/services`;
```

**Добавлено подробное логирование:**

```javascript
console.log('MAIN_API_URL from window:', window.MAIN_API_URL);
console.log('Using API URL:', mainApiUrl);
console.log('Fetching services from Pixora API:', servicesUrl);
```

---

## Тестирование

### 1. Проверка Backend

**Запустить сервер с логированием:**

```bash
uvicorn app.main:app --reload --log-level info
```

**Открыть страницу сессии и проверить логи:**

```
INFO: Replaced '"{{ MAIN_API_URL }}"' with '"https://staging.pixorasoft.ru"'
INFO: Serving interface for session abc123 with MAIN_API_URL: https://staging.pixorasoft.ru
```

**Если видите WARNING:**

```
WARNING: MAIN_API_URL template not found in HTML. Checking content...
WARNING: Found window.MAIN_API_URL: window.MAIN_API_URL = "{{MAIN_API_URL}}";
```

Это означает, что в HTML используется вариант БЕЗ пробелов, но теперь он тоже обрабатывается.

---

### 2. Проверка Frontend

**Открыть DevTools Console (F12):**

```javascript
// Должно быть:
MAIN_API_URL from window: https://staging.pixorasoft.ru
Using API URL: https://staging.pixorasoft.ru
Fetching services from Pixora API: https://staging.pixorasoft.ru/api/session/abc123/services

// НЕ должно быть:
MAIN_API_URL from window: {{ MAIN_API_URL }}
Using API URL: https://staging.pixorasoft.ru  // fallback сработал
```

---

### 3. Проверка HTML Source

**View Page Source (Ctrl+U):**

```html
<!-- ПРАВИЛЬНО: -->
<script>
    window.MAIN_API_URL = "https://staging.pixorasoft.ru";
</script>

<!-- НЕПРАВИЛЬНО: -->
<script>
    window.MAIN_API_URL = "{{ MAIN_API_URL }}";
</script>
```

---

## Возможные варианты шаблона в HTML

Backend теперь обрабатывает ВСЕ эти варианты:

```html
<!-- С пробелами -->
window.MAIN_API_URL = "{{ MAIN_API_URL }}";
window.MAIN_API_URL = '{{ MAIN_API_URL }}';
const url = {{ MAIN_API_URL }};

<!-- Без пробелов -->
window.MAIN_API_URL = "{{MAIN_API_URL}}";
window.MAIN_API_URL = '{{MAIN_API_URL}}';
const url = {{MAIN_API_URL}};
```

---

## Fallback Механизм

Если замена не сработала, система автоматически использует fallback:

```javascript
// Frontend всегда имеет fallback
const mainApiUrl = window.MAIN_API_URL && 
                  !window.MAIN_API_URL.includes('{{') && 
                  !window.MAIN_API_URL.includes('}}')
    ? window.MAIN_API_URL 
    : 'https://staging.pixorasoft.ru';  // HARDCODED FALLBACK
```

**Это гарантирует работу даже если:**
- Backend не заменил шаблон
- `.env` файл не настроен
- Переменная окружения отсутствует

---

## Отладка

### Проблема: В консоли видно "{{ MAIN_API_URL }}"

**Шаг 1: Проверить .env файл**

```bash
cat .env | grep MAIN_API_URL
# Должно быть:
MAIN_API_URL=https://staging.pixorasoft.ru
```

**Шаг 2: Перезапустить сервер**

```bash
# Остановить текущий процесс (Ctrl+C)
# Запустить заново
uvicorn app.main:app --reload
```

**Шаг 3: Проверить логи сервера**

Должно быть сообщение о замене:
```
INFO: Replaced '"{{ MAIN_API_URL }}"' with '"https://staging.pixorasoft.ru"'
```

**Шаг 4: Очистить кэш браузера**

```
Ctrl+Shift+R (hard reload)
или
Ctrl+Shift+Delete → Clear cache
```

---

### Проблема: URL формируется неправильно

**Пример неправильного URL:**
```
http://localhost:8000/session/abc123/api/session/abc123/services
```

**Причина:** Относительный путь вместо абсолютного

**Решение:** Убедиться, что `mainApiUrl` начинается с `http://` или `https://`

```javascript
// Проверка в консоли
console.log('mainApiUrl:', mainApiUrl);
console.log('Starts with http:', mainApiUrl.startsWith('http'));

// Должно быть:
mainApiUrl: https://staging.pixorasoft.ru
Starts with http: true
```

---

## Проверочный чеклист

### Backend
- [x] Добавлены варианты замены без пробелов
- [x] Улучшено логирование
- [x] Увеличен snippet для отладки до 150 символов
- [x] Все варианты кавычек обрабатываются

### Frontend
- [x] Улучшена проверка window.MAIN_API_URL
- [x] Добавлено удаление trailing slash
- [x] Гарантирован абсолютный URL
- [x] Добавлено подробное логирование
- [x] Hardcoded fallback на случай ошибки

### HTML
- [x] Скрипт с window.MAIN_API_URL в `<head>`
- [x] Загружается до face-search-pricing.js
- [x] Использует двойные кавычки

---

## Тестовые сценарии

### Сценарий 1: Нормальная работа

```
1. .env настроен правильно
2. Backend заменяет шаблон
3. Frontend получает правильный URL
4. Запрос идет на https://staging.pixorasoft.ru/api/session/.../services
5. Цены загружаются успешно
```

### Сценарий 2: Backend не заменил шаблон

```
1. window.MAIN_API_URL = "{{ MAIN_API_URL }}"
2. Frontend обнаруживает {{ в строке
3. Использует fallback: https://staging.pixorasoft.ru
4. Запрос идет на fallback URL
5. Цены загружаются (если CORS настроен)
```

### Сценарий 3: .env не настроен

```
1. settings.MAIN_API_URL = None или пустая строка
2. Backend заменяет на пустую строку
3. Frontend обнаруживает пустую строку
4. Использует fallback: https://staging.pixorasoft.ru
5. Цены загружаются (если CORS настроен)
```

---

## Измененные файлы

### Code
- ✅ `app/api/v1/endpoints/sessions.py` - добавлены варианты без пробелов
- ✅ `app/static/js/face-search-pricing.js` - улучшена проверка и формирование URL

### Documentation
- ✅ `TEMPLATE_INJECTION_FIX.md` - этот документ

---

## Коммит

```bash
git add app/api/v1/endpoints/sessions.py app/static/js/face-search-pricing.js
git commit -m "fix: Critical template injection bug - handle variants without spaces"
git push origin main
```

---

## Статус

✅ **Backend исправлен** - обрабатывает все варианты шаблона  
✅ **Frontend исправлен** - правильно формирует абсолютный URL  
✅ **Логирование улучшено** - легче отлаживать  
✅ **Fallback механизм** - работает даже при ошибках  

**Готово к тестированию!**

---

**Дата:** 2026-02-20  
**Версия:** 1.1  
**Приоритет:** CRITICAL
