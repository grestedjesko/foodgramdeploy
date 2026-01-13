"""Конфигурация из переменных окружения"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
    RABBITMQ_USERNAME = os.getenv('RABBITMQ_USERNAME')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')
    RABBITMQ_EXCHANGE = os.getenv('RABBITMQ_EXCHANGE', 'foodgram_tasks')
    RABBITMQ_EXCHANGE_TYPE = os.getenv('RABBITMQ_EXCHANGE_TYPE', 'direct')
    
    THEMEALDB_API_KEY = os.getenv('THEMEALDB_API_KEY', '1')
    API_RESULTS_DIR = os.getenv('API_RESULTS_DIR', 'api_results')
    
    @classmethod
    def validate(cls):
        errors = []
        if not cls.RABBITMQ_USERNAME:
            errors.append("RABBITMQ_USERNAME не установлен")
        if not cls.RABBITMQ_PASSWORD:
            errors.append("RABBITMQ_PASSWORD не установлен")
        
        if errors:
            raise ValueError(
                f"Отсутствуют обязательные переменные окружения:\n" + 
                "\n".join(f"  - {err}" for err in errors)
            )
    
    @classmethod
    def get_rabbitmq_credentials(cls) -> Dict[str, any]:
        cls.validate()
        return {
            'host': cls.RABBITMQ_HOST,
            'port': cls.RABBITMQ_PORT,
            'username': cls.RABBITMQ_USERNAME,
            'password': cls.RABBITMQ_PASSWORD,
        }
    
    @classmethod
    def get_api_key(cls, api_name: str) -> Optional[str]:
        if api_name.lower() == 'themealdb':
            return cls.THEMEALDB_API_KEY
        raise ValueError(f"Неизвестное API: {api_name}")
