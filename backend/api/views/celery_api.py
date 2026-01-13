"""API эндпоинты для работы с Celery задачами"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from celery.result import AsyncResult

from celery_tasks.external_api import (
    search_recipe_by_name,
    get_random_meal,
    search_product,
    health_check,
)


@api_view(['POST'])
@permission_classes([])
def celery_import_recipe(request):
    """
    Импортировать рецепт из TheMealDB через Celery
    
    POST /api/celery/import-recipe/
    Body: {"name": "pasta"} или {"random": true}
    
    Returns:
        task_id для отслеживания статуса
    """
    try:
        if request.data.get('random'):
            task = get_random_meal.delay()
            message = 'Задача на импорт случайного рецепта запущена'
            params = {'random': True}
        else:
            name = request.data.get('name')
            if not name:
                return Response(
                    {'error': 'Укажите name или random'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            task = search_recipe_by_name.delay(name)
            message = f'Задача на импорт рецепта "{name}" запущена'
            params = {'name': name}
        
        return Response({
            'success': True,
            'message': message,
            'task_id': task.id,
            'params': params,
            'status_url': f'/api/celery/task-status/{task.id}/',
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])
def celery_search_product(request):
    """
    Найти продукт в Open Food Facts через Celery
    
    POST /api/celery/search-product/
    Body: {"query": "tomato"}
    
    Returns:
        task_id для отслеживания статуса
    """
    try:
        query = request.data.get('query')
        if not query:
            return Response(
                {'error': 'Укажите query'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task = search_product.delay(query)
        
        return Response({
            'success': True,
            'message': f'Задача на поиск продукта "{query}" запущена',
            'task_id': task.id,
            'params': {'query': query},
            'status_url': f'/api/celery/task-status/{task.id}/',
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])
def celery_task_status(request, task_id):
    """
    Получить статус Celery задачи
    
    GET /api/celery/task-status/<task_id>/
    
    Returns:
        Подробная информация о статусе задачи
    """
    try:
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'state': task_result.state,
            'ready': task_result.ready(),
            'successful': task_result.successful() if task_result.ready() else None,
            'failed': task_result.failed() if task_result.ready() else None,
        }
        
        # Если задача завершена, добавить результат
        if task_result.ready():
            if task_result.successful():
                response_data['result'] = task_result.result
            else:
                response_data['error'] = str(task_result.info)
        
        # Добавить информацию о прогрессе, если доступна
        if task_result.state == 'PROGRESS':
            response_data['progress'] = task_result.info
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])
def celery_health(request):
    """
    Проверить работоспособность Celery
    
    GET /api/celery/health/
    
    Returns:
        Статус Celery worker
    """
    try:
        # Запустить простую задачу для проверки
        task = health_check.delay()
        
        # Подождать результат (макс. 5 секунд)
        result = task.get(timeout=5)
        
        return Response({
            'status': 'healthy',
            'celery': result,
            'broker': 'connected',
        })
        
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([])
def celery_status(request):
    """
    Получить общую информацию о Celery
    
    GET /api/celery/status/
    """
    try:
        from celery_app import app as celery_app
        
        # Получить информацию о workers (если доступно)
        inspect = celery_app.control.inspect()
        active = inspect.active()
        registered = inspect.registered()
        
        return Response({
            'celery': {
                'broker': celery_app.conf.broker_url.split('@')[-1] if '@' in celery_app.conf.broker_url else celery_app.conf.broker_url,
                'result_backend': celery_app.conf.result_backend.split('@')[-1] if '@' in celery_app.conf.result_backend else celery_app.conf.result_backend,
            },
            'workers': {
                'active_tasks': active if active else {},
                'registered_tasks': registered if registered else {},
            },
            'tasks': {
                'themealdb': {
                    'search_by_name': 'celery_tasks.external_api.search_recipe_by_name',
                    'random_meal': 'celery_tasks.external_api.get_random_meal',
                },
                'openfoodfacts': {
                    'search_product': 'celery_tasks.external_api.search_product',
                }
            }
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
