"""Paginação padrão do projeto.

Mantém o envelope ``{success, status, message, data, error}`` do projeto:
o ``data`` vira um objeto com ``count``, ``next``, ``previous``, ``page``,
``page_size``, ``total_pages`` e ``results``.

Uso em uma viewset (opcional — já é default em ``REST_FRAMEWORK``)::

    class FooViewSet(BaseModelViewSet):
        pagination_class = StandardPagination

Query params suportados:

- ``?page=2``
- ``?page_size=50``  (máximo configurável via ``MAX_PAGE_SIZE``, default 100)
"""

from __future__ import annotations

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
