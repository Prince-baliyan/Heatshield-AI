from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    SafeUserSerializer,
    StudentRegistrationSerializer,
)


def _validation_error(serializer):
    return Response(
        {
            "error": {
                "code": "INVALID_REQUEST",
                "message": "The request contains invalid fields.",
                "details": serializer.errors,
            }
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"csrfToken": get_token(request._request)})


@method_decorator(csrf_protect, name="dispatch")
class StudentRegistrationView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            return Response(
                {
                    "error": {
                        "code": "ACCOUNT_CONFLICT",
                        "message": "A username or email is already in use.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {"user": SafeUserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        user = authenticate(
            request=request._request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_CREDENTIALS",
                        "message": "Invalid username or password.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request._request, user)
        return Response(
            {
                "user": SafeUserSerializer(user).data,
                "csrfToken": get_token(request._request),
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        logout(request._request)
        return Response(
            {
                "detail": "Successfully logged out.",
                "csrfToken": get_token(request._request),
            }
        )


class CurrentUserView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "Authentication is required.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response({"user": SafeUserSerializer(request.user).data})
