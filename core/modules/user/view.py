from django.conf import settings
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import Profile, User
from core.modules.user.serializer import (
    ChangePasswordForgotSerializer,
    ForgotPasswordSerializer,
    SendVerificationCodeSerializer,
    UserDetailSerializer,
    UserListSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from core.modules.user.service import UserService
from core.serializers import ProfileLookupSerializer


class UserViewSet(BaseModelViewSet):
    view_name = "user"
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = UserSerializer
    allowed_lookups = ["lookup_profile"]
    search_fields = ["id", "email", "name"]
    ordering = ("id",)

    def get_permissions(self):
        # allow-any: cadastro, reset de senha e confirmação de e-mail são pré-login.
        # Throttle aplicado em get_throttles().
        if self.action in [
            "forgot_password",
            "change_password_forgot_password",
            "send_verification_code",
            "verify_email",
        ]:
            return [permissions.AllowAny()]
        # `profile` devolve o próprio usuário logado: não exige permissão de menu.
        if self.action == "profile":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_throttles(self):
        if self.action in ("forgot_password", "change_password_forgot_password"):
            self.throttle_scope = "forgot_password"
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action in ("retrieve", "profile"):
            return UserDetailSerializer
        return UserSerializer

    def get_queryset(self):
        return User.objects.filter(deleted_at__isnull=True)

    def create(self, request, *args, **kwargs):
        """
        Cadastra o usuário

        Returns:
            envelope com os dados do usuário criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o usuário; trocar a senha exige `old_password`

        Returns:
            envelope com os dados do usuário atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    @action(detail=False, methods=["get"], url_path="profile")
    def profile(self, request):
        """
        Retorna o usuário autenticado

        Returns:
            envelope com os dados do próprio usuário
        """
        serializer = self.get_serializer(request.user)
        return envelope_success(data=serializer.data)

    # allow-any: dispara o reset de senha por e-mail; o usuário não está logado.
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="forgot-password",
    )
    def forgot_password(self, request):
        """
        Envia o e-mail de reset de senha

        Returns:
            envelope com `{"worked": true}` — resposta genérica para evitar
            enumeração de e-mails
        """
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self._service().request_password_reset(serializer.validated_data["email"])
        return envelope_success(data={"worked": True})

    # allow-any: confirma a nova senha com hash + expiração do reset; sem login.
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="change-password-forgot-password",
    )
    def change_password_forgot_password(self, request):
        """
        Troca a senha a partir do token recebido por e-mail

        Returns:
            envelope com `{"worked": true}`
        """
        serializer = ChangePasswordForgotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        self._service().reset_password(
            data["email"], data["forgot_password_hash"], data["new_password"]
        )
        return envelope_success(data={"worked": True})

    @action(detail=False, methods=["get"], url_path="lookup-profile")
    def lookup_profile(self, request):
        """
        Lista os profiles ativos para preencher selects do formulário de usuário

        Returns:
            envelope com `[{key, value}]`
        """
        profiles = Profile.objects.filter(is_active=True)
        serializer = ProfileLookupSerializer(profiles, many=True)
        return envelope_success(data=serializer.data)

    # allow-any: reenvio do código de verificação de e-mail (pré-login).
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="send-verification-code",
    )
    def send_verification_code(self, request):
        """
        Reenvia o código de verificação para o e-mail informado

        Returns:
            envelope com `{"worked": true}`; 404 se
            EMAIL_VERIFICATION_REQUIRED estiver desligado
        """
        if not settings.EMAIL_VERIFICATION_REQUIRED:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = SendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self._service().resend_verification_code(serializer.validated_data["email"])
        return envelope_success(data={"worked": True})

    # allow-any: valida o código recebido por e-mail antes do primeiro login.
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.AllowAny],
        url_path="verify-email",
    )
    def verify_email(self, request):
        """
        Confirma o código enviado por e-mail

        Returns:
            envelope com `{"worked": true, "already_verified": bool}`; 404 se
            EMAIL_VERIFICATION_REQUIRED estiver desligado
        """
        if not settings.EMAIL_VERIFICATION_REQUIRED:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = self._service().verify_email(data["email"], data["code"])
        return envelope_success(
            data={"worked": True, "already_verified": result == "already_verified"}
        )

    def _service(self) -> UserService:
        return UserService(actor=getattr(self.request, "user", None))
