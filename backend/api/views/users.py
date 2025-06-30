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

GITHUB_AUTH_URL  = "https://github.com/login/oauth/authorize"  # :contentReference[oaicite:0]{index=0}
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"  # :contentReference[oaicite:1]{index=1}
GITHUB_USER_URL  = "https://api.github.com/user"  # :contentReference[oaicite:2]{index=2}


class CustomUserViewSet(UserViewSet, SubscriptionMixin):
    lookup_field = 'id'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

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
        return Response(serializer.data, status=status.HTTP_200_OK)

    @set_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny],
            url_path="github/login")
    def github_login(self, request):
        state = secrets.token_urlsafe(16)
        request.session["gh_state"] = state  # хранится в подписанной cookie
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "false",
        }
        print(settings.GITHUB_REDIRECT_URI)
        return redirect(f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(params)}")

    @action(detail=False, methods=["get"], permission_classes=[AllowAny],
            url_path="github/callback")
    def github_callback(self, request):
        if request.GET.get("state") != request.session.pop("gh_state", None):
            return Response({"detail": "Invalid state"}, status=400)

        code = request.GET.get("code")
        token_json = requests.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            timeout=5,
        ).json()
        gh_token = token_json.get("access_token")
        if not gh_token:
            return Response({"detail": "GitHub token error"}, status=400)

        user_json = requests.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {gh_token}",
                     "Accept": "application/vnd.github+json"},
            timeout=5,
        ).json()

        username = user_json["login"]
        email = user_json.get("email") or f"{username}@users.noreply.github.com"

        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": user_json.get("name", "")},
        )

        token, _ = Token.objects.get_or_create(user=user)

        return redirect(f"http://localhost/oauth/github?token={token.key}")
