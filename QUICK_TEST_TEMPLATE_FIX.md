# ⚡ Quick Test: Template Injection Fix

## 🎯 Цель
Проверить, что `{{ MAIN_API_URL }}` правильно заменяется на реальный URL.

---

## 1️⃣ Проверка Backend (30 секунд)

### Запустить сервер с логами:
```bash
uvicorn app.main:app --reload --log-level info
```

### Открыть страницу сессии:
```
http://localhost:8000/api/v1/sessions/{test-session-id}/interface
```

### Проверить логи сервера:

✅ **УСПЕХ - должно быть:**
```
INFO: Replaced '"{{ MAIN_API_URL }}"' with '"https://staging.pixorasoft.ru"'
INFO: Serving interface for session abc123 with MAIN_API_URL: https://staging.pixorasoft.ru
```

❌ **ОШИБКА - если видите:**
```
WARNING: MAIN_API_URL template not found in HTML
WARNING: Found window.MAIN_API_URL: window.MAIN_API_URL = "{{ MAIN_API_URL }}";
```

**Решение:** Проверить `.env` файл и перезапустить сервер.

---

## 2️⃣ Проверка Frontend (30 секунд)

### Открыть DevTools Console (F12):

✅ **УСПЕХ - должно быть:**
```javascript
MAIN_API_URL from window: https://staging.pixorasoft.ru
Using API URL: https://staging.pixorasoft.ru
Fetching services from Pixora API: https://staging.pixorasoft.ru/api/session/abc123/services
```

❌ **ОШИБКА - если видите:**
```javascript
MAIN_API_URL from window: {{ MAIN_API_URL }}
Using API URL: https://staging.pixorasoft.ru  // fallback
```

**Решение:** Backend не заменил шаблон, но fallback работает.

---

## 3️⃣ Проверка HTML Source (30 секунд)

### View Page Source (Ctrl+U):

### Найти строку с `window.MAIN_API_URL`:

✅ **УСПЕХ:**
```html
<script>
    window.MAIN_API_URL = "https://staging.pixorasoft.ru";
</script>
```

❌ **ОШИБКА:**
```html
<script>
    window.MAIN_API_URL = "{{ MAIN_API_URL }}";
</script>
```

---

## 4️⃣ Проверка Network Tab (1 минута)

### Открыть DevTools → Network:

1. Загрузить селфи
2. Выполнить поиск
3. Найти запрос к `/services`

✅ **УСПЕХ - URL должен быть:**
```
https://staging.pixorasoft.ru/api/session/abc123/services
```

❌ **ОШИБКА - если URL:**
```
http://localhost:8000/session/abc123/api/session/abc123/services  ← Относительный путь!
{{ MAIN_API_URL }}/api/session/abc123/services  ← Шаблон не заменен!
```

---

## 🔧 Быстрые исправления

### Проблема 1: Backend не заменяет шаблон

```bash
# Проверить .env
cat .env | grep MAIN_API_URL

# Должно быть:
MAIN_API_URL=https://staging.pixorasoft.ru

# Если нет, добавить:
echo "MAIN_API_URL=https://staging.pixorasoft.ru" >> .env

# Перезапустить сервер
```

### Проблема 2: Кэш браузера

```
Ctrl+Shift+R  (hard reload)
или
Ctrl+Shift+Delete → Clear cache
```

### Проблема 3: Fallback не работает

Проверить в `face-search-pricing.js`:
```javascript
const mainApiUrl = window.MAIN_API_URL && 
                  !window.MAIN_API_URL.includes('{{') && 
                  !window.MAIN_API_URL.includes('}}')
    ? window.MAIN_API_URL 
    : 'https://staging.pixorasoft.ru';  // ← Этот URL должен быть правильным
```

---

## ✅ Чеклист успешного теста

- [ ] Логи сервера показывают успешную замену
- [ ] Console показывает правильный URL (без `{{`)
- [ ] Page Source показывает замененный URL
- [ ] Network tab показывает запрос на правильный домен
- [ ] Цены загружаются и отображаются

---

## 🚨 Если ничего не помогло

1. **Проверить версию кода:**
   ```bash
   git log --oneline -1
   # Должно быть: 3863244 fix: Critical template injection bug
   ```

2. **Проверить файлы:**
   ```bash
   grep -n "{{MAIN_API_URL}}" app/api/v1/endpoints/sessions.py
   # Должно найти строку с заменой без пробелов
   ```

3. **Полная перезагрузка:**
   ```bash
   # Остановить сервер
   # Очистить кэш браузера
   # Перезапустить сервер
   uvicorn app.main:app --reload --log-level debug
   ```

---

**Время теста:** ~2 минуты  
**Критичность:** HIGH  
**Статус:** FIXED ✅
