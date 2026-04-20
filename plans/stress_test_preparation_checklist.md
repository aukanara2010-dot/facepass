# Чек-лист подготовки сервера к суточному стресс-тесту FacePass

## Общие параметры теста
- **Продолжительность**: 24 часа
- **Нагрузка**: 18 точек × 80,000 фото на точку = 1,440,000 фото за тест
- **Скорость**: 1 задача каждые 1.08 секунд на точку (≈16.67 задач/сек общая нагрузка)
- **Оборудование**: Сервер с 16 ядрами CPU и 32 ГБ ОЗУ

## 1. Проверка зависимостей

### Python библиотеки

```bash
# Активация виртуального окружения
cd ~/facepass
source venv/bin/activate

# Проверка наличия необходимых библиотек
pip list | grep -E "boto3|psutil|redis|pandas|rich"

# Установка недостающих библиотек (если необходимо)
pip install boto3 psutil redis pandas rich
```

### Подготовка тестовых изображений

```bash
# Проверка наличия директории для тестовых изображений
mkdir -p ~/facepass/test_images

# Проверка наличия файла test_image.jpg в корне проекта
ls -la ~/facepass/test_image.jpg

# Если нет достаточного количества тестовых изображений:
ls -la ~/facepass/test_images/ | wc -l
```

**Важно**: Для реалистичного тестирования рекомендуется использовать **несколько разных изображений лиц** (5-10 различных фото). Это создаст более реалистичную нагрузку на базу данных, т.к. при использовании одного и того же изображения будет постоянно вычисляться один и тот же вектор, что не нагружает индексы должным образом.

**Рекомендация**: Загрузите в директорию `~/facepass/test_images/` несколько различных фотографий с лицами и убедитесь, что скрипт стресс-тестирования настроен на их случайный выбор.

## 2. Проверка инфраструктуры (Health Check)

### Redis

```bash
# Проверка соединения с Redis
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

# Альтернативный метод (через Python)
python -c "
import redis
from core.config import get_settings
settings = get_settings()
r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, 
                password=settings.REDIS_PASSWORD, db=settings.REDIS_DB)
print(f'Redis connection: {r.ping()}')
"
```

### S3

```bash
# Убедимся, что переменные окружения загружены из .env
cd ~/facepass
export $(grep -v '^#' .env | xargs)

# Проверка соединения с S3
python -c "
import boto3
from core.config import get_settings
settings = get_settings()

# Создание S3 клиента
s3_client = boto3.client(
    's3',
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    region_name=settings.S3_REGION
)

# Тестовая операция - создание временного объекта
test_key = f'{settings.S3_ENV_PREFIX}/test/health_check.txt'
s3_client.put_object(
    Bucket=settings.S3_BUCKET,
    Key=test_key,
    Body=b'Health check test'
)

# Проверка, что объект был создан
response = s3_client.head_object(Bucket=settings.S3_BUCKET, Key=test_key)
print(f'S3 connection: OK (Created test object, status code: {response[\"ResponseMetadata\"][\"HTTPStatusCode\"]})')

# Удаление тестового объекта
s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=test_key)
"
```

### PostgreSQL

```bash
# Проверка соединения с PostgreSQL
python -c "
from core.database import engine
import sqlalchemy as sa

with engine.connect() as connection:
    result = connection.execute(sa.text('SELECT 1'))
    print(f'PostgreSQL connection: OK (Result: {result.fetchone()[0]})')
"
```

## 3. Очистка "хвостов"

### Сброс задач в Celery

```bash
# Очистка всех очередей Celery
cd ~/facepass
celery -A core.celery_app purge -f
```

### Очистка кэша Redis

**Внимание**: Следующие команды удалят данные из Redis. Используйте только если это безопасно для текущей работы.

```bash
# Вариант 1: Более безопасный - удаление только ключей, связанных с Celery
redis-cli -h $REDIS_HOST -p $REDIS_PORT KEYS "celery*" | xargs redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL

# Вариант 2: Полная очистка Redis (использовать с осторожностью!)
# redis-cli -h $REDIS_HOST -p $REDIS_PORT FLUSHDB
```

## 4. Тюнинг PM2 (Concurrency)

### Проверка текущих настроек PM2

```bash
# Проверка текущих настроек PM2
pm2 show facepass-worker
```

### Оптимальные настройки для стресс-теста

Для сервера с 16 ядрами, оптимальные настройки:
- Для индексации: 12 воркеров (75% ядер)
- Для поиска: 4 воркера (25% ядер)

```bash
# Перезапуск воркеров с оптимальными настройками
pm2 stop facepass-worker
pm2 start celery -n facepass-worker -- -A core.celery_app worker --concurrency=12 -l INFO
```

## 5. Настройка логирования

### Проверка свободного места на диске

```bash
# Проверка свободного места
df -h /

# Проверка размера текущих лог-файлов
du -sh ~/.pm2/logs/
```

### Настройка ротации логов PM2

```bash
# Очистка текущих лог-файлов PM2
pm2 flush

# Настройка ротации логов (если еще не настроена)
cat > ~/.pm2/log-rotate.json << EOL
{
  "max_size": "100M",
  "retain": 5,
  "compress": true,
  "dateFormat": "YYYY-MM-DD_HH-mm-ss",
  "workerInterval": 30,
  "rotateInterval": "0 0 * * *"
}
EOL

pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 100M
pm2 set pm2-logrotate:retain 5
pm2 set pm2-logrotate:compress true
```

### Настройка логирования для скрипта стресс-теста

```bash
# Создание директории для логов стресс-теста
mkdir -p ~/facepass/logs/stress_test

# Проверка и установка корректных прав доступа
# Важно! Пользователь, под которым запущен PM2, должен иметь права на запись
sudo chown -R $(whoami):$(whoami) ~/facepass/logs/stress_test
chmod -R 755 ~/facepass/logs/stress_test

# Проверка прав на запись
touch ~/facepass/logs/stress_test/test_write.log
if [ $? -eq 0 ]; then
  echo "Права на запись в директорию логов установлены корректно"
  rm ~/facepass/logs/stress_test/test_write.log
else
  echo "ОШИБКА: Невозможно записать в директорию логов"
fi

# Убедитесь, что скрипт стресс-теста использует настроенный логгер
```

## 6. Финальная проверка

### Основной чек-лист готовности

| Компонент | Статус | Описание |
|-----------|--------|----------|
| Python зависимости | ✅/❌ | boto3, psutil, redis, pandas/rich |
| test_image.jpg | ✅/❌ | Наличие тестового изображения |
| Redis соединение | ✅/❌ | PING успешен |
| S3 соединение | ✅/❌ | Создание/удаление объекта |
| PostgreSQL соединение | ✅/❌ | SELECT 1 успешен |
| Очистка задач Celery | ✅/❌ | Очереди пусты |
| PM2 concurrency | ✅/❌ | Установлено 12 воркеров |
| Свободное место | ✅/❌ | > 5 ГБ на основном разделе |
| Логирование | ✅/❌ | Настроена ротация логов |

## 7. Запуск стресс-теста

После успешного прохождения всех проверок, запустите стресс-тест в фоновом режиме:

```bash
cd ~/facepass
nohup python stress_marathon.py > logs/stress_test/marathon_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo $! > logs/stress_test/marathon.pid
```

## Мониторинг теста

Для мониторинга в процессе теста:

```bash
# Мониторинг лог-файла в реальном времени
tail -f logs/stress_test/marathon_*.log

# Проверка статуса процесса
ps -p $(cat logs/stress_test/marathon.pid)

# Мониторинг системных ресурсов
htop

# Мониторинг очереди Redis
watch -n 10 "redis-cli -h $REDIS_HOST -p $REDIS_PORT LLEN celery"
```

## Остановка теста (если необходимо)

```bash
kill $(cat logs/stress_test/marathon.pid)