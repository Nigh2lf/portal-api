from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.modules.auth.service import build_permissions, display_name


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["name"] = display_name(user)
        token["permissions"] = build_permissions(user)
        return token
