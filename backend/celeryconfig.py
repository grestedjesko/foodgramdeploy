"""Celery конфигурация для Foodgram"""
import os

# Broker и Backend
# Конструируем URL из REDIS_HOST, REDIS_PORT и REDIS_PASSWORD
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
redis_password = os.getenv('REDIS_PASSWORD', '')

if redis_password:
    # Используем Redis с аутентификацией
    broker_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/0'
    result_backend = f'redis://:{redis_password}@{redis_host}:{redis_port}/0'
else:
    # Redis без пароля (для локальной разработки)
    broker_url = f'redis://{redis_host}:{redis_port}/0'
    result_backend = f'redis://{redis_host}:{redis_port}/0'

# Сериализация
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Настройки задач
task_track_started = True
task_time_limit = 30 * 60  # 30 минут
task_soft_time_limit = 25 * 60  # 25 минут
task_acks_late = True
task_reject_on_worker_lost = True

# Настройки результатов
result_expires = 3600  # 1 час

# Имена задач
task_routes = {
    'celery_tasks.external_api.*': {'queue': 'external_api'},
}

# Worker настройки
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_disable_rate_limits = True

# Безопасность
worker_hijack_root_logger = False
