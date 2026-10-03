from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from core.models import Profile, ProfilePermission


def revoke_profile_tokens(profile):
    """Blacklista os refresh tokens dos usuários do profile, forçando novo login."""
    outstanding = OutstandingToken.objects.filter(user__user_profiles__profile=profile)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding],
        ignore_conflicts=True,
    )


class ProfileService:
    def create(self, validated_data):
        """
        Cria o profile e vincula as permissions recebidas

        Args:
            validated_data: dados já validados pelo ProfileSerializer

        Returns:
            Profile
        """
        permissions = validated_data.pop("permissions", [])
        profile = Profile.objects.create(**validated_data)

        if permissions:
            self._sync_permissions(profile, permissions)
        return profile

    def update(self, instance, validated_data):
        """
        Atualiza o profile e revoga os tokens dos usuários vinculados;
        enviar `permissions` substitui a lista inteira

        Args:
            instance: profile a atualizar
            validated_data: dados já validados pelo ProfileSerializer

        Returns:
            Profile
        """
        permissions = validated_data.pop("permissions", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if permissions is not None:
            self._sync_permissions(instance, permissions)

        revoke_profile_tokens(instance)
        return instance

    @staticmethod
    def _sync_permissions(profile, permissions):
        """Reamarra as permissions do profile: apaga os vínculos antigos e grava os novos."""
        ProfilePermission.objects.filter(profile=profile).delete()
        ProfilePermission.objects.bulk_create(
            [
                ProfilePermission(profile=profile, permission=permission)
                for permission in permissions
            ]
        )
