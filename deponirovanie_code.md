# ФРАГМЕНТЫ ИСХОДНОГО КОДА ПРОГРАММЫ "PIXORA FACE"
## Для официальной регистрации в Роспатенте

**Программа:** PIXORA FACE - Система поиска фотографий по лицу  
**Правообладатель:** PIXORASOFT  
**Дата подготовки:** 19 февраля 2026 г.

---

## 1. МОДУЛЬ РАСПОЗНАВАНИЯ ЛИЦ И ГЕНЕРАЦИИ ЭМБЕДДИНГОВ

```python
# Функция извлечения векторного дескриптора лица из изображения
# Использует модель InsightFace buffalo_l для генерации 512-мерного вектора
def get_embeddings(self, image_data: bytes) -> List[Tuple[np.ndarray, float]]:
    """
    Извлечение эмбеддингов лиц из изображения
    
    Находит все лица на изображении и возвращает их векторные дескрипторы.
    Основной алгоритм системы PIXORA FACE.
    
    Args:
        image_data: Бинарные данные изображения
        
    Returns:
        Список кортежей (вектор_эмбеддинга, коэффициент_уверенности)
    """
    if not self.initialized or self.app is None:
        raise RuntimeError("Сервис распознавания лиц не инициализирован")
    
    try:
        # Конвертация байтов в массив изображения
        img = self._bytes_to_image(image_data)
        
        # Детекция лиц и извлечение эмбеддингов с помощью buffalo_l модели
        faces = self.app.get(img)
        
        if len(faces) == 0:
            return []
        
        # Извлечение эмбеддингов и коэффициентов уверенности
        results = []
        for face in faces:
            embedding = face.embedding  # 512-мерный вектор
            confidence = float(face.det_score)  # Коэффициент детекции
            
            # Проверка нормализации эмбеддинга
            norm = np.linalg.norm(embedding)
            
            results.append((embedding, confidence))
            
        return results
        
    except Exception as e:
        raise ValueError(f"Ошибка обработки изображения: {str(e)}")

# Функция сравнения двух векторных дескрипторов лиц
# Использует косинусное сходство для определения идентичности лиц
def compare_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Сравнение двух эмбеддингов лиц с использованием косинусного сходства
    
    Args:
        embedding1: Первый вектор эмбеддинга (512 измерений)
        embedding2: Второй вектор эмбеддинга (512 измерений)
        
    Returns:
        Коэффициент сходства (0.0 до 1.0, выше = более похожи)
    """
    # Нормализация векторов
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # Косинусное сходство
    dot_product = np.dot(embedding1, embedding2)
    similarity = dot_product / (norm1 * norm2)
    
    # Преобразование из [-1, 1] в [0, 1]
    normalized_similarity = (similarity + 1) / 2
    
    return float(normalized_similarity)
```

---

## 2. МОДУЛЬ ВЕКТОРНОГО ПОИСКА В БАЗЕ ДАННЫХ POSTGRESQL

```python
# Функция поиска похожих лиц в векторной базе данных
# Использует расширение pgvector для эффективного поиска по сходству
async def search_faces_in_session(
    session_id: str,
    file: UploadFile,
    threshold: float = 0.5,
    limit: int = 50,
    vector_db: Session
):
    """
    Поиск похожих лиц в рамках фотосессии (основная функция FacePass)
    
    Алгоритм:
    1. Извлекает эмбеддинг из загруженного селфи
    2. Ищет похожие лица в векторной БД с фильтром по сессии
    3. Возвращает совпадения выше порога сходства
    
    Args:
        session_id: UUID фотосессии для поиска
        file: Селфи от клиента
        threshold: Минимальный порог сходства (0.5 = 50% похожести)
        limit: Максимальное количество результатов
    """
    
    # Извлечение эмбеддинга из загруженного селфи
    face_service = get_face_recognition_service()
    query_embedding, confidence = face_service.extract_single_embedding(file_data)
    
    if query_embedding is None:
        return {"matches": [], "message": "Лицо не обнаружено"}
    
    # Нормализация эмбеддинга для консистентного расчета сходства
    import numpy as np
    embedding_norm = np.linalg.norm(query_embedding)
    if embedding_norm > 0:
        query_embedding = query_embedding / embedding_norm
    
    # Конвертация эмбеддинга в строковый формат для SQL запроса
    query_embedding_list = query_embedding.tolist()
    query_embedding_str = '[' + ','.join(map(str, query_embedding_list)) + ']'
    
    # Векторный поиск сходства с использованием оператора <=> (косинусное расстояние)
    # Формула: сходство = 1 - расстояние
    query = text("""
        SELECT 
            fe.photo_id,
            1 - (fe.embedding <=> :query_embedding) as similarity
        FROM face_embeddings fe
        WHERE fe.session_id = :session_id
            AND (1 - (fe.embedding <=> :query_embedding)) >= :threshold
        ORDER BY similarity DESC
        LIMIT :limit
    """)
    
    result = vector_db.execute(
        query,
        {
            "query_embedding": query_embedding_str,
            "session_id": session_id,
            "threshold": threshold,
            "limit": limit
        }
    )
    
    # Сбор ID фотографий и коэффициентов сходства
    photo_matches = []
    for row in result:
        photo_id = row[0]
        similarity = float(row[1])
        
        photo_matches.append({
            "photo_id": photo_id,
            "similarity": similarity
        })
    
    return {"matches": photo_matches}
```

---

## 3. МОДУЛЬ АВТОМАТИЧЕСКОЙ ИНДЕКСАЦИИ ФОТОГРАФИЙ

```python
# Функция обработки одной фотографии для извлечения и сохранения эмбеддингов
# Ключевой алгоритм подготовки данных для поиска
def process_single_photo(
    self, 
    s3_key: str, 
    session_id: str, 
    vector_db: Session
) -> Tuple[bool, Optional[str]]:
    """
    Обработка одной фотографии: загрузка, извлечение эмбеддингов, сохранение в БД
    
    Алгоритм PIXORA FACE для автоматической индексации:
    1. Загружает фото из облачного хранилища
    2. Извлекает все лица и их векторные дескрипторы
    3. Нормализует векторы для консистентного поиска
    4. Сохраняет в векторную базу данных PostgreSQL
    
    Args:
        s3_key: Ключ объекта в S3 хранилище
        session_id: UUID фотосессии
        vector_db: Сессия векторной базы данных
        
    Returns:
        Кортеж (успех: bool, сообщение_об_ошибке: Optional[str])
    """
    
    # Извлечение ID фотографии из S3 ключа
    photo_id = self.extract_photo_id_from_s3_key(s3_key)
    if not photo_id:
        return False, f"Не удалось извлечь ID фото из {s3_key}"
    
    # Проверка, не обработана ли уже эта фотография
    existing = vector_db.query(FaceEmbedding).filter(
        FaceEmbedding.photo_id == photo_id,
        FaceEmbedding.session_id == session_id
    ).first()
    
    if existing:
        return True, None  # Уже обработана
    
    # Загрузка фотографии из S3
    try:
        photo_data = download_image(s3_key)
    except S3Error as e:
        return False, f"Ошибка загрузки {s3_key}: {str(e)}"
    
    # Извлечение эмбеддингов лиц
    try:
        embeddings = self.face_service.get_embeddings(photo_data)
        
        if not embeddings:
            return True, None  # Лица не найдены - не ошибка
        
    except Exception as e:
        return False, f"Ошибка извлечения лиц из {s3_key}: {str(e)}"
    
    # Сохранение эмбеддингов в базу данных
    saved_count = 0
    for embedding_vector, confidence in embeddings:
        try:
            # Нормализация эмбеддинга для консистентного расчета сходства
            import numpy as np
            embedding_norm = np.linalg.norm(embedding_vector)
            if embedding_norm > 0:
                normalized_embedding = embedding_vector / embedding_norm
            else:
                normalized_embedding = embedding_vector
            
            # Создание записи в векторной БД
            face_embedding = FaceEmbedding(
                photo_id=photo_id,
                session_id=session_id,
                embedding=normalized_embedding.tolist(),  # Нормализованный вектор
                confidence=confidence
            )
            
            vector_db.add(face_embedding)
            saved_count += 1
            
        except Exception as e:
            return False, f"Ошибка сохранения в БД: {str(e)}"
    
    # Фиксация транзакции
    vector_db.commit()
    
    return True, None
```

---

## 4. КОНФИГУРАЦИЯ СИСТЕМЫ (ОЧИЩЕННАЯ ОТ СЕКРЕТНЫХ ДАННЫХ)

```python
# Основные настройки системы PIXORA FACE
class Settings(BaseSettings):
    """Конфигурация системы распознавания лиц"""
    
    # Настройки базы данных (секретные данные заменены на заглушки)
    DATABASE_URL: str = "postgresql://username:your_secure_password@localhost:5432/facepass_db"
    VECTOR_DATABASE_URL: str = "postgresql://username:your_secure_password@localhost:5432/vector_db"
    PIXORA_DATABASE_URL: str = "postgresql://username:your_secure_password@remote_host:5432/pixora_db"
    
    # Настройки S3 хранилища (секретные ключи заменены)
    S3_ACCESS_KEY: str = "your_s3_access_key"
    S3_SECRET_KEY: str = "your_s3_secret_key"
    S3_BUCKET_NAME: str = "pixora-photos-bucket"
    S3_ENDPOINT_URL: str = "https://s3.example.com"
    
    # Параметры алгоритма распознавания лиц
    FACE_SIMILARITY_THRESHOLD: float = 0.5  # Порог сходства (50%)
    MAX_FACES_PER_PHOTO: int = 10           # Максимум лиц на фото
    EMBEDDING_DIMENSION: int = 512          # Размерность вектора InsightFace
    
    # Настройки производительности
    MAX_PHOTOS_PER_SESSION: int = 1000      # Лимит фото в сессии
    SEARCH_RESULT_LIMIT: int = 50           # Лимит результатов поиска
    INDEXING_BATCH_SIZE: int = 10           # Размер пакета индексации
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

---

## ТЕХНИЧЕСКОЕ ОПИСАНИЕ АЛГОРИТМА

**Уникальные особенности системы PIXORA FACE:**

1. **Двухэтапная нормализация векторов** - эмбеддинги нормализуются как при сохранении, так и при поиске для максимальной точности косинусного сходства

2. **Гибридная архитектура баз данных** - использование отдельной векторной БД с pgvector для высокоскоростного поиска и основной БД для метаданных

3. **Автоматическая индексация с проверкой дубликатов** - система автоматически индексирует новые фотографии, избегая повторной обработки

4. **Адаптивный порог сходства** - настраиваемый порог от 0.5 до 0.7 в зависимости от требований точности

5. **Сессионная изоляция данных** - поиск ограничен рамками конкретной фотосессии для обеспечения приватности

**Математическая основа:**
- Косинусное сходство: `similarity = (A·B) / (||A|| × ||B||)`
- Нормализация: `normalized_vector = vector / ||vector||`
- Поиск: `1 - cosine_distance >= threshold`

---

**Примечание:** Все секретные ключи, пароли и IP-адреса в данном документе заменены на заглушки в соответствии с требованиями безопасности. Реальные значения хранятся в защищенных конфигурационных файлах.