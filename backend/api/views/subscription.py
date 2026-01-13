from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from users.models.subscription import Subscription
from users.models.user import CustomUser
from api.serializers.subscription import (
    SubscriptionCreateSerializer,
    AuthorWithRecipesSerializer
)
from api.services.cache_manager import cache_queryset, get_cache_manager, CacheTTL


class SubscriptionMixin:
    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(CustomUser, id=id)

        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data={'user': user.id, 'author': author.id}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            response_serializer = AuthorWithRecipesSerializer(author,
                                                              context={'request': request})
            
            try:
                cache = get_cache_manager()
                if cache:
                    cache.delete_pattern(f"subscriptions:*user_id*{user.id}*")
                    cache.delete_pattern(f"users:list:*")
                    cache.delete_pattern(f"users:detail:*")
            except Exception:
                pass
            
            return Response(response_serializer.data,
                            status=status.HTTP_201_CREATED)

        subscription = Subscription.objects.filter(user=user, author=author).first()
        if not subscription:
            return Response({'error': 'Вы не подписаны на этого пользователя.'},
                            status=status.HTTP_400_BAD_REQUEST)
        subscription.delete()
        
        try:
            cache = get_cache_manager()
            if cache:
                cache.delete_pattern(f"subscriptions:*user_id*{user.id}*")
                cache.delete_pattern(f"users:list:*")
                cache.delete_pattern(f"users:detail:*")
        except Exception:
            pass
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    @cache_queryset("subscriptions:list", ttl=CacheTTL.FIVE_MINUTES)
    def subscriptions(self, request):
        """Список подписок пользователя с кэшированием"""
        queryset = CustomUser.objects.filter(subscribers__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = AuthorWithRecipesSerializer(page,
                                                 many=True,
                                                 context={'request': request})
        return self.get_paginated_response(serializer.data)
