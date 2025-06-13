from rest_framework import viewsets, filters
from recipes.models import Ingredient
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from api.serializers.recipes import (IngredientSerializer,
                                     RecipeListSerializer,
                                     RecipeCreateSerializer)
from recipes.models import Recipe
from api.views.shopping_cart import ShoppingCartMixin


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['^name']  # Поиск по началу названия


class RecipeViewSet(viewsets.ModelViewSet, ShoppingCartMixin):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeListSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
