from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models.user import CustomUser
from api.views.subscription import SubscriptionMixin
from api.serializers.users import CustomUserSerializer
from api.serializers.users import AvatarSerializer
from rest_framework.authtoken.models import Token
from django.conf import settings
from rest_framework.permissions import AllowAny
import secrets, urllib.parse, requests
from django.shortcuts import redirect
from api.services.cache_manager import cache_queryset, get_cache_manager, CacheTTL

GITHUB_AUTH_URL  = "https://github.com/login/oauth/authorize"  # :contentReference[oaicite:0]{index=0}
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"  # :contentReference[oaicite:1]{index=1}
GITHUB_USER_URL  = "https://api.github.com/user"  # :contentReference[oaicite:2]{index=2}


class CustomUserViewSet(UserViewSet, SubscriptionMixin):
    lookup_field = 'id'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    
    @cache_queryset("users:list", ttl=CacheTTL.TEN_MINUTES)
    def list(self, request, *args, **kwargs):
        """Список пользователей с кэшированием"""
        return super().list(request, *args, **kwargs)
    
    @cache_queryset("users:detail", ttl=CacheTTL.TEN_MINUTES)
    def retrieve(self, request, *args, **kwargs):
        """Детали пользователя с кэшированием"""
        return super().retrieve(request, *args, **kwargs)

    @action(
        methods=['get', 'put', 'patch', 'delete'],
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(detail=False, methods=['put'], url_path='me/avatar', permission_classes=[IsAuthenticated])
    def set_avatar(self, request):
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        try:
            cache = get_cache_manager()
            if cache:
                cache.delete_pattern(f"users:list:*")
                cache.delete_pattern(f"users:detail:*")
        except Exception:
            pass
        
        return Response(serializer.data, status=status.HTTP_200_OK)

    @set_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        user.avatar.delete(save=True)
        
        try:
            cache = get_cache_manager()
            if cache:
                cache.delete_pattern(f"users:list:*")
                cache.delete_pattern(f"users:detail:*")
        except Exception:
            pass
        
        return Response(status=status.HTTP_204_NO_CONTENT)