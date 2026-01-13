#!/usr/bin/env python3
"""Producer - отправляет задачи в RabbitMQ"""
import pika
import json
import sys
from config import Config


class TaskProducer:
    def __init__(self):
        creds = Config.get_rabbitmq_credentials()
        credentials = pika.PlainCredentials(creds['username'], creds['password'])
        
        parameters = pika.ConnectionParameters(
            host=creds['host'],
            port=creds['port'],
            credentials=credentials
        )
        
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        
        self.channel.exchange_declare(
            exchange=Config.RABBITMQ_EXCHANGE,
            exchange_type='direct',
            durable=True
        )
        
        print(f"Подключено к RabbitMQ")
    
    def send_task(self, api_alias: str, params: dict, routing_key: str):
        """Отправить задачу"""
        message = {'api_alias': api_alias, 'params': params}
        
        self.channel.basic_publish(
            exchange=Config.RABBITMQ_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(message, ensure_ascii=False),
            properties=pika.BasicProperties(delivery_mode=2)  # durable
        )
        
        print(f"✓ Отправлено: {api_alias} → {params['action']}")
    
    def close(self):
        self.connection.close()


def main():
    print("=== Foodgram Task Producer ===\n")
    
    try:
        producer = TaskProducer()
        
        producer.send_task('themealdb', {'action': 'search_by_name', 'name': 'pasta'}, 'themealdb_tasks')
        producer.send_task('themealdb', {'action': 'random_meal'}, 'themealdb_tasks')
        
        producer.send_task('openfoodfacts', {'action': 'search_product', 'query': 'tomato'}, 'openfoodfacts_tasks')
        
        print(f"\nОтправлено 3 задачи")
        producer.close()
        
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
