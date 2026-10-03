"""ViewSets base do projeto.

Três peças:

- ``BaseViewSetMixin`` — o que ``BaseModelViewSet`` e ``BaseViewSet`` têm em
  comum: filtro dos endpoints de lookup (``allowed_lookups``) e os helpers de
  raw SQL.
- ``BaseModelViewSet`` — CRUD completo (``ModelViewSet``) com envelope,
  transação atômica na escrita, soft delete e auditoria.
- ``BaseViewSet`` — sem CRUD automático; para ViewSets que só expõem
  ``@action`` (relatórios, painéis, endpoints de serviço).

Diferenças vs ModelViewSet padrão:
- Todas as respostas (sucesso e erro) seguem o envelope:
    {success, status, message, data, error}
- Erros são tratados pelo `envelope_exception_handler` (configurado em settings),
  então estes viewsets não sobrescrevem `dispatch`.
- `destroy` faz soft-delete (`instance.delete(deleted_by=user)`) nos models que
  suportam; nos demais, o delete padrão do Django.
- Permissão é declarada com ``permission_classes = [IsAuthenticated,
  CustomPermissionClass]`` + ``view_name`` (ver docs/auth-permissions.md).
"""

import inspect

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.response import Response

from core.classes.exception_handler import envelope_success
from core.classes.pagination import StandardPagination
from core.modules.lookup.view import LookupViewSet


class BaseViewSetMixin:
    """Recursos compartilhados pelas ViewSets base do projeto.

    Concentra o que ``BaseModelViewSet`` e ``BaseViewSet`` têm em comum:
    filtragem dos endpoints de lookup via ``allowed_lookups`` e os helpers de
    raw SQL.

    Padrão de permissões do projeto — ``CustomPermissionClass`` + ``view_name``::

        class ProductViewSet(BaseModelViewSet):
            view_name = "product"
            router_user = ["ADMIN"]          # opcional: papéis permitidos
            view_read = True                  # opcional: todo método exige só READ
            permission_classes = [IsAuthenticated, CustomPermissionClass]

    O método HTTP vira o tipo de permissão exigido (GET → ``READ``, POST →
    ``CREATE``, PUT/PATCH → ``UPDATE``, DELETE → ``DELETE``), consultado em
    ``Profile`` → ``ProfilePermission`` → ``Permission``.

    Atributos:
        allowed_lookups: Controla quais endpoints ``lookup_*`` herdados de
            ``LookupViewSet`` ficam acessíveis nesta ViewSet.
            - ``None``: expõe todos os lookups.
            - ``list[str]``: expõe somente os lookups cujos nomes estão na
              lista (ex.: ``["lookup_usuario"]``).
            - ``[]`` (padrão): oculta todos os lookups.
            Actions que não comecem com ``lookup_`` nunca são filtradas.
            Expor um lookup **não** o libera: ele continua sujeito ao
            ``permission_classes`` da ViewSet.
    """

    allowed_lookups: list[str] | None = []

    @classmethod
    def get_extra_actions(cls):
        """Retorna as ``@action`` extras que o router deve registrar.

        Sobrescreve o método do DRF para filtrar dinamicamente os endpoints
        de lookup conforme ``cls.allowed_lookups``. O filtro acontece no
        momento de montagem das URLs, então lookups não autorizados nem
        chegam a ter rota registrada (não retornam 403/404 — simplesmente
        não existem para a ViewSet).

        A regra de filtragem é:
            - Se ``allowed_lookups`` é ``None``, devolve a lista completa.
            - Caso contrário, mantém qualquer action que **não** comece com
              ``lookup_`` e, dentre as que começam, somente as nomeadas em
              ``allowed_lookups``.
        """
        actions = super().get_extra_actions()
        if cls.allowed_lookups is None:
            return actions
        return [
            a
            for a in actions
            if not a.__name__.startswith("lookup_") or a.__name__ in cls.allowed_lookups
        ]

    # ------------------------------------------------------------------
    # Raw SQL (relatórios)
    # ------------------------------------------------------------------
    def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        """Executa um SQL puro e retorna as linhas como dicts.

        ``sql`` é a query e ``params`` são os valores que substituem os
        placeholders ``%s``, evitando SQL injection. Nunca interpole valor de
        request na string da query.
        """
        from core.services.execute_sql import execute_sql

        return execute_sql(sql, params)

    def paginated_raw_sql(self, query, params, request, *, count_field="total_registros"):
        """Executa raw SQL com paginação opcional baseada em ``?page=&page_size=``.

        Sem ``page`` retorna a lista crua. Com ``page`` aplica LIMIT/OFFSET na
        query e devolve o mesmo dict que a ``StandardPagination`` produz
        (``count``, ``total_pages``, ``page``, ``page_size``, ``next``,
        ``previous``, ``results``) — para o front não notar diferença entre um
        endpoint de ORM e um de raw SQL.

        A query deve incluir ``COUNT(*) OVER() AS total_registros`` (ou outro
        alias passado em ``count_field``) para evitar uma segunda viagem ao
        banco, e **não** deve trazer ``LIMIT``/``OFFSET`` inline.

        O retorno é um dict/lista cru — cabe à action embrulhar no envelope::

            return envelope_success(data=self.paginated_raw_sql(SQL, params, request))
        """
        pagination = (getattr(self, "pagination_class", None) or StandardPagination)()
        page_param = pagination.page_query_param
        size_param = pagination.page_size_query_param

        raw_page = request.query_params.get(page_param)
        if raw_page is None:
            rows = self.execute_query(query, params)
            for row in rows:
                row.pop(count_field, None)
            return rows

        try:
            page_number = max(int(raw_page), 1)
        except (TypeError, ValueError):
            page_number = 1

        try:
            page_size = min(
                max(int(request.query_params.get(size_param, pagination.page_size)), 1),
                pagination.max_page_size,
            )
        except (TypeError, ValueError):
            page_size = pagination.page_size

        offset = (page_number - 1) * page_size
        rows = self.execute_query(
            f"{query} LIMIT %s OFFSET %s",  # noqa: S608 - query vem do código; valores por %s
            [*params, page_size, offset],
        )

        count = rows[0][count_field] if rows else 0
        for row in rows:
            row.pop(count_field, None)

        base_url = request.build_absolute_uri(request.path)
        total_pages = -(-count // page_size) if page_size else 0

        next_url = None
        if offset + page_size < count:
            nxt = request.GET.copy()
            nxt[page_param] = page_number + 1
            next_url = f"{base_url}?{nxt.urlencode()}"

        previous_url = None
        if page_number > 1:
            prev = request.GET.copy()
            if page_number - 1 == 1:
                prev.pop(page_param, None)
            else:
                prev[page_param] = page_number - 1
            previous_url = f"{base_url}?{prev.urlencode()}"

        return {
            "count": count,
            "total_pages": total_pages,
            "page": page_number,
            "page_size": page_size,
            "next": next_url,
            "previous": previous_url,
            "results": rows,
        }

    # Mantido por compatibilidade com actions existentes que usam este helper.
    def _response_format(self, success, status, message=None, data=None, error=None):
        if success:
            return envelope_success(data=data, message=message or "", http_status=status)
        return Response(
            {
                "success": False,
                "status": status,
                "message": message,
                "data": data,
                "error": error,
            },
            status=status,
        )


class BaseModelViewSet(BaseViewSetMixin, viewsets.ModelViewSet, LookupViewSet):
    """ViewSet base do projeto para CRUD completo.

    Combina o CRUD do ``ModelViewSet`` (envelopado e atômico na escrita) com os
    endpoints de lookup do ``LookupViewSet``. Os recursos compartilhados vêm de
    ``BaseViewSetMixin`` — veja lá o padrão de permissão e ``allowed_lookups``.

    Filtros / busca / ordenação (já habilitados via ``DEFAULT_FILTER_BACKENDS``)::

        class ProductViewSet(BaseModelViewSet):
            queryset = Product.objects.all()
            serializer_class = ProductSerializer
            filterset_fields = ["category", "is_active"]   # django-filter
            search_fields = ["name", "description"]         # ?search=...
            ordering_fields = ["name", "created_at"]        # ?ordering=...
            ordering = ["-created_at"]                       # default

    Paginação (default ``StandardPagination``): ``?page=2&page_size=50``.

    Actions públicas (pré-login) continuam saindo do padrão via
    ``get_permissions`` ou ``permission_classes`` na própria ``@action``.
    """

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        res = super().create(request, *args, **kwargs)
        return envelope_success(data=res.data, http_status=res.status_code)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        res = super().update(request, *args, **kwargs)
        return envelope_success(data=res.data, http_status=res.status_code)

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        return envelope_success(data=res.data, http_status=res.status_code)

    def retrieve(self, request, *args, **kwargs):
        res = super().retrieve(request, *args, **kwargs)
        return envelope_success(data=res.data, http_status=res.status_code)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        res = super().destroy(request, *args, **kwargs)
        return envelope_success(
            message=_("Registro deletado com sucesso!"),
            http_status=res.status_code,
        )

    def perform_destroy(self, instance):
        # ``deleted_by`` só existe em models com soft delete (``SoftDeleteMixin``
        # ou ``delete`` próprio, como ``User``). Nos demais, delete padrão.
        if "deleted_by" in inspect.signature(instance.delete).parameters:
            instance.delete(deleted_by=self.request.user)
        else:
            instance.delete()

    # ------------------------------------------------------------------
    # Auditoria automática (created_by / updated_by do AbstractModel)
    # ------------------------------------------------------------------
    def _audit_kwargs(self, field_name):
        """Retorna ``{field_name: request.user}`` se o model tem o campo e o
        usuário está autenticado. Caso contrário, dict vazio."""
        model = getattr(self, "queryset", None)
        model = model.model if model is not None else None
        if model is None:
            serializer_cls = getattr(self, "serializer_class", None)
            model = getattr(getattr(serializer_cls, "Meta", None), "model", None)
        if model is None:
            return {}
        try:
            model._meta.get_field(field_name)
        except Exception:  # noqa: BLE001 - get_field lança FieldDoesNotExist
            return {}
        user = getattr(self.request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return {}
        return {field_name: user}

    def perform_create(self, serializer):
        serializer.save(**self._audit_kwargs("created_by"))

    def perform_update(self, serializer):
        serializer.save(**self._audit_kwargs("updated_by"))


class BaseViewSet(BaseViewSetMixin, LookupViewSet):
    """ViewSet base do projeto para actions customizadas.

    Equivalente ao ``BaseModelViewSet``, porém sem o CRUD automático
    (``list``/``create``/``retrieve``/``update``/``destroy``) — herda de
    ``ViewSet`` via ``LookupViewSet``. Use quando a ViewSet expõe apenas
    ``@action`` customizadas e não está atrelada a um ``queryset``/
    ``serializer_class``: relatórios, painéis, endpoints de serviço.

    Como não há CRUD gerado, **cada action monta a própria resposta** — sempre
    no envelope, via ``envelope_success`` (ou ``self._response_format``)::

        class RelatorioViewSet(BaseViewSet):
            view_name = "relatorio"
            permission_classes = [IsAuthenticated, CustomPermissionClass]

            @action(detail=False, methods=["get"])
            def resumo(self, request):
                return envelope_success(data=self.paginated_raw_sql(SQL, [], request))

    Escrita não é atômica por padrão aqui (não há ``create``/``update`` gerado):
    decore a action com ``@transaction.atomic`` quando ela gravar.

    Os recursos compartilhados vêm de ``BaseViewSetMixin`` — veja lá o padrão
    de permissão e ``allowed_lookups``.
    """

    pagination_class = StandardPagination
