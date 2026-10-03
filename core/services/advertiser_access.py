"""Acesso do anunciante à área logada do portal.

Anunciantes são ``User`` com ``role=USER`` e o perfil RBAC ``ANUNCIANTE``, que
reúne as permissões dos ``view_name`` do app ``advertiser``. O perfil é criado
por ``manage.py seed_advertiser_profile``; aqui só vinculamos o usuário.
"""

from core.models import Profile, UserProfile

ADVERTISER_PROFILE_NAME = "ANUNCIANTE"


def get_advertiser_profile():
    profile, _ = Profile.objects.get_or_create(name=ADVERTISER_PROFILE_NAME, defaults={"is_active": True})
    return profile


def grant_advertiser_access(user):
    """
    Vincula o usuário ao perfil ANUNCIANTE (idempotente)

    Args:
        user: User do anunciante

    Returns:
        UserProfile criado ou existente
    """
    link, _ = UserProfile.objects.get_or_create(user=user, profile=get_advertiser_profile())
    return link
