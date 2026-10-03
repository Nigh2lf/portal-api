from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import Profile, User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    old_password = serializers.CharField(write_only=True, required=False)
    profiles = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Profile.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "profile_image",
            "is_active",
            "role",
            "profiles",
            "password",
            "old_password",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        )

    def validate_password(self, value):
        validate_password(value, user=self.instance)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": [_("Senha é obrigatória.")]})
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "profile_image",
            "is_active",
            "role",
            "created_at",
        )


class UserDetailSerializer(serializers.ModelSerializer):
    profiles = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "profile_image",
            "is_active",
            "role",
            "email_verified",
            "profiles",
            "created_at",
            "updated_at",
        )


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ChangePasswordForgotSerializer(serializers.Serializer):
    email = serializers.EmailField()
    forgot_password_hash = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class SendVerificationCodeSerializer(serializers.Serializer):
    """Solicita reenvio do código de verificação de e-mail."""

    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):
    """Confirma o código de verificação enviado por e-mail."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=12)
