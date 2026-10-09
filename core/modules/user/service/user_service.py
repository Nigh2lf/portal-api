import secrets
from contextlib import suppress
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import User, UserProfile
from core.services import (
    send_email_forgot_password,
    send_email_verification_code,
    send_email_welcome,
)

FORGOT_PASSWORD_TTL = timedelta(hours=1)


class UserService:
    def __init__(self, actor=None):
        self.actor = actor

    def create(self, validated_data):
        """
        Cria o usuário, vincula os profiles e dispara o e-mail de cadastro

        Args:
            validated_data: dados já validados pelo UserSerializer

        Returns:
            User
        """
        profiles = validated_data.pop("profiles", [])
        password = validated_data.pop("password")
        validated_data.pop("old_password", None)

        role = validated_data.pop("role", User.Role.USER) if self._actor_is_admin() else User.Role.USER
        is_active = validated_data.pop("is_active", True)

        user = User(**validated_data, is_active=is_active, role=role, is_staff=False)
        user.set_password(password)
        user.save()

        if profiles:
            self._sync_profiles(user, profiles)
        self._send_signup_email(user)
        return user

    def update(self, instance, validated_data):
        """
        Atualiza o usuário; a troca de senha exige a senha atual, salvo quando um ADMIN altera outro usuário

        Args:
            instance: usuário a atualizar
            validated_data: dados já validados pelo UserSerializer

        Returns:
            User
        """
        profiles = validated_data.pop("profiles", None)
        password = validated_data.pop("password", None)
        old_password = validated_data.pop("old_password", None)

        if not self._actor_is_admin():
            validated_data.pop("role", None)
            validated_data.pop("is_active", None)

        if password is not None:
            admin_editando_outro = self._actor_is_admin() and self.actor.pk != instance.pk
            if not admin_editando_outro and (not old_password or not instance.check_password(old_password)):
                raise serializers.ValidationError({"old_password": [_("Senha atual incorreta.")]})
            instance.set_password(password)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if profiles is not None:
            self._sync_profiles(instance, profiles)
        return instance

    def request_password_reset(self, email):
        """
        Gera o token de reset e envia o e-mail; silencioso se o e-mail não existe

        Args:
            email: e-mail informado no formulário
        """
        user = self._active_user(email)
        if user is None:
            return

        token = secrets.token_urlsafe(48)
        user.forgot_password_hash = token
        user.forgot_password_expire = timezone.now() + FORGOT_PASSWORD_TTL
        user.save(update_fields=["forgot_password_hash", "forgot_password_expire"])

        with suppress(Exception):  # noqa: BLE001 - falha de envio não pode vazar para o cliente
            send_email_forgot_password(user.email, user.name, token)

    def reset_password(self, email, token, new_password):
        """
        Troca a senha a partir do token de reset

        Args:
            email: e-mail do usuário
            token: hash recebido por e-mail
            new_password: nova senha
        """
        invalid = serializers.ValidationError({"detail": [_("Token inválido ou expirado.")]})
        user = self._active_user(email)
        if user is None:
            raise invalid

        stored_hash = user.forgot_password_hash or ""
        if not stored_hash or not secrets.compare_digest(stored_hash, token or ""):
            raise invalid
        if not user.forgot_password_expire or user.forgot_password_expire < timezone.now():
            raise invalid

        validate_password(new_password, user=user)

        user.set_password(new_password)
        user.save(update_fields=["password", "forgot_password_hash", "forgot_password_expire"])

    def resend_verification_code(self, email):
        """
        Gera e reenvia o código de verificação; silencioso se não houver o que enviar

        Args:
            email: e-mail informado no formulário
        """
        user = self._active_user(email)
        if user is None or user.email_verified:
            return

        code = user.generate_email_verification_code()
        user.save(update_fields=["email_verification_code", "email_verification_expire"])
        with suppress(Exception):  # noqa: BLE001 - idem
            send_email_verification_code(user.email, user.name, code)

    def verify_email(self, email, code):
        """
        Confirma o código de verificação e envia o welcome

        Args:
            email: e-mail do usuário
            code: código recebido por e-mail

        Returns:
            "verified" ou "already_verified"
        """
        invalid = serializers.ValidationError({"code": [_("Código inválido ou expirado.")]})
        user = self._active_user(email)
        if user is None:
            raise invalid
        if user.email_verified:
            return "already_verified"
        if not user.confirm_email_verification(code):
            raise invalid

        with suppress(Exception):  # noqa: BLE001 - idem
            send_email_welcome(user.email, user.name)
        return "verified"

    def _send_signup_email(self, user):
        """Envia o código de verificação ou o welcome, conforme EMAIL_VERIFICATION_REQUIRED."""
        if settings.EMAIL_VERIFICATION_REQUIRED:
            code = user.generate_email_verification_code()
            user.save(update_fields=["email_verification_code", "email_verification_expire"])
            with suppress(Exception):  # noqa: BLE001 - não quebrar cadastro por falha de e-mail
                send_email_verification_code(user.email, user.name, code)
        else:
            with suppress(Exception):  # noqa: BLE001 - idem
                send_email_welcome(user.email, user.name)

    def _actor_is_admin(self):
        return bool(self.actor) and getattr(self.actor, "role", None) == User.Role.ADMIN

    @staticmethod
    def _sync_profiles(user, profiles):
        """Reamarra os profiles do usuário: apaga os vínculos antigos e grava os novos."""
        UserProfile.objects.filter(user=user).delete()
        UserProfile.objects.bulk_create(
            [UserProfile(user=user, profile=profile) for profile in profiles]
        )

    @staticmethod
    def _active_user(email):
        """Busca o usuário ativo pelo e-mail; None se não existir."""
        return User.objects.filter(email=email, is_active=True, deleted_at__isnull=True).first()

    @staticmethod
    def summary():
        """
        Totais do painel: usuários cadastrados, com login liberado, que já entraram e por vínculo

        Returns:
            dict com ``total``, ``active``, ``logged_in``, ``of_published_advertisers`` e ``admins``
        """
        published = Q(advertiser_profile__is_published=True, advertiser_profile__deleted_at__isnull=True)
        return User.objects.filter(deleted_at__isnull=True).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            logged_in=Count("id", filter=Q(last_login__isnull=False)),
            of_published_advertisers=Count("id", filter=published),
            admins=Count("id", filter=Q(role=User.Role.ADMIN)),
        )
