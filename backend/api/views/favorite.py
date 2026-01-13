from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from recipes.models import Recipe, Favorite
from api.serializers.favorite import FavoriteSerializer
from api.services.cache_manager import get_cache_manager


class FavoriteMixin:
    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в избранном.'},
                                status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = FavoriteSerializer(recipe)
            
            try:
                cache = get_cache_manager()
                if cache:
                    cache.delete_pattern(f"recipes:list:*user_id*{user.id}*")
                    cache.delete_pattern(f"recipes:detail:*")
            except Exception:
                pass
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        favorite = Favorite.objects.filter(user=user, recipe=recipe).first()
        if not favorite:
            return Response({'errors': 'Рецепта не было в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)
        favorite.delete()
        
        try:
            cache = get_cache_manager()
            if cache:
                cache.delete_pattern(f"recipes:list:*user_id*{user.id}*")
                cache.delete_pattern(f"recipes:detail:*")
        except Exception:
            pass
        
        return Response(status=status.HTTP_204_NO_CONTENT)
