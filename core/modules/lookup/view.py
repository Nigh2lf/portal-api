"""Endpoints de lookup compartilhados.

Ver ``core/classes/base_viewset.py`` para como cada ViewSet escolhe quais
lookups expõe (``allowed_lookups``).
"""

from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from core.classes.exception_handler import envelope_success
from core.models import User
from core.modules.lookup.serializer import UserLookupSerializer

#: Máximo de registros retornados por qualquer lookup.
LOOKUP_LIMIT = 100


class LookupViewSet(ViewSet):
    """Centraliza os endpoints de lookup do sistema.

    Cada action exposta aqui segue a convenção de nome ``lookup_<entidade>``
    e ``url_path="lookup-<entidade>"``, retornando uma lista enxuta de
    registros ativos para preencher selects/autocompletes do front-end.
    Todos aceitam o query param opcional ``search`` para filtragem por
    nome (``icontains``).

    Esta classe é combinada em ``BaseModelViewSet`` / ``BaseViewSet`` via
    herança múltipla, de modo que toda ViewSet do projeto herda os lookups.
    Para escolher quais uma ViewSet específica expõe, defina
    ``allowed_lookups`` na classe filha (ver ``BaseViewSetMixin``).

    Convenção ao adicionar um novo lookup:
        - Nome do método deve começar com ``lookup_`` (caso contrário o
          filtro de ``allowed_lookups`` não atua sobre ele e o endpoint fica
          sempre visível).
        - Use ``@action(detail=False, methods=["get"], url_path="lookup-...")``.
        - Responda com ``envelope_success(data=serializer.data)``.

    **Não declare ``permission_classes`` aqui.** O atributo apareceria no MRO
    de toda ViewSet do projeto e faria os checks ``core.E001``/``core.E003``
    (que varrem o MRO atrás de uma declaração explícita) pararem de acusar
    ViewSets sem permissão. A permissão de cada lookup vem do
    ``permission_classes`` da ViewSet que o expõe — normalmente
    ``CustomPermissionClass``, que exige a permissão ``READ`` do ``view_name``.
    """

    @action(detail=False, methods=["get"], url_path="lookup-usuario")
    def lookup_usuario(self, request, *args, **kwargs):
        search = request.query_params.get("search")

        users = User.objects.filter(is_active=True).order_by("name")
        if search:
            users = users.filter(Q(name__icontains=search) | Q(email__icontains=search))

        serializer = UserLookupSerializer(users[:LOOKUP_LIMIT], many=True)
        return envelope_success(data=serializer.data)
