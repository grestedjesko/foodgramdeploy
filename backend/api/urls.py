from rest_framework.routers import DefaultRouter
from django.urls import path, include

from api.views.recipes import IngredientViewSet, RecipeViewSet
from api.views.users import CustomUserViewSet
from api.views.github_auth import GitHubLoginView, GitHubCallbackView

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path("auth/github/login/", GitHubLoginView.as_view(), name="github-login"),
    path("auth/github/callback/", GitHubCallbackView.as_view(), name="github-callback"),
]
