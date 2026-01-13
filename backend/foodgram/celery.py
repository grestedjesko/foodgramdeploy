"""Celery интеграция с Django"""
import os
from celery import Celery

# Установить Django settings модуль по умолчанию
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')

# Создать Celery приложение
app = Celery('foodgram')

# Загрузить конфигурацию из celeryconfig.py
app.config_from_object('celeryconfig')

# Автоматически находить задачи
app.autodiscover_tasks(['celery_tasks'])
