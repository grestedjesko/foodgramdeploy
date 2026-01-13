import os
import json
import redis
import hashlib
from functools import wraps
from typing import Any, Optional, Callable


class CacheManager:
    def __init__(self):
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        
        self.client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        try:
            self.client.ping()
            print(f"✓ Подключено к Redis: {self.redis_host}:{self.redis_port}")
        except redis.ConnectionError as e:
            print(f"✗ Ошибка подключения к Redis: {e}")
            raise
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized_value = json.dumps(value, ensure_ascii=False)
            
            if ttl:
                self.client.setex(key, ttl, serialized_value)
            else:
                self.client.set(key, serialized_value)
            
            return True
        except Exception as e:
            print(f"Ошибка записи в кэш (key={key}): {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.client.get(key)
            
            if value is None:
                return None
            
            return json.loads(value)
        except Exception as e:
            print(f"Ошибка чтения из кэша (key={key}): {e}")
            return None
    
    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Ошибка удаления из кэша (key={key}): {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Ошибка удаления по паттерну (pattern={pattern}): {e}")
            return 0
    
    def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        cached_value = self.get(key)
        
        if cached_value is not None:
            print(f"✓ Данные получены из кэша: {key}")
            return cached_value
        
        print(f"→ Кэш промах, вычисляем: {key}")
        value = factory_func()
        
        self.set(key, value, ttl)
        
        return value


class CacheTTL:
    MINUTE = 60
    FIVE_MINUTES = 300
    TEN_MINUTES = 600
    THIRTY_MINUTES = 1800
    HOUR = 3600
    SIX_HOURS = 21600
    DAY = 86400
    WEEK = 604800


def get_cache_manager() -> Optional[CacheManager]:
    try:
        return CacheManager()
    except Exception as e:
        print(f"Redis недоступен, кэширование отключено: {e}")
        return None


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    params_data = {
        'args': args,
        'kwargs': kwargs
    }
    params_str = json.dumps(params_data, sort_keys=True, default=str)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
    
    return f"{prefix}:{params_hash}"


def cache_queryset(cache_key_prefix: str, ttl: int = CacheTTL.FIVE_MINUTES):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            if not cache:
                return func(*args, **kwargs)
            
            request = None
            if len(args) > 1:
                request = args[1]
            
            cache_params = {}
            if request:
                cache_params.update(dict(request.GET.items()))
                if hasattr(request, 'user') and request.user.is_authenticated:
                    cache_params['user_id'] = request.user.id
            
            cache_key = make_cache_key(cache_key_prefix, **cache_params)
            
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                print(f"✓ Данные из кэша: {cache_key}")
                from rest_framework.response import Response
                return Response(cached_data)
            
            print(f"→ Кэш промах, выполняем запрос: {cache_key}")
            response = func(*args, **kwargs)
            
            if hasattr(response, 'data') and hasattr(response, 'status_code'):
                if 200 <= response.status_code < 300:
                    cache.set(cache_key, response.data, ttl)
            
            return response
        
        return wrapper
    return decorator


class CacheInvalidationMixin:
    cache_key_patterns = []
    
    def invalidate_cache(self, patterns: Optional[list] = None):
        cache = get_cache_manager()
        if not cache:
            return
        
        patterns_to_delete = patterns or self.cache_key_patterns
        
        for pattern in patterns_to_delete:
            deleted_count = cache.delete_pattern(pattern)
            if deleted_count > 0:
                print(f"✓ Инвалидировано кэш-ключей: {deleted_count} (паттерн: {pattern})")
    
    def perform_create(self, serializer):
        result = super().perform_create(serializer)
        self.invalidate_cache()
        return result
    
    def perform_update(self, serializer):
        result = super().perform_update(serializer)
        self.invalidate_cache()
        return result
    
    def perform_destroy(self, instance):
        result = super().perform_destroy(instance)
        self.invalidate_cache()
        return result
