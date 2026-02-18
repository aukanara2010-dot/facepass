#!/usr/bin/env python3
"""
Скрипт для проверки структуры S3 бакета и поиска фотографий сессий.
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


def explore_s3_structure():
    """Исследует структуру S3 бакета."""
    
    print("🔍 Исследование структуры S3 бакета...")
    print("=" * 60)
    
    # Проверяем корневые папки
    try:
        print("📁 Корневые объекты в бакете:")
        # Используем минимальный префикс для получения всех объектов
        root_objects = list_s3_objects("a")  # Попробуем с префиксом "a"
        
        if not root_objects:
            # Если с "a" ничего нет, попробуем другие префиксы
            for prefix in ["s", "p", "u", "d", "i", "t", "f", "m"]:
                try:
                    test_objects = list_s3_objects(prefix)
                    if test_objects:
                        root_objects = test_objects
                        print(f"Найдены объекты с префиксом '{prefix}'")
                        break
                except S3Error:
                    continue
        
        # Группируем по папкам
        folders = set()
        files = []
        
        for obj in root_objects[:50]:  # Первые 50 объектов
            if '/' in obj:
                folder = obj.split('/')[0]
                folders.add(folder)
            else:
                files.append(obj)
        
        print(f"\n📂 Найдено папок: {len(folders)}")
        for folder in sorted(folders):
            print(f"  - {folder}/")
        
        if files:
            print(f"\n📄 Файлы в корне: {len(files)}")
            for file in files[:10]:
                print(f"  - {file}")
        
    except S3Error as e:
        print(f"❌ Ошибка доступа к S3: {e}")
        return
    
    # Проверяем возможные пути для сессий
    session_prefixes = [
        "sessions/",
        "session/", 
        "photo_sessions/",
        "photosessions/",
        "photos/sessions/",
        "uploads/sessions/",
        "storage/sessions/"
    ]
    
    print(f"\n🔍 Проверка возможных путей для сессий:")
    
    for prefix in session_prefixes:
        try:
            objects = list_s3_objects(prefix)
            if objects:
                print(f"✅ {prefix} - найдено {len(objects)} объектов")
                
                # Показываем примеры
                for obj in objects[:3]:
                    print(f"    - {obj}")
                if len(objects) > 3:
                    print(f"    ... и еще {len(objects) - 3}")
            else:
                print(f"❌ {prefix} - пусто")
                
        except S3Error:
            print(f"❌ {prefix} - не существует")
    
    # Ищем UUID-подобные папки (сессии)
    print(f"\n🔍 Поиск UUID-подобных папок (возможные сессии):")
    
    try:
        all_objects = list_s3_objects("")
        uuid_folders = set()
        
        for obj in all_objects:
            parts = obj.split('/')
            for part in parts:
                # Проверяем, похоже ли на UUID (36 символов с дефисами)
                if len(part) == 36 and part.count('-') == 4:
                    uuid_folders.add(part)
        
        if uuid_folders:
            print(f"📋 Найдено {len(uuid_folders)} UUID-подобных папок:")
            for uuid_folder in sorted(list(uuid_folders)[:10]):
                print(f"  - {uuid_folder}")
                
                # Проверяем содержимое этой папки
                try:
                    folder_objects = list_s3_objects(uuid_folder + "/")
                    if folder_objects:
                        print(f"    └─ {len(folder_objects)} объектов")
                        # Ищем подпапку previews
                        preview_objects = [obj for obj in folder_objects if 'preview' in obj.lower()]
                        if preview_objects:
                            print(f"    └─ {len(preview_objects)} preview объектов")
                except S3Error:
                    pass
        else:
            print("❌ UUID-подобные папки не найдены")
            
    except S3Error as e:
        print(f"❌ Ошибка поиска UUID папок: {e}")
    
    # Ищем файлы с расширениями изображений
    print(f"\n🖼️  Поиск изображений:")
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']
    
    try:
        all_objects = list_s3_objects("")
        image_files = []
        
        for obj in all_objects[:1000]:  # Первые 1000 объектов
            ext = '.' + obj.lower().split('.')[-1] if '.' in obj else ''
            if ext in image_extensions:
                image_files.append(obj)
        
        if image_files:
            print(f"📸 Найдено {len(image_files)} изображений:")
            
            # Группируем по папкам
            image_folders = {}
            for img in image_files:
                folder = '/'.join(img.split('/')[:-1]) if '/' in img else 'root'
                if folder not in image_folders:
                    image_folders[folder] = []
                image_folders[folder].append(img)
            
            for folder, images in sorted(image_folders.items()):
                print(f"  📁 {folder}: {len(images)} изображений")
                for img in images[:2]:
                    print(f"    - {img.split('/')[-1]}")
        else:
            print("❌ Изображения не найдены")
            
    except S3Error as e:
        print(f"❌ Ошибка поиска изображений: {e}")


if __name__ == "__main__":
    explore_s3_structure()