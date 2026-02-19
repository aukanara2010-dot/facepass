#!/usr/bin/env python3
"""
Security Check Script for FacePass
Проверяет сайт на соответствие требованиям Google Safe Browsing
"""

import requests
import re
import os
from urllib.parse import urljoin
import json

class SecurityChecker:
    def __init__(self, base_url="https://facepass.pixorasoft.ru"):
        self.base_url = base_url
        self.issues = []
        self.passed = []
        
    def log_issue(self, category, message):
        self.issues.append(f"❌ {category}: {message}")
        
    def log_pass(self, category, message):
        self.passed.append(f"✅ {category}: {message}")
        
    def check_https_enforcement(self):
        """Проверяет принудительное использование HTTPS"""
        print("🔍 Проверка HTTPS...")
        
        try:
            # Проверяем редирект с HTTP на HTTPS
            http_url = self.base_url.replace('https://', 'http://')
            response = requests.get(http_url, allow_redirects=False, timeout=10)
            
            if response.status_code in [301, 302, 308]:
                location = response.headers.get('Location', '')
                if location.startswith('https://'):
                    self.log_pass("HTTPS", "HTTP корректно перенаправляется на HTTPS")
                else:
                    self.log_issue("HTTPS", "HTTP не перенаправляется на HTTPS")
            else:
                self.log_issue("HTTPS", f"HTTP возвращает код {response.status_code} вместо редиректа")
                
        except Exception as e:
            self.log_issue("HTTPS", f"Ошибка проверки HTTPS: {str(e)}")
    
    def check_security_headers(self):
        """Проверяет заголовки безопасности"""
        print("🔍 Проверка заголовков безопасности...")
        
        try:
            response = requests.get(self.base_url, timeout=10)
            headers = response.headers
            
            # Обязательные заголовки безопасности
            required_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                'X-XSS-Protection': '1; mode=block',
                'Content-Security-Policy': None,  # Просто проверяем наличие
                'Permissions-Policy': None
            }
            
            for header, expected in required_headers.items():
                if header in headers:
                    if expected is None:
                        self.log_pass("Headers", f"{header} присутствует")
                    elif isinstance(expected, list):
                        if any(exp in headers[header] for exp in expected):
                            self.log_pass("Headers", f"{header}: {headers[header]}")
                        else:
                            self.log_issue("Headers", f"{header} имеет неожиданное значение: {headers[header]}")
                    elif expected in headers[header]:
                        self.log_pass("Headers", f"{header}: {headers[header]}")
                    else:
                        self.log_issue("Headers", f"{header} имеет неожиданное значение: {headers[header]}")
                else:
                    self.log_issue("Headers", f"Отсутствует заголовок {header}")
                    
        except Exception as e:
            self.log_issue("Headers", f"Ошибка проверки заголовков: {str(e)}")
    
    def check_robots_txt(self):
        """Проверяет robots.txt"""
        print("🔍 Проверка robots.txt...")
        
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            response = requests.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Проверяем основные директивы
                if 'User-agent:' in content:
                    self.log_pass("robots.txt", "Содержит User-agent директивы")
                else:
                    self.log_issue("robots.txt", "Отсутствуют User-agent директивы")
                    
                if 'Disallow:' in content:
                    self.log_pass("robots.txt", "Содержит Disallow директивы")
                else:
                    self.log_issue("robots.txt", "Отсутствуют Disallow директивы")
                    
                if 'Sitemap:' in content:
                    self.log_pass("robots.txt", "Содержит ссылку на sitemap")
                else:
                    self.log_issue("robots.txt", "Отсутствует ссылка на sitemap")
                    
            else:
                self.log_issue("robots.txt", f"Недоступен (код {response.status_code})")
                
        except Exception as e:
            self.log_issue("robots.txt", f"Ошибка проверки: {str(e)}")
    
    def check_security_txt(self):
        """Проверяет security.txt"""
        print("🔍 Проверка security.txt...")
        
        try:
            security_url = urljoin(self.base_url, '/.well-known/security.txt')
            response = requests.get(security_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                required_fields = ['Contact:', 'Expires:', 'Canonical:']
                for field in required_fields:
                    if field in content:
                        self.log_pass("security.txt", f"Содержит {field}")
                    else:
                        self.log_issue("security.txt", f"Отсутствует {field}")
                        
            else:
                self.log_issue("security.txt", f"Недоступен (код {response.status_code})")
                
        except Exception as e:
            self.log_issue("security.txt", f"Ошибка проверки: {str(e)}")
    
    def check_sitemap_xml(self):
        """Проверяет sitemap.xml"""
        print("🔍 Проверка sitemap.xml...")
        
        try:
            sitemap_url = urljoin(self.base_url, '/sitemap.xml')
            response = requests.get(sitemap_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                if '<?xml' in content and '<urlset' in content:
                    self.log_pass("sitemap.xml", "Корректный XML формат")
                else:
                    self.log_issue("sitemap.xml", "Некорректный XML формат")
                    
                if self.base_url in content:
                    self.log_pass("sitemap.xml", "Содержит URL сайта")
                else:
                    self.log_issue("sitemap.xml", "Не содержит URL сайта")
                    
            else:
                self.log_issue("sitemap.xml", f"Недоступен (код {response.status_code})")
                
        except Exception as e:
            self.log_issue("sitemap.xml", f"Ошибка проверки: {str(e)}")
    
    def check_mixed_content(self):
        """Проверяет смешанный контент (HTTP ресурсы на HTTPS странице)"""
        print("🔍 Проверка смешанного контента...")
        
        try:
            response = requests.get(self.base_url, timeout=10)
            content = response.text
            
            # Ищем HTTP ссылки в HTML
            http_links = re.findall(r'http://[^"\s<>]+', content)
            
            # Фильтруем localhost ссылки (они допустимы для разработки)
            external_http = [link for link in http_links if 'localhost' not in link and '127.0.0.1' not in link]
            
            if external_http:
                for link in external_http:
                    self.log_issue("Mixed Content", f"HTTP ссылка: {link}")
            else:
                self.log_pass("Mixed Content", "Внешние HTTP ссылки не найдены")
                
        except Exception as e:
            self.log_issue("Mixed Content", f"Ошибка проверки: {str(e)}")
    
    def check_javascript_safety(self):
        """Проверяет безопасность JavaScript"""
        print("🔍 Проверка JavaScript безопасности...")
        
        try:
            # Проверяем основную страницу
            response = requests.get(self.base_url, timeout=10)
            content = response.text
            
            # Ищем подозрительные паттерны
            suspicious_patterns = [
                r'eval\s*\(',
                r'document\.write\s*\(',
                r'innerHTML\s*=.*<script',
                r'setTimeout\s*\(\s*["\'].*["\']',
                r'setInterval\s*\(\s*["\'].*["\']'
            ]
            
            found_suspicious = False
            for pattern in suspicious_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    self.log_issue("JavaScript", f"Подозрительный паттерн: {pattern}")
                    found_suspicious = True
            
            if not found_suspicious:
                self.log_pass("JavaScript", "Подозрительные паттерны не найдены")
                
            # Проверяем внешние скрипты
            script_sources = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content)
            
            for src in script_sources:
                if src.startswith('http://'):
                    self.log_issue("JavaScript", f"HTTP скрипт: {src}")
                elif src.startswith('https://'):
                    # Проверяем доверенные CDN
                    trusted_cdns = [
                        'cdn.tailwindcss.com',
                        'cdnjs.cloudflare.com',
                        'fonts.googleapis.com',
                        'fonts.gstatic.com'
                    ]
                    
                    if any(cdn in src for cdn in trusted_cdns):
                        self.log_pass("JavaScript", f"Доверенный CDN: {src}")
                    else:
                        self.log_issue("JavaScript", f"Внешний скрипт: {src}")
                        
        except Exception as e:
            self.log_issue("JavaScript", f"Ошибка проверки: {str(e)}")
    
    def run_all_checks(self):
        """Запускает все проверки"""
        print("🚀 Запуск проверки безопасности FacePass...")
        print(f"🌐 URL: {self.base_url}")
        print("=" * 60)
        
        self.check_https_enforcement()
        self.check_security_headers()
        self.check_robots_txt()
        self.check_security_txt()
        self.check_sitemap_xml()
        self.check_mixed_content()
        self.check_javascript_safety()
        
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ")
        print("=" * 60)
        
        print(f"\n✅ ПРОЙДЕНО ({len(self.passed)}):")
        for item in self.passed:
            print(f"  {item}")
            
        print(f"\n❌ ПРОБЛЕМЫ ({len(self.issues)}):")
        for item in self.issues:
            print(f"  {item}")
            
        print(f"\n📈 ОБЩИЙ СЧЕТ: {len(self.passed)}/{len(self.passed) + len(self.issues)}")
        
        if len(self.issues) == 0:
            print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Сайт готов к подаче запроса на пересмотр в Google Safe Browsing.")
        else:
            print("⚠️  ТРЕБУЮТСЯ ИСПРАВЛЕНИЯ перед подачей запроса на пересмотр.")
            
        return len(self.issues) == 0

def main():
    import sys
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://facepass.pixorasoft.ru"
    
    checker = SecurityChecker(url)
    success = checker.run_all_checks()
    
    # Возвращаем код выхода
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()