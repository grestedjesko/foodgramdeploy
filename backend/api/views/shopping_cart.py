from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from recipes.models import Recipe, ShoppingCart
from api.serializers.shopping_cart import ShoppingCartSerializer
from django.http import HttpResponse
from recipes.models import IngredientInRecipe
from api.services.cache_manager import get_cache_manager, CacheTTL


class ShoppingCartMixin:
    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в корзине.'},
                                status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartSerializer(recipe)
            
            try:
                cache = get_cache_manager()
                if cache:
                    cache.delete_pattern(f"recipes:list:*user_id*{user.id}*")
                    cache.delete_pattern(f"shopping_cart:*user_id*{user.id}*")
            except Exception:
                pass
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe).first()
        if not cart_item:
            return Response({'errors': 'Рецепта не было в корзине.'},
                            status=status.HTTP_400_BAD_REQUEST)
        cart_item.delete()
        
        try:
            cache = get_cache_manager()
            if cache:
                cache.delete_pattern(f"recipes:list:*user_id*{user.id}*")
                cache.delete_pattern(f"shopping_cart:*user_id*{user.id}*")
        except Exception:
            pass
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок с кэшированием"""
        user = request.user
        
        cache = get_cache_manager()
        cache_key = f"shopping_cart:download:user_id:{user.id}"
        
        if cache:
            try:
                cached_content = cache.get(cache_key)
                if cached_content is not None:
                    print(f"✓ Список покупок из кэша: user_id={user.id}")
                    response = HttpResponse(cached_content, content_type='text/plain')
                    response['Content-Disposition'] = 'attachment; filename=shopping_list.txt'
                    return response
            except Exception as e:
                print(f"Ошибка получения из кэша: {e}")
        
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
        
        if cache:
            try:
                cache.set(cache_key, content, CacheTTL.FIVE_MINUTES)
                print(f"✓ Список покупок сохранен в кэш: user_id={user.id}")
            except Exception as e:
                print(f"Ошибка сохранения в кэш: {e}")
        
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=shopping_list.txt'
        return response
