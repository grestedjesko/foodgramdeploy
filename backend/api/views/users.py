from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import CustomUser
from api.serializers.users import CustomUserSerializer


class CustomUserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    @action(detail=False, methods=['put'],
            permission_classes=[IsAuthenticated])
    def me_avatar(self, request):
        user = request.user
        avatar = request.data.get('avatar')
        if not avatar:
            return Response({'avatar': ['Это поле обязательно.']},
                            status=status.HTTP_400_BAD_REQUEST)
        user.avatar = avatar
        user.save()
        return Response(CustomUserSerializer(user,
                                             context={'request': request}).data)

    @me_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
