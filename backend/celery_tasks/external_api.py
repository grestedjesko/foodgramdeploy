"""Celery задачи для работы с внешними API"""
import os
import sys
from celery import shared_task
from typing import Dict

# Добавить путь к rabbitmq_integration для импорта api_handlers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rabbitmq_integration'))

from api_handlers import TheMealDBHandler, OpenFoodFactsHandler, save_api_response


@shared_task(name='celery_tasks.external_api.search_recipe_by_name', bind=True)
def search_recipe_by_name(self, name: str) -> Dict:
    """
    Поиск рецепта по названию в TheMealDB
    
    Args:
        name: Название рецепта для поиска
        
    Returns:
        dict: Результат поиска с информацией о сохраненном файле и данными рецепта
    """
    try:
        handler = TheMealDBHandler(api_key=os.getenv('THEMEALDB_API_KEY', '1'))
        result = handler.search_by_name(name)
        
        filepath = save_api_response('themealdb', 'search_by_name', result)
        
        # Извлечь данные рецепта для отображения
        recipe_data = None
        if result and 'meals' in result and result['meals']:
            meal = result['meals'][0]
            # Собрать ингредиенты
            ingredients = []
            for i in range(1, 21):
                ingredient = meal.get(f'strIngredient{i}')
                measure = meal.get(f'strMeasure{i}')
                if ingredient and ingredient.strip():
                    ingredients.append({
                        'name': ingredient.strip(),
                        'measure': measure.strip() if measure else ''
                    })
            
            recipe_data = {
                'name': meal.get('strMeal', ''),
                'image': meal.get('strMealThumb', ''),
                'category': meal.get('strCategory', ''),
                'area': meal.get('strArea', ''),
                'instructions': meal.get('strInstructions', ''),
                'youtube': meal.get('strYoutube', ''),
                'source': meal.get('strSource', 'TheMealDB'),
                'ingredients': ingredients,
            }
        
        return {
            'status': 'success',
            'api': 'themealdb',
            'action': 'search_by_name',
            'params': {'name': name},
            'filepath': filepath,
            'task_id': self.request.id,
            'recipe': recipe_data,
        }
    except Exception as e:
        return {
            'status': 'error',
            'api': 'themealdb',
            'action': 'search_by_name',
            'params': {'name': name},
            'error': str(e),
            'task_id': self.request.id,
        }


@shared_task(name='celery_tasks.external_api.get_random_meal', bind=True)
def get_random_meal(self) -> Dict:
    """
    Получить случайный рецепт из TheMealDB
    
    Returns:
        dict: Результат с информацией о сохраненном файле и данными рецепта
    """
    try:
        handler = TheMealDBHandler(api_key=os.getenv('THEMEALDB_API_KEY', '1'))
        result = handler.random_meal()
        
        filepath = save_api_response('themealdb', 'random_meal', result)
        
        # Извлечь данные рецепта для отображения
        recipe_data = None
        if result and 'meals' in result and result['meals']:
            meal = result['meals'][0]
            # Собрать ингредиенты
            ingredients = []
            for i in range(1, 21):
                ingredient = meal.get(f'strIngredient{i}')
                measure = meal.get(f'strMeasure{i}')
                if ingredient and ingredient.strip():
                    ingredients.append({
                        'name': ingredient.strip(),
                        'measure': measure.strip() if measure else ''
                    })
            
            recipe_data = {
                'name': meal.get('strMeal', ''),
                'image': meal.get('strMealThumb', ''),
                'category': meal.get('strCategory', ''),
                'area': meal.get('strArea', ''),
                'instructions': meal.get('strInstructions', ''),
                'youtube': meal.get('strYoutube', ''),
                'source': meal.get('strSource', 'TheMealDB'),
                'ingredients': ingredients,
            }
        
        return {
            'status': 'success',
            'api': 'themealdb',
            'action': 'random_meal',
            'params': {},
            'filepath': filepath,
            'task_id': self.request.id,
            'recipe': recipe_data,
        }
    except Exception as e:
        return {
            'status': 'error',
            'api': 'themealdb',
            'action': 'random_meal',
            'params': {},
            'error': str(e),
            'task_id': self.request.id,
        }


@shared_task(name='celery_tasks.external_api.search_product', bind=True)
def search_product(self, query: str) -> Dict:
    """
    Поиск продукта в Open Food Facts
    
    Args:
        query: Поисковый запрос
        
    Returns:
        dict: Результат поиска с информацией о сохраненном файле
    """
    try:
        handler = OpenFoodFactsHandler()
        result = handler.search_product(query)
        
        filepath = save_api_response('openfoodfacts', 'search_product', result)
        
        return {
            'status': 'success',
            'api': 'openfoodfacts',
            'action': 'search_product',
            'params': {'query': query},
            'filepath': filepath,
            'task_id': self.request.id,
        }
    except Exception as e:
        return {
            'status': 'error',
            'api': 'openfoodfacts',
            'action': 'search_product',
            'params': {'query': query},
            'error': str(e),
            'task_id': self.request.id,
        }


@shared_task(name='celery_tasks.external_api.health_check', bind=True)
def health_check(self) -> Dict:
    """
    Проверка работоспособности Celery worker
    
    Returns:
        dict: Статус worker
    """
    return {
        'status': 'healthy',
        'worker': self.request.hostname,
        'task_id': self.request.id,
    }
