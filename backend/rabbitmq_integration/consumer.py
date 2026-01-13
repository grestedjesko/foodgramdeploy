#!/usr/bin/env python3
"""Consumer - обрабатывает задачи из RabbitMQ"""
import pika
import json
import sys
import argparse
from config import Config
from api_handlers import TheMealDBHandler, OpenFoodFactsHandler, save_api_response


class TaskConsumer:
    def __init__(self, queue_name: str):
        creds = Config.get_rabbitmq_credentials()
        credentials = pika.PlainCredentials(creds['username'], creds['password'])
        
        parameters = pika.ConnectionParameters(
            host=creds['host'],
            port=creds['port'],
            credentials=credentials
        )
        
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.queue_name = queue_name
        
        # Создать exchange и очередь (durable)
        self.channel.exchange_declare(exchange=Config.RABBITMQ_EXCHANGE, exchange_type='direct', durable=True)
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(exchange=Config.RABBITMQ_EXCHANGE, queue=queue_name, routing_key=queue_name)
        self.channel.basic_qos(prefetch_count=1)
        
        self.themealdb = TheMealDBHandler(Config.get_api_key('themealdb'))
        self.openfoodfacts = OpenFoodFactsHandler()
        
        print(f"Подключено. Слушаю очередь: {queue_name}")
    
    def process_task(self, api_alias: str, params: dict) -> dict:
        """Выполнить задачу"""
        action = params['action']
        
        if api_alias == 'themealdb':
            if action == 'search_by_name':
                return self.themealdb.search_by_name(params['name'])
            elif action == 'random_meal':
                return self.themealdb.random_meal()
        
        elif api_alias == 'openfoodfacts':
            if action == 'search_product':
                return self.openfoodfacts.search_product(params['query'])
        
        raise ValueError(f"Неизвестная задача: {api_alias}/{action}")
    
    def callback(self, ch, method, properties, body):
        """Обработка сообщения"""
        try:
            message = json.loads(body.decode('utf-8'))
            api_alias = message['api_alias']
            params = message['params']
            
            print(f"\n📨 Задача: {api_alias} → {params['action']}")
            
            result = self.process_task(api_alias, params)
            
            filepath = save_api_response(api_alias, params['action'], result)
            print(f"✓ Сохранено: {filepath}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start(self):
        """Начать обработку"""
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.callback, auto_ack=False)
        print(f"🎧 Ожидание задач... (Ctrl+C для остановки)\n")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("\n⏹ Остановка...")
            self.channel.stop_consuming()
            self.connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('queue', help='Очередь: themealdb_tasks или openfoodfacts_tasks')
    args = parser.parse_args()
    
    print("=== Foodgram Task Consumer ===\n")
    
    try:
        consumer = TaskConsumer(args.queue)
        consumer.start()
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
