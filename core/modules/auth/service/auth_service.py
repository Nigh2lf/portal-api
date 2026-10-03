from collections import defaultdict

from core.models import Permission

CRUD = ("create", "read", "update", "delete")


def build_permissions(user):
    """
    Monta o mapa de permissões CRUD do usuário, uma entrada por ``view_name``.

    Args:
        user: usuário autenticado.

    Returns:
        {"<view_name>": {"create": bool, "read": bool, "update": bool, "delete": bool}}
    """
    granted = set(
        Permission.objects.filter(profiles__users=user, profiles__is_active=True).values_list(
            "id", flat=True
        )
    )

    tree = defaultdict(lambda: dict.fromkeys(CRUD, False))
    for row in Permission.objects.filter(menu__view__isnull=False).values(
        "id", "menu__view", "type"
    ):
        crud = tree[row["menu__view"]]
        key = row["type"].lower()
        if key in crud:
            crud[key] = crud[key] or row["id"] in granted

    return dict(tree)


def display_name(user):
    """
    Nome exibido no app.

    Args:
        user: usuário autenticado.

    Returns:
        str: o nome cadastrado ou o e-mail como fallback.
    """
    return user.name or user.email
