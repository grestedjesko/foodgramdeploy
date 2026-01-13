"""API эндпоинты для работы с внешними API через RabbitMQ"""
import sys
import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rabbitmq_integration'))

from producer import TaskProducer


@api_view(['POST'])
@permission_classes([])
def import_recipe(request):
    """
    Импортировать рецепт из TheMealDB
    
    POST /api/external/import-recipe/
    Body: {"name": "pasta"} или {"random": true}
    """
    try:
        producer = TaskProducer()
        
        if request.data.get('random'):
            producer.send_task('themealdb', {'action': 'random_meal'}, 'themealdb_tasks')
            message = 'Задача на импорт случайного рецепта отправлена'
        else:
            name = request.data.get('name')
            if not name:
                return Response({'error': 'Укажите name или random'}, status=status.HTTP_400_BAD_REQUEST)
            
            producer.send_task('themealdb', {'action': 'search_by_name', 'name': name}, 'themealdb_tasks')
            message = f'Задача на импорт рецепта "{name}" отправлена'
        
        producer.close()
        
        return Response({
            'success': True,
            'message': message,
            'info': 'Результаты будут сохранены в api_results/'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])
def search_product(request):
    """
    Найти продукт в Open Food Facts
    
    POST /api/external/search-product/
    Body: {"query": "tomato"}
    """
    try:
        query = request.data.get('query')
        if not query:
            return Response({'error': 'Укажите query'}, status=status.HTTP_400_BAD_REQUEST)
        
        producer = TaskProducer()
        producer.send_task('openfoodfacts', {'action': 'search_product', 'query': query}, 'openfoodfacts_tasks')
        producer.close()
        
        return Response({
            'success': True,
            'message': f'Задача на поиск продукта "{query}" отправлена',
            'info': 'Результаты будут сохранены в api_results/'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([])
def api_status(request):
    """
    Проверить статус интеграции с внешними API
    
    GET /api/external/status/
    """
    try:
        from config import Config
        
        return Response({
            'rabbitmq': {
                'host': Config.RABBITMQ_HOST,
                'exchange': Config.RABBITMQ_EXCHANGE,
                'connected': True
            },
            'apis': {
                'themealdb': {
                    'name': 'TheMealDB',
                    'description': 'База данных рецептов',
                    'available': True
                },
                'openfoodfacts': {
                    'name': 'Open Food Facts',
                    'description': 'База данных продуктов',
                    'available': True
                }
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
