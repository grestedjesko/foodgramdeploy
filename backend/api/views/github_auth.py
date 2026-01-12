from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.authtoken.models import Token
from users.models import CustomUser
import secrets, urllib.parse, requests

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


class GitHubLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        state = secrets.token_urlsafe(16)
        request.session["gh_state"] = state
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "false",
        }
        return redirect(f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(params)}")


class GitHubCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
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
            headers={"Authorization": f"Bearer {gh_token}"},
            timeout=5,
        ).json()

        username = user_json["login"]
        email = user_json.get("email") or f"{username}@users.noreply.github.com"

        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": user_json.get("name") or "GitHubUser"
            },
        )

        token, _ = Token.objects.get_or_create(user=user)

        return redirect(f"http://localhost/oauth/github?token={token.key}")
