"""Обработчики для внешних API с кэшированием"""
import requests
import json
import sys
from typing import Dict, Optional
from datetime import datetime
import os
import hashlib

# Добавить путь к api/services для импорта cache_manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../api/services'))
from cache_manager import get_cache_manager, CacheTTL


class TheMealDBHandler:
    """TheMealDB API - поиск рецептов с кэшированием"""
    
    def __init__(self, api_key: str = "1"):
        self.base_url = f"https://www.themealdb.com/api/json/v1/{api_key}"
        self.cache = get_cache_manager()
    
    def _make_cache_key(self, action: str, **kwargs) -> str:
        """Создать ключ кэша на основе действия и параметров"""
        params_str = json.dumps(kwargs, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"api:themealdb:{action}:{params_hash}"
    
    def search_by_name(self, name: str) -> Dict:
        """Поиск рецептов по названию с кэшированием"""
        cache_key = self._make_cache_key("search", name=name)
        
        if self.cache:
            def fetch_data():
                response = requests.get(f"{self.base_url}/search.php", params={"s": name}, timeout=10)
                response.raise_for_status()
                return response.json()
            
            return self.cache.get_or_set(cache_key, fetch_data, ttl=CacheTTL.HOUR)
        
        response = requests.get(f"{self.base_url}/search.php", params={"s": name}, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def random_meal(self) -> Dict:
        """Случайный рецепт (без кэширования - всегда новый)"""
        response = requests.get(f"{self.base_url}/random.php", timeout=10)
        response.raise_for_status()
        return response.json()


class OpenFoodFactsHandler:
    """Open Food Facts API - поиск продуктов с кэшированием"""
    
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/api/v2"
        self.headers = {"User-Agent": "Foodgram"}
        self.cache = get_cache_manager()
    
    def _make_cache_key(self, action: str, **kwargs) -> str:
        """Создать ключ кэша на основе действия и параметров"""
        params_str = json.dumps(kwargs, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"api:openfoodfacts:{action}:{params_hash}"
    
    def search_product(self, query: str) -> Dict:
        """Поиск продуктов с кэшированием"""
        cache_key = self._make_cache_key("search", query=query)
        
        if self.cache:
            def fetch_data():
                params = {"search_terms": query, "page_size": 5, "json": 1}
                response = requests.get(f"{self.base_url}/search", params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                return response.json()
            
            return self.cache.get_or_set(cache_key, fetch_data, ttl=CacheTTL.SIX_HOURS)
        
        params = {"search_terms": query, "page_size": 5, "json": 1}
        response = requests.get(f"{self.base_url}/search", params=params, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()


def save_api_response(api_name: str, action: str, data: Dict) -> str:
    """Сохранить результат в JSON"""
    results_dir = "api_results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{api_name}_{action}_{timestamp}.json"
    filepath = os.path.join(results_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({'api': api_name, 'action': action, 'data': data}, f, ensure_ascii=False, indent=2)
    
    return filepath
