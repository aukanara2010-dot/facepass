# FacePass v2.0 - Deployment Checklist

## Pre-Deployment Checklist

### 1. Prerequisites ✅

#### Infrastructure
- [ ] Docker и Docker Compose установлены
- [ ] Минимум 4GB RAM доступно
- [ ] Минимум 10GB свободного места на диске
- [ ] PostgreSQL 16+ с pgvector extension
- [ ] Redis 7+
- [ ] SSL/TLS сертификаты (для production)

#### Access & Credentials
- [ ] Доступ к production серверу (SSH)
- [ ] Доступ к S3 storage (access key, secret key)
- [ ] Доступ к PostgreSQL (admin credentials)
- [ ] Доступ к Docker registry (если используется)

#### Networking
- [ ] Firewall rules настроены
- [ ] Ports открыты: 8000 (API), 5432 (PostgreSQL), 6379 (Redis), 9090 (Prometheus)
- [ ] DNS records настроены
- [ ] Load balancer настроен (если используется)

---

## Configuration Checklist

### 2. Environment Variables ✅

Создайте production `.env` файл:

```bash
# Application
APP_NAME=FacePass
APP_VERSION=2.0.0
DEBUG=False

# Database
POSTGRES_USER=facepass_prod_user
POSTGRES_PASSWORD=<SECURE_PASSWORD>
POSTGRES_DB=facepass_vector
POSTGRES_HOST=db_vector
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# S3 Storage
S3_ENDPOINT=https://s3.beget.com
S3_ACCESS_KEY=<YOUR_ACCESS_KEY>
S3_SECRET_KEY=<YOUR_SECRET_KEY>
S3_BUCKET=facepass-images
S3_REGION=ru-1

# Security
API_KEYS=<GENERATE_SECURE_KEYS>
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Face Recognition
FACE_SIMILARITY_THRESHOLD=0.5
FACE_DETECTION_THRESHOLD=0.6
EMBEDDING_DIMENSION=512
```

**Checklist:**
- [ ] Все required переменные заполнены
- [ ] `DEBUG=False` для production
- [ ] Secure passwords сгенерированы (минимум 32 символа)
- [ ] API keys сгенерированы (используйте `openssl rand -hex 32`)
- [ ] CORS origins настроены правильно
- [ ] S3 credentials проверены

### 3. Security Configuration ✅

#### API Keys
```bash
# Генерация secure API keys
openssl rand -hex 32  # Повторить для каждого ключа
```

- [ ] Минимум 3 API keys сгенерировано
- [ ] API keys сохранены в secure storage (Vault, AWS Secrets Manager)
- [ ] API keys добавлены в `.env`
- [ ] Старые/test keys удалены

#### SSL/TLS
- [ ] SSL сертификаты получены (Let's Encrypt или коммерческий CA)
- [ ] Сертификаты установлены на load balancer/reverse proxy
- [ ] HTTPS redirect настроен
- [ ] HTTP Strict Transport Security (HSTS) включен

#### Firewall
- [ ] Только необходимые ports открыты
- [ ] SSH доступ ограничен по IP
- [ ] Database ports закрыты для внешнего доступа
- [ ] Rate limiting на уровне firewall настроен

---

## Database Migration Checklist

### 4. Database Preparation ✅

#### Backup
```bash
# 1. Создать backup текущей БД
./scripts/backup_database.sh

# 2. Проверить backup
ls -lh backups/
```

- [ ] Backup создан успешно
- [ ] Backup файл скопирован в безопасное место
- [ ] Backup протестирован (restore на test environment)

#### Migration
```bash
# 1. Подключиться к БД
docker-compose exec db_vector psql -U facepass_user -d facepass_vector

# 2. Проверить текущую схему
\d face_embeddings

# 3. Выполнить миграцию
\i /code/scripts/migration_v2.sql

# 4. Проверить результат
\d face_embeddings
SELECT COUNT(*) FROM face_embeddings;
```

- [ ] Migration script проверен на staging
- [ ] Backup создан перед миграцией
- [ ] Migration выполнена успешно
- [ ] Данные проверены после миграции
- [ ] Indexes созданы корректно
- [ ] Vector index (IVFFlat) создан

#### Rollback Plan
- [ ] Rollback script протестирован на staging
- [ ] Процедура rollback документирована
- [ ] Команда знает, как выполнить rollback

---

## Deployment Steps

### 5. Staging Deployment ✅

#### Deploy на Staging
```bash
# 1. Clone repository
git clone <repository-url>
cd facepass

# 2. Checkout production branch
git checkout main

# 3. Copy production .env
cp .env.production .env

# 4. Build and start services
docker-compose build
docker-compose up -d

# 5. Check health
curl http://staging.facepass.com/api/v2/health
```

- [ ] Staging environment настроен
- [ ] Services запущены успешно
- [ ] Health check проходит
- [ ] Database migration выполнена
- [ ] Logs проверены (нет критических ошибок)

#### Smoke Tests на Staging
```bash
# 1. Health check
curl http://staging:8000/api/v2/health

# 2. Index test photo
curl -X POST "http://staging:8000/api/v2/index" \
  -H "X-API-Key: test-key" \
  -F "photo_id=test1" \
  -F "session_id=test-session" \
  -F "file=@test.jpg"

# 3. Search test
curl -X POST "http://staging:8000/api/v2/search" \
  -F "session_id=test-session" \
  -F "file=@selfie.jpg"

# 4. Check metrics
curl http://staging:8000/api/v2/metrics
```

- [ ] Health check возвращает 200 OK
- [ ] Indexing работает корректно
- [ ] Search возвращает результаты
- [ ] Metrics endpoint работает
- [ ] Authentication работает (401 без API key)
- [ ] Rate limiting работает

### 6. Production Deployment ✅

#### Pre-Deployment
- [ ] Staging tests пройдены успешно
- [ ] Team уведомлена о deployment
- [ ] Maintenance window запланирован (если нужен)
- [ ] Rollback plan готов

#### Deployment Process
```bash
# 1. SSH на production server
ssh user@production-server

# 2. Navigate to app directory
cd /opt/facepass

# 3. Pull latest code
git pull origin main

# 4. Backup current .env
cp .env .env.backup

# 5. Update .env with production values
nano .env

# 6. Build new images
docker-compose build

# 7. Stop old services
docker-compose down

# 8. Start new services
docker-compose up -d

# 9. Check health
curl http://localhost:8000/api/v2/health

# 10. Check logs
docker-compose logs -f app
```

- [ ] Code deployed успешно
- [ ] Services запущены
- [ ] Health check проходит
- [ ] Logs проверены
- [ ] No critical errors в logs

#### Post-Deployment Verification
```bash
# 1. Health check
curl https://facepass.yourdomain.com/api/v2/health

# 2. Metrics check
curl https://facepass.yourdomain.com/api/v2/metrics

# 3. Test indexing (с production API key)
curl -X POST "https://facepass.yourdomain.com/api/v2/index" \
  -H "X-API-Key: $PROD_API_KEY" \
  -F "photo_id=prod-test-1" \
  -F "session_id=prod-test-session" \
  -F "file=@test.jpg"

# 4. Test search
curl -X POST "https://facepass.yourdomain.com/api/v2/search" \
  -F "session_id=prod-test-session" \
  -F "file=@selfie.jpg"
```

- [ ] All endpoints responding
- [ ] HTTPS working correctly
- [ ] Authentication working
- [ ] Rate limiting working
- [ ] Metrics being collected
- [ ] Logs being written

---

## Monitoring Setup

### 7. Monitoring & Alerting ✅

#### Prometheus
```bash
# Access Prometheus
http://facepass.yourdomain.com:9090

# Check targets
http://facepass.yourdomain.com:9090/targets
```

- [ ] Prometheus scraping metrics
- [ ] All targets UP
- [ ] Metrics visible in Prometheus UI

#### Grafana (Optional)
- [ ] Grafana installed
- [ ] Prometheus data source configured
- [ ] Dashboards imported
- [ ] Alerts configured

#### Log Aggregation
- [ ] Logs forwarded to aggregation system (ELK, Loki, etc.)
- [ ] Log retention policy configured
- [ ] Log search working

#### Alerts
Configure alerts for:
- [ ] Service down (health check fails)
- [ ] High error rate (> 5%)
- [ ] High latency (p95 > 1s)
- [ ] Database connection issues
- [ ] Disk space low (< 10%)
- [ ] Memory usage high (> 80%)

---

## Performance Testing

### 8. Load Testing ✅

#### Basic Load Test
```bash
# Install Apache Bench
apt-get install apache2-utils

# Test search endpoint
ab -n 1000 -c 10 -p selfie.jpg -T 'multipart/form-data' \
  http://facepass.yourdomain.com/api/v2/search
```

- [ ] Load test executed
- [ ] Response times acceptable (p95 < 500ms)
- [ ] No errors under load
- [ ] Resource usage monitored

#### Stress Test
```bash
# Gradually increase load
ab -n 10000 -c 50 ...
ab -n 10000 -c 100 ...
ab -n 10000 -c 200 ...
```

- [ ] System handles expected load
- [ ] Graceful degradation under stress
- [ ] Auto-recovery after stress

---

## Backup & Recovery

### 9. Backup Strategy ✅

#### Automated Backups
```bash
# Setup cron job for daily backups
0 2 * * * /opt/facepass/scripts/backup_database.sh
```

- [ ] Automated backup script configured
- [ ] Backup schedule set (daily recommended)
- [ ] Backup retention policy defined (30 days recommended)
- [ ] Backups stored off-site
- [ ] Backup restoration tested

#### Recovery Procedure
```bash
# 1. Stop services
docker-compose down

# 2. Restore database
docker-compose exec db_vector psql -U user -d db < backup.sql

# 3. Start services
docker-compose up -d

# 4. Verify
curl http://localhost:8000/api/v2/health
```

- [ ] Recovery procedure documented
- [ ] Recovery tested on staging
- [ ] RTO (Recovery Time Objective) defined
- [ ] RPO (Recovery Point Objective) defined

---

## Documentation

### 10. Documentation Updates ✅

- [ ] README.md updated with production URLs
- [ ] API documentation accessible (/docs)
- [ ] Migration guide shared with Pixora team
- [ ] Runbook created for operations team
- [ ] Incident response plan documented
- [ ] Contact information updated

---

## Rollback Procedure

### 11. Rollback Plan ✅

#### If Deployment Fails

**Option 1: Rollback Code**
```bash
# 1. Stop new services
docker-compose down

# 2. Checkout previous version
git checkout <previous-tag>

# 3. Restore .env
cp .env.backup .env

# 4. Start old services
docker-compose up -d
```

**Option 2: Rollback Database**
```bash
# 1. Stop services
docker-compose down

# 2. Rollback database
docker-compose exec db_vector psql -U user -d db -f /code/scripts/rollback_v2.sql

# 3. Start services
docker-compose up -d
```

- [ ] Rollback procedure tested on staging
- [ ] Rollback can be executed in < 15 minutes
- [ ] Team trained on rollback procedure

---

## Post-Deployment

### 12. Post-Deployment Tasks ✅

#### Immediate (Day 1)
- [ ] Monitor logs for errors
- [ ] Monitor metrics (latency, error rate)
- [ ] Monitor resource usage (CPU, memory, disk)
- [ ] Verify all integrations working
- [ ] Collect feedback from Pixora team

#### Short-term (Week 1)
- [ ] Review performance metrics
- [ ] Optimize slow queries (if any)
- [ ] Adjust rate limits (if needed)
- [ ] Fine-tune monitoring alerts
- [ ] Document any issues encountered

#### Long-term (Month 1)
- [ ] Capacity planning review
- [ ] Cost optimization review
- [ ] Security audit
- [ ] Performance optimization
- [ ] Feature requests prioritization

---

## Sign-off

### 13. Deployment Approval ✅

**Staging Sign-off:**
- [ ] QA Team: _________________ Date: _______
- [ ] Dev Team: _________________ Date: _______
- [ ] DevOps: ___________________ Date: _______

**Production Sign-off:**
- [ ] Tech Lead: ________________ Date: _______
- [ ] Product Owner: ____________ Date: _______
- [ ] Operations: _______________ Date: _______

---

## Emergency Contacts

### 14. Contact Information

**Development Team:**
- Tech Lead: [Name] - [Phone] - [Email]
- Backend Dev: [Name] - [Phone] - [Email]

**Operations Team:**
- DevOps Lead: [Name] - [Phone] - [Email]
- SRE: [Name] - [Phone] - [Email]

**Business:**
- Product Owner: [Name] - [Phone] - [Email]
- Stakeholder: [Name] - [Phone] - [Email]

**Escalation Path:**
1. On-call Engineer
2. Tech Lead
3. CTO

---

## Appendix

### A. Useful Commands

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f app

# Restart service
docker-compose restart app

# Check database connections
docker-compose exec db_vector psql -U user -d db -c "SELECT count(*) FROM pg_stat_activity;"

# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Test API endpoint
curl -v http://localhost:8000/api/v2/health
```

### B. Troubleshooting

**Service won't start:**
1. Check logs: `docker-compose logs app`
2. Check .env file
3. Check database connectivity
4. Check disk space

**High latency:**
1. Check database indexes
2. Check vector index (IVFFlat)
3. Check resource usage
4. Check network latency

**Authentication errors:**
1. Verify API keys in .env
2. Check X-API-Key header
3. Check logs for auth attempts

---

**Version**: 2.0.0  
**Last Updated**: 2024-02-26  
**Next Review**: 2024-03-26
