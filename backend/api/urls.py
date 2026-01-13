from rest_framework.routers import DefaultRouter
from django.urls import path, include

from api.views.recipes import IngredientViewSet, RecipeViewSet
from api.views.users import CustomUserViewSet
from api.views.github_auth import GitHubLoginView, GitHubCallbackView
from api.views.password_reset import PasswordResetConfirmAPIView
from api.views.external_api import import_recipe, search_product, api_status
from api.views.celery_api import (
    celery_import_recipe,
    celery_search_product,
    celery_task_status,
    celery_health,
    celery_status,
)

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/password/reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='custom-password-reset-confirm'),

    path('auth/', include('djoser.urls.authtoken')),
    path("auth/github/login/", GitHubLoginView.as_view(), name="github-login"),
    path("auth/github/callback/", GitHubCallbackView.as_view(), name="github-callback"),
    
    # RabbitMQ endpoints (archived)
    path('external/import-recipe/', import_recipe, name='import-recipe'),
    path('external/search-product/', search_product, name='search-product'),
    path('external/status/', api_status, name='api-status'),
    
    # Celery endpoints
    path('celery/import-recipe/', celery_import_recipe, name='celery-import-recipe'),
    path('celery/search-product/', celery_search_product, name='celery-search-product'),
    path('celery/task-status/<str:task_id>/', celery_task_status, name='celery-task-status'),
    path('celery/health/', celery_health, name='celery-health'),
    path('celery/status/', celery_status, name='celery-status'),
]
