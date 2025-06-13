from rest_framework import viewsets, filters
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


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet, ShoppingCartMixin, FavoriteMixin):
    pagination_class = LimitPageNumberPagination
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly & IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeListSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = RecipeCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=request.user)
        output_serializer = RecipeListSerializer(recipe, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = RecipeCreateSerializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        output_serializer = RecipeListSerializer(serializer.instance, context={'request': request})
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
