#!/usr/bin/env python3
"""
Скрипт для тестирования принудительной переиндексации сессии
"""

import requests
import sys

def test_force_reindex(session_id: str, base_url: str = "http://localhost:8000"):
    """Тестирует эндпоинт принудительной переиндексации"""
    
    url = f"{base_url}/api/v1/faces/force-reindex-session/{session_id}"
    
    print(f"Запускаем принудительную переиндексацию для сессии: {session_id}")
    print(f"URL: {url}")
    print("=" * 60)
    
    try:
        response = requests.post(url, timeout=300)  # 5 минут таймаут
        
        if response.status_code == 200:
            result = response.json()
            print("✅ УСПЕШНО!")
            print(f"Сообщение: {result.get('message', 'N/A')}")
            print(f"Всего фото в облаке: {result.get('total_photos', 'N/A')}")
            print(f"Обработано новых: {result.get('processed_photos', 'N/A')}")
            print(f"Успешно: {result.get('successful_photos', 'N/A')}")
            print(f"Пропущено (уже есть): {result.get('skipped_photos', 'N/A')}")
            print(f"Ошибок: {result.get('failed_photos', 'N/A')}")
            print(f"Время обработки: {result.get('processing_time_ms', 'N/A'):.2f}ms")
            
            if result.get('errors'):
                print("\nОшибки:")
                for error in result['errors']:
                    print(f"  - {error}")
                    
        else:
            print(f"❌ ОШИБКА HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Детали: {error_detail}")
            except:
                print(f"Ответ: {response.text}")
                
    except requests.exceptions.Timeout:
        print("❌ ТАЙМАУТ - процесс занял больше 5 минут")
    except requests.exceptions.ConnectionError:
        print("❌ ОШИБКА ПОДКЛЮЧЕНИЯ - проверьте, что сервер запущен")
    except Exception as e:
        print(f"❌ НЕОЖИДАННАЯ ОШИБКА: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python test_force_reindex.py <session_id>")
        print("Пример: python test_force_reindex.py f1896ee0-d548-4676-a0a5-02ac09e6aad9")
        sys.exit(1)
    
    session_id = sys.argv[1]
    test_force_reindex(session_id)