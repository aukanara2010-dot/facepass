#!/usr/bin/env python3
"""
Простой скрипт для проверки конкретных путей в S3.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.s3 import list_s3_objects, S3Error
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_specific_paths():
    """Проверяет конкретные пути в S3."""
    
    print("🔍 Проверка конкретных путей в S3...")
    print("=" * 50)
    
    # Список возможных путей для сессий
    paths_to_check = [
        "sessions/",
        "session/", 
        "photo_sessions/",
        "photosessions/",
        "photos/sessions/",
        "uploads/sessions/",
        "storage/sessions/",
        "pixora/sessions/",
        "data/sessions/",
        "files/sessions/",
        # Попробуем также прямые UUID (если сессии в корне)
        "1788875f-fc71-49d6-a9fa-a060e3ee6fee/",
        "550e8400-e29b-41d4-a716-446655440000/",
        # Другие возможные структуры
        "studio/",
        "galleries/",
        "events/",
        "media/",
        "images/",
        "photos/",
        "uploads/",
        "storage/",
        "data/",
        "files/",
        "content/",
        "assets/",
        "public/",
        "private/",
        "temp/",
        "tmp/",
        "cache/"
    ]
    
    found_paths = []
    
    for path in paths_to_check:
        try:
            objects = list_s3_objects(path)
            if objects:
                found_paths.append((path, len(objects)))
                print(f"✅ {path} - найдено {len(objects)} объектов")
                
                # Показываем первые несколько объектов
                for obj in objects[:3]:
                    print(f"    - {obj}")
                if len(objects) > 3:
                    print(f"    ... и еще {len(objects) - 3}")
                print()
            else:
                print(f"📁 {path} - папка существует, но пуста")
                
        except S3Error as e:
            print(f"❌ {path} - {str(e)}")
    
    print("\n" + "=" * 50)
    print("📊 ИТОГИ:")
    
    if found_paths:
        print(f"✅ Найдено {len(found_paths)} непустых путей:")
        for path, count in found_paths:
            print(f"  - {path}: {count} объектов")
    else:
        print("❌ Непустые пути не найдены")
    
    # Дополнительная проверка - ищем файлы изображений по расширениям
    print(f"\n🖼️  Поиск изображений по популярным префиксам...")
    
    image_prefixes = ["p", "i", "u", "s", "d", "f", "m", "a", "t"]
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']
    
    total_images = 0
    image_paths = {}
    
    for prefix in image_prefixes:
        try:
            objects = list_s3_objects(prefix)
            for obj in objects:
                ext = '.' + obj.lower().split('.')[-1] if '.' in obj else ''
                if ext in image_extensions:
                    total_images += 1
                    folder = '/'.join(obj.split('/')[:-1]) if '/' in obj else 'root'
                    if folder not in image_paths:
                        image_paths[folder] = 0
                    image_paths[folder] += 1
                    
                    if total_images <= 10:  # Показываем первые 10 изображений
                        print(f"  📸 {obj}")
                        
        except S3Error:
            continue
    
    if total_images > 0:
        print(f"\n📊 Найдено {total_images} изображений в папках:")
        for folder, count in sorted(image_paths.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {folder}: {count} изображений")
    else:
        print("\n❌ Изображения не найдены")


if __name__ == "__main__":
    check_specific_paths()