#!/usr/bin/env python3
"""
Тест автоиндексации с реальными данными из S3.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from services.photo_indexing import get_photo_indexing_service
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_real_s3_structure():
    """Тестирует работу с реальной структурой S3."""
    
    print("🧪 Тест автоиндексации с реальными данными S3")
    print("=" * 60)
    
    # Реальные session_id из S3
    real_sessions = [
        "7108f6a3-0866-464f-8b68-0aaa5b2dc8a6",  # production
        "76f880ab-d239-4a48-8676-0d93d04fc75e",  # production
        "78b658cf-6597-41c8-b542-1c01f28302ad",  # staging
        "c04ea5b1-c513-4999-b52d-ba47a5161508",  # staging
    ]
    
    indexing_service = get_photo_indexing_service()
    
    for session_id in real_sessions:
        print(f"\n📋 Тестирование сессии: {session_id}")
        print("-" * 50)
        
        # Тест 1: Автоопределение окружения
        try:
            print("🔍 Автоопределение окружения...")
            photos_auto = indexing_service.scan_session_photos(session_id, "auto")
            print(f"✅ Найдено {len(photos_auto)} фотографий (auto)")
            
            if photos_auto:
                for photo in photos_auto[:3]:
                    photo_id = indexing_service.extract_photo_id_from_s3_key(photo)
                    print(f"  - {photo} → photo_id: {photo_id}")
        except Exception as e:
            print(f"❌ Ошибка auto: {e}")
        
        # Тест 2: Production окружение
        try:
            print("🏭 Production окружение...")
            photos_prod = indexing_service.scan_session_photos(session_id, "production")
            print(f"✅ Найдено {len(photos_prod)} фотографий (production)")
        except Exception as e:
            print(f"❌ Ошибка production: {e}")
        
        # Тест 3: Staging окружение
        try:
            print("🧪 Staging окружение...")
            photos_staging = indexing_service.scan_session_photos(session_id, "staging")
            print(f"✅ Найдено {len(photos_staging)} фотографий (staging)")
        except Exception as e:
            print(f"❌ Ошибка staging: {e}")
    
    print(f"\n" + "=" * 60)
    print("✅ Тест завершен!")


def test_photo_id_extraction():
    """Тестирует извлечение photo_id из реальных путей S3."""
    
    print("\n🔍 Тест извлечения photo_id")
    print("=" * 40)
    
    # Реальные пути из S3
    real_s3_keys = [
        "production/photos/7108f6a3-0866-464f-8b68-0aaa5b2dc8a6/previews/1769583325329-images.png",
        "production/photos/7108f6a3-0866-464f-8b68-0aaa5b2dc8a6/previews/1769583325358-Венгерский.png",
        "production/photos/76f880ab-d239-4a48-8676-0d93d04fc75e/previews/1769586652601-3880_ht29.jpg",
        "staging/photos/78b658cf-6597-41c8-b542-1c01f28302ad/1769580924868-PAJERO.jpg",
        "staging/photos/c04ea5b1-c513-4999-b52d-ba47a5161508/1769582360971-images.png",
    ]
    
    indexing_service = get_photo_indexing_service()
    
    for s3_key in real_s3_keys:
        photo_id = indexing_service.extract_photo_id_from_s3_key(s3_key)
        print(f"📸 {s3_key}")
        print(f"   → photo_id: {photo_id}")
        print()


if __name__ == "__main__":
    test_real_s3_structure()
    test_photo_id_extraction()