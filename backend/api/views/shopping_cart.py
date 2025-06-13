from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from recipes.models import Recipe, ShoppingCart
from api.serializers.shopping_cart import ShoppingCartSerializer
from django.http import HttpResponse
from recipes.models import IngredientInRecipe


class ShoppingCartMixin:
    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в корзине.'}, status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe).first()
        if not cart_item:
            return Response({'errors': 'Рецепта не было в корзине.'}, status=status.HTTP_400_BAD_REQUEST)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        recipes = Recipe.objects.filter(in_shopping_carts__user=user)
        ingredients = {}

        for recipe in recipes:
            for item in IngredientInRecipe.objects.filter(recipe=recipe):
                name = item.ingredient.name
                unit = item.ingredient.measurement_unit
                amount = item.amount

                key = (name, unit)
                ingredients[key] = ingredients.get(key, 0) + amount

        lines = ['Список покупок:\n']
        for (name, unit), amount in ingredients.items():
            lines.append(f'• {name} — {amount} {unit}')

        content = '\n'.join(lines)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=shopping_list.txt'
        return response
