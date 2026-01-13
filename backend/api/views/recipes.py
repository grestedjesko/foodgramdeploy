from rest_framework import viewsets
from recipes.models import Ingredient
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from api.serializers.recipes import (IngredientSerializer,
                                     RecipeListSerializer,
                                     RecipeCreateSerializer)
from recipes.models import Recipe
from api.views.shopping_cart import ShoppingCartMixin
from api.views.favorite import FavoriteMixin
from django_filters.rest_framework import DjangoFilterBackend
from api.views.filters import RecipeFilter, IngredientFilter
from rest_framework.response import Response
from rest_framework import status
from api.pagination import LimitPageNumberPagination
from rest_framework.decorators import action
from api.permissions import IsAuthorOrReadOnly
from api.services.cache_manager import cache_queryset, CacheInvalidationMixin, CacheTTL


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    pagination_class = None
    
    @cache_queryset("ingredients:list", ttl=CacheTTL.DAY)
    def list(self, request, *args, **kwargs):
        """Список ингредиентов с кэшированием (редко меняются)"""
        return super().list(request, *args, **kwargs)
    
    @cache_queryset("ingredients:detail", ttl=CacheTTL.DAY)
    def retrieve(self, request, *args, **kwargs):
        """Детали ингредиента с кэшированием"""
        return super().retrieve(request, *args, **kwargs)


class RecipeViewSet(CacheInvalidationMixin, viewsets.ModelViewSet, ShoppingCartMixin, FavoriteMixin):
    pagination_class = LimitPageNumberPagination
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly & IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    
    # Паттерны для инвалидации кэша при изменениях
    cache_key_patterns = [
        "recipes:list:*",
        "recipes:detail:*"
    ]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeListSerializer
        return RecipeCreateSerializer
    
    @cache_queryset("recipes:list", ttl=CacheTTL.FIVE_MINUTES)
    def list(self, request, *args, **kwargs):
        """Список рецептов с кэшированием"""
        return super().list(request, *args, **kwargs)
    
    @cache_queryset("recipes:detail", ttl=CacheTTL.TEN_MINUTES)
    def retrieve(self, request, *args, **kwargs):
        """Детали рецепта с кэшированием"""
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = RecipeCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=request.user)
        output_serializer = RecipeListSerializer(recipe, context={'request': request})
    
        self.invalidate_cache()
        
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = RecipeCreateSerializer(instance,
                                            data=request.data,
                                            partial=partial,
                                            context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        output_serializer = RecipeListSerializer(serializer.instance,
                                                 context={'request': request})
        return Response(output_serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return Response({'short-link': short_link})
