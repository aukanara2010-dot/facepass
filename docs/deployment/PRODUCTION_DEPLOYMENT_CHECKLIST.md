# ✅ FacePass Production Deployment Checklist

## 🎯 Обзор изменений

FacePass успешно настроен для работы на домене `facepass.pixorasoft.ru` с красивыми URL и полной интеграцией с Pixora Store.

## 📋 Выполненные изменения

### ✅ 1. Обновление CORS настроек
```python
allow_origins=[
    "https://facepass.pixorasoft.ru",      # Основной домен FacePass
    "https://staging.pixorasoft.ru",       # Staging Pixora для покупок  
    "https://pixorasoft.ru",               # Основной сайт Pixora
    "http://localhost:3000",               # Локальная разработка
    "http://localhost:8000",               # Локальная разработка
]
```

### ✅ 2. Красивые публичные URL
**Было:** `/api/v1/sessions/{id}/interface`  
**Стало:** `/session/{session_id}`

```python
@app.get("/session/{session_id}")
async def public_session_interface(session_id: str):
    # Валидация сессии + инжекция мета-тегов
```

### ✅ 3. Относительные пути в JavaScript
```javascript
// Было:
fetch('http://localhost:8000/api/v1/sessions/validate/...')

// Стало:
fetch('/api/v1/sessions/validate/...')
```

### ✅ 4. OpenGraph мета-теги
```html
<meta property="og:title" content="Найти фото - {session_name} | FacePass">
<meta property="og:description" content="Найдите свои фотографии с фотосессии '{session_name}'">
<meta property="og:image" content="https://facepass.pixorasoft.ru/static/images/facepass-og.jpg">
<meta property="og:url" content="https://facepass.pixorasoft.ru/session/{session_id}">
```

### ✅ 5. Интеграция с Pixora Store
```javascript
const purchaseUrl = `https://staging.pixorasoft.ru/session/${this.sessionId}?selected=${selectedFileNames}`;
```

### ✅ 6. Брендинг и иконки
- Логотип: `/static/images/facepass-logo.svg`
- Favicon: `/static/images/favicon.svg`
- OpenGraph изображение: `/static/images/facepass-og.jpg`

## 🚀 Инструкции по развертыванию

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y python3 python3-pip python3-venv nginx postgresql redis-server

# Создание пользователя для приложения
sudo useradd -m -s /bin/bash facepass
sudo usermod -aG sudo facepass
```

### 2. Клонирование и настройка проекта

```bash
# Переключение на пользователя facepass
sudo su - facepass

# Клонирование репозитория
git clone https://github.com/pixora/facepass.git
cd facepass

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

```bash
# Копирование и настройка .env
cp .env.example .env
nano .env
```

**Обязательные изменения в .env:**
```env
# Домены
DOMAIN=facepass.pixorasoft.ru
STAGING_DOMAIN=staging.pixorasoft.ru

# База данных
POSTGRES_USER=facepass_prod
POSTGRES_PASSWORD=secure_password_here
MAIN_DB_HOST=localhost

# S3 (реальные ключи)
S3_ACCESS_KEY=real_access_key
S3_SECRET_KEY=real_secret_key
S3_BUCKET=facepass-production

# Внешняя база Pixora (проверить актуальность)
MAIN_APP_DATABASE_URL=postgresql://postgres:Gqmkcp2HUcgbeWlScZN1GUvkpxdqsTFX@155.212.216.176:5432/postgres
```

### 4. Настройка базы данных

```bash
# Создание баз данных
sudo -u postgres createdb facepass_main
sudo -u postgres createdb facepass_vector

# Установка pgvector
sudo -u postgres psql -d facepass_vector -c "CREATE EXTENSION vector;"

# Инициализация схемы
python scripts/init_db.py
```

### 5. Настройка Nginx

```bash
sudo nano /etc/nginx/sites-available/facepass.pixorasoft.ru
```

```nginx
server {
    listen 80;
    server_name facepass.pixorasoft.ru;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name facepass.pixorasoft.ru;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/facepass.pixorasoft.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/facepass.pixorasoft.ru/privkey.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Static Files
    location /static/ {
        alias /home/facepass/facepass/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # CORS for static files
        add_header Access-Control-Allow-Origin "*";
    }
    
    # Main Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health Check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

```bash
# Активация конфигурации
sudo ln -s /etc/nginx/sites-available/facepass.pixorasoft.ru /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. SSL сертификат

```bash
# Установка Certbot
sudo apt install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d facepass.pixorasoft.ru

# Автообновление
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 7. Systemd сервис

```bash
sudo nano /etc/systemd/system/facepass.service
```

```ini
[Unit]
Description=FacePass FastAPI Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=facepass
Group=facepass
WorkingDirectory=/home/facepass/facepass
Environment=PATH=/home/facepass/facepass/venv/bin
ExecStart=/home/facepass/facepass/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/facepass/facepass

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable facepass
sudo systemctl start facepass
sudo systemctl status facepass
```

### 8. Celery Worker

```bash
sudo nano /etc/systemd/system/facepass-worker.service
```

```ini
[Unit]
Description=FacePass Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=facepass
Group=facepass
WorkingDirectory=/home/facepass/facepass
Environment=PATH=/home/facepass/facepass/venv/bin
ExecStart=/home/facepass/facepass/venv/bin/celery -A workers.celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable facepass-worker
sudo systemctl start facepass-worker
```

## 🔍 Тестирование продакшена

### 1. Локальное тестирование перед деплоем

```bash
# Запуск тестов
python test_production_urls.py
python test_session_endpoints_simple.py
python test_db_connection.py
```

### 2. Тестирование после деплоя

```bash
# Проверка доступности
curl -I https://facepass.pixorasoft.ru/

# Тестирование сессии
curl -I https://facepass.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee

# Проверка API
curl https://facepass.pixorasoft.ru/api/v1/sessions/validate/1788875f-fc71-49d6-a9fa-a060e3ee6fee

# Проверка статических файлов
curl -I https://facepass.pixorasoft.ru/static/js/face-search.js
```

### 3. Функциональное тестирование

1. **Откройте в браузере:** `https://facepass.pixorasoft.ru/session/1788875f-fc71-49d6-a9fa-a060e3ee6fee`
2. **Проверьте:** Загрузка интерфейса, мета-теги, favicon
3. **Протестируйте:** Камеру, загрузку файлов, поиск лиц
4. **Проверьте:** Переход на покупку в Pixora Store

## 📊 Мониторинг и логи

### 1. Логи приложения

```bash
# Логи FastAPI
sudo journalctl -u facepass -f

# Логи Celery
sudo journalctl -u facepass-worker -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Мониторинг производительности

```bash
# Статус сервисов
sudo systemctl status facepass facepass-worker nginx postgresql redis

# Использование ресурсов
htop
df -h
free -h
```

### 3. Настройка алертов

```bash
# Простой скрипт мониторинга
nano /home/facepass/monitor.sh
```

```bash
#!/bin/bash
# Проверка доступности FacePass

URL="https://facepass.pixorasoft.ru/"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $STATUS -ne 200 ]; then
    echo "FacePass is down! Status: $STATUS" | mail -s "FacePass Alert" admin@pixorasoft.ru
fi
```

```bash
chmod +x /home/facepass/monitor.sh
# Добавить в crontab: */5 * * * * /home/facepass/monitor.sh
```

## 🔒 Безопасность

### 1. Firewall

```bash
# UFW настройка
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 2. Fail2Ban

```bash
sudo apt install -y fail2ban

sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
```

### 3. Регулярные обновления

```bash
# Автоматические обновления безопасности
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 📈 Оптимизация производительности

### 1. PostgreSQL

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

```ini
# Оптимизация для FacePass
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 100
```

### 2. Redis

```bash
sudo nano /etc/redis/redis.conf
```

```ini
# Оптимизация Redis
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## ✅ Финальный чек-лист

### Перед запуском в продакшен:

- [ ] Домен facepass.pixorasoft.ru настроен и доступен
- [ ] SSL сертификат установлен и работает
- [ ] Все переменные окружения настроены
- [ ] Базы данных созданы и инициализированы
- [ ] Подключение к внешней Pixora DB работает
- [ ] Nginx конфигурация активна
- [ ] Systemd сервисы запущены и работают
- [ ] Статические файлы доступны
- [ ] CORS настроен для всех доменов
- [ ] Мониторинг и логирование настроены
- [ ] Резервное копирование настроено
- [ ] Тестирование пройдено успешно

### После запуска:

- [ ] Интерфейс загружается по красивому URL
- [ ] Мета-теги отображаются корректно
- [ ] Поиск лиц работает
- [ ] Переход на покупку функционирует
- [ ] Мобильная версия работает
- [ ] Производительность соответствует требованиям

## 🎉 Готово к продакшену!

FacePass полностью настроен и готов к развертыванию на `facepass.pixorasoft.ru`. Все компоненты интегрированы, URL красивые, мета-теги настроены, и система готова к работе с реальными пользователями.

**Основные URL в продакшене:**
- Интерфейс: `https://facepass.pixorasoft.ru/session/{session_id}`
- API: `https://facepass.pixorasoft.ru/api/v1/...`
- Покупка: `https://staging.pixorasoft.ru/session/{session_id}?selected=...`