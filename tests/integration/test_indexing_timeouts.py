#!/usr/bin/env python3
"""
Тест таймаутов и статусов индексации.
"""

import asyncio
import aiohttp
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))


async def test_search_with_timeout():
    """Тестирует поиск с таймаутами."""
    
    print("🧪 Тест поиска с таймаутами и статусами индексации")
    print("=" * 60)
    
    # Тестовые данные
    test_session_id = "7108f6a3-0866-464f-8b68-0aaa5b2dc8a6"  # Реальная сессия
    
    # Создаем тестовое изображение (1x1 пиксель PNG)
    test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # Настройки таймаута
    timeout = aiohttp.ClientTimeout(total=600)  # 10 минут
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        print(f"📋 Тестирование сессии: {test_session_id}")
        print(f"⏱️  Таймаут: {timeout.total} секунд")
        print("-" * 50)
        
        # Подготавливаем данные для отправки
        data = aiohttp.FormData()
        data.add_field('session_id', test_session_id)
        data.add_field('file', test_image_data, filename='test.png', content_type='image/png')
        data.add_field('threshold', '0.7')
        data.add_field('limit', '10')
        
        start_time = time.time()
        
        try:
            print("🚀 Отправляем запрос на поиск...")
            
            async with session.post('http://localhost:8000/api/v1/faces/search-session', data=data) as response:
                
                print(f"📡 Статус ответа: {response.status}")
                
                if response.status == 408:
                    print("⏰ Получен таймаут (408)")
                    result = await response.json()
                    print(f"💬 Сообщение: {result.get('detail', {}).get('message', 'Timeout')}")
                    return
                
                result = await response.json()
                
                elapsed_time = time.time() - start_time
                print(f"⏱️  Время выполнения: {elapsed_time:.2f} секунд")
                
                # Анализируем результат
                print("\n📊 Результат:")
                print(f"  - Статус индексации: {result.get('indexing_status', 'не указан')}")
                print(f"  - Найдено совпадений: {len(result.get('matches', []))}")
                print(f"  - Проиндексировано фото: {result.get('indexed_photos', 0)}")
                print(f"  - Время поиска: {result.get('query_time_ms', 0):.0f} мс")
                
                # Информация об индексации
                if 'indexing_progress' in result:
                    progress = result['indexing_progress']
                    print(f"\n🔄 Прогресс индексации:")
                    print(f"  - Статус: {progress.get('status', 'неизвестен')}")
                    
                    if 'total_photos' in progress:
                        print(f"  - Всего фото: {progress['total_photos']}")
                    if 'successful_photos' in progress:
                        print(f"  - Успешно обработано: {progress['successful_photos']}")
                    if 'indexing_time_seconds' in progress:
                        print(f"  - Время индексации: {progress['indexing_time_seconds']:.2f}с")
                    if 'photos_per_second' in progress:
                        print(f"  - Скорость: {progress['photos_per_second']:.1f} фото/сек")
                
                # Примеры найденных фото
                if result.get('matches'):
                    print(f"\n📸 Примеры найденных фото:")
                    for i, match in enumerate(result['matches'][:3]):
                        print(f"  {i+1}. {match.get('file_name', 'unknown')} (схожесть: {match.get('similarity', 0):.2f})")
                
                print(f"\n✅ Тест завершен успешно!")
                
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"⏰ Таймаут клиента после {elapsed_time:.2f} секунд")
            
        except aiohttp.ClientError as e:
            print(f"❌ Ошибка клиента: {e}")
            
        except Exception as e:
            print(f"💥 Неожиданная ошибка: {e}")


async def test_manual_indexing():
    """Тестирует ручную индексацию."""
    
    print("\n" + "=" * 60)
    print("🔧 Тест ручной индексации")
    print("=" * 60)
    
    test_session_id = "c04ea5b1-c513-4999-b52d-ba47a5161508"  # Staging сессия
    
    timeout = aiohttp.ClientTimeout(total=900)  # 15 минут
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        print(f"📋 Тестирование ручной индексации: {test_session_id}")
        print(f"⏱️  Таймаут: {timeout.total} секунд")
        
        start_time = time.time()
        
        try:
            url = f'http://localhost:8000/api/v1/faces/index-session/{test_session_id}'
            params = {
                'force_reindex': True,
                'max_photos': 50
            }
            
            print("🚀 Запускаем ручную индексацию...")
            
            async with session.post(url, params=params) as response:
                
                print(f"📡 Статус ответа: {response.status}")
                
                result = await response.json()
                elapsed_time = time.time() - start_time
                
                print(f"⏱️  Время выполнения: {elapsed_time:.2f} секунд")
                
                if response.status == 200:
                    print("✅ Индексация завершена успешно!")
                    print(f"  - Обработано фото: {result.get('processed_photos', 0)}")
                    print(f"  - Успешно: {result.get('successful_photos', 0)}")
                    print(f"  - Неудачно: {result.get('failed_photos', 0)}")
                    print(f"  - Время обработки: {result.get('processing_time_ms', 0):.0f} мс")
                else:
                    print(f"❌ Ошибка индексации: {result.get('detail', 'Unknown error')}")
                
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            print(f"⏰ Таймаут ручной индексации после {elapsed_time:.2f} секунд")
            
        except Exception as e:
            print(f"💥 Ошибка: {e}")


async def main():
    """Главная функция тестирования."""
    
    print("🧪 Тестирование таймаутов и индексации FacePass")
    print("=" * 60)
    
    try:
        # Тест 1: Поиск с автоиндексацией
        await test_search_with_timeout()
        
        # Тест 2: Ручная индексация
        await test_manual_indexing()
        
        print("\n" + "=" * 60)
        print("🎉 Все тесты завершены!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Тесты прерваны пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())