from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class CustomPermissionClass(BasePermission):
    """Permissão dinâmica: lê ``UserProfile`` → ``Profile`` → ``ProfilePermission``.

    Atributos lidos da ViewSet:

    - ``view_name`` (obrigatório) — casa com ``Menu.view``. Sem ele, nega tudo
      (fail-closed).
    - ``router_user`` (opcional) — lista de ``User.role`` que podem acessar a
      rota (ex.: ``["ADMIN"]``). Papel fora da lista recebe 403 antes mesmo de
      consultar as permissões.
    - ``view_read`` (opcional, default ``False``) — quando ``True``, **qualquer**
      método HTTP exige apenas a permissão ``READ``. Padrão de painel: quem
      enxerga a tela também opera nela.
    """

    # Mapeamento de métodos HTTP para tipos de permissão
    METHOD_PERMISSION_MAP = {
        "GET": ["READ"],  # list e retrieve compartilham READ
        "POST": ["CREATE"],
        "PUT": ["UPDATE"],
        "PATCH": ["UPDATE"],
        "DELETE": ["DELETE"],
        "OPTIONS": ["OPTIONS"],
    }

    def has_permission(self, request, view):
        # Usuários não autenticados não têm permissão
        if not request.user or not request.user.is_authenticated:
            self._raise_permission_denied()

        # # Bypass para o papel ADMIN (papel de negócio, não /admin/).
        # if request.user.role == "ADMIN":
        #     return True

        # router_user — restringe a rota a papéis específicos (User.role).
        router_user = getattr(view, "router_user", None)
        if router_user and request.user.role not in router_user:
            self._raise_permission_denied()

        # Se a view não tiver view_name definido, NEGA acesso (fail-closed).
        # Antes liberávamos por default, o que abria o sistema caso o dev esquecesse
        # de declarar a permissão. Agora forçamos a declaração explícita.
        view_name = getattr(view, "view_name", None)
        if not view_name:
            self._raise_permission_denied()

        # view_read=True colapsa todos os métodos em READ (se vê, opera).
        method = "GET" if getattr(view, "view_read", False) else request.method

        # Obtém os tipos de permissão necessários para este método
        required_permission_types = self.METHOD_PERMISSION_MAP.get(method, [])
        if not required_permission_types:
            self._raise_permission_denied()

        # Obtém todos os perfis do usuário
        user_profiles = request.user.user_profiles.filter(profile__is_active=True).select_related(
            "profile"
        )

        # Se o usuário não tem perfis, não tem permissão
        if not user_profiles.exists():
            self._raise_permission_denied()

        # Obtém todos os IDs dos perfis do usuário
        profile_ids = user_profiles.values_list("profile_id", flat=True)

        # Busca as permissões dos perfis do usuário
        from core.models import ProfilePermission

        permissions = ProfilePermission.objects.filter(
            profile_id__in=profile_ids,
            permission__menu__view=view_name,
            permission__type__in=required_permission_types,
        ).select_related("permission", "permission__menu")

        # Se encontrou alguma permissão, permite acesso
        return permissions.exists()

    def _raise_permission_denied(self):
        raise PermissionDenied(
            {
                "success": False,
                "status": 403,
                "message": "Sem permissão para acessar o recurso.",
                "data": {},
                "error": {},
            }
        )


class SafeDefaultPermission(BasePermission):
    """Rede de segurança contra ViewSets sem ``permission_classes`` declarado.

    Esta classe é incluída no ``DEFAULT_PERMISSION_CLASSES`` do DRF. Como o DRF
    só usa o default global quando o ViewSet **não** declara seu próprio
    ``permission_classes`` nem sobrescreve ``get_permissions``, a presença
    desta classe na execução prova que o dev esqueceu de configurar.

    Comportamento:
    - GET / HEAD / OPTIONS → permite (mantém compatibilidade com leituras).
    - POST / PUT / PATCH / DELETE → **bloqueia**.

    O bloqueio é redundante com o ``system check`` de ``core.checks`` (que
    derruba o boot), mas serve de defesa em profundidade caso o check seja
    silenciado.
    """

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
    message = (
        "ViewSet sem permission_classes declarado. "
        "Operações destrutivas estão bloqueadas pela rede de segurança "
        "(SafeDefaultPermission). Declare permission_classes na classe."
    )

    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS
