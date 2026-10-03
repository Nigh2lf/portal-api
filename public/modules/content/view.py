from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from core.classes.base_viewset import BaseViewSet
from core.classes.exception_handler import envelope_success
from core.classes.pagination import StandardPagination
from core.models import Portal
from public.modules.content.serializer import PublicPostDetailSerializer, PublicPostListSerializer, PublicTipSerializer
from public.modules.content.service import ContentService

POSTS_PAGE_SIZE = 9


class PublicPostPagination(StandardPagination):
    page_size = POSTS_PAGE_SIZE


class PublicContentMixin:
    def get_portal(self):
        portal = Portal.objects.filter(slug=self.kwargs.get("portal_slug"), is_active=True).first()
        if portal is None:
            raise NotFound("Portal não encontrado.")
        return portal


class PublicPostViewSet(PublicContentMixin, BaseViewSet):
    # allow-any: blog do site público (SSR), sem usuário logado; throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"
    pagination_class = PublicPostPagination
    lookup_field = "slug"
    lookup_value_regex = r"[a-z0-9-]+"

    def list(self, request, portal_slug=None):
        """
        Posts do blog visíveis no portal, paginados (`?page=`, `?page_size=`, padrão 9)

        Returns:
            envelope com `{count, total_pages, page, page_size, next, previous, results}`
        """
        portal = self.get_portal()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(ContentService(portal).posts(), request, view=self)
        dados = PublicPostListSerializer(page, many=True, context={"request": request}).data
        return envelope_success(data=paginator.get_paginated_response(dados).data)

    def retrieve(self, request, portal_slug=None, slug=None):
        """
        Post completo pelo slug (inclui `body` em HTML)

        Returns:
            envelope com o post; 404 se não publicado ou fora do escopo do portal
        """
        portal = self.get_portal()
        post = ContentService(portal).post_by_slug(slug)
        if post is None:
            raise NotFound("Post não encontrado.")
        return envelope_success(data=PublicPostDetailSerializer(post, context={"request": request}).data)


class PublicTipViewSet(PublicContentMixin, BaseViewSet):
    # allow-any: dicas do site público (SSR), sem usuário logado; throttle por IP.
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    def list(self, request, portal_slug=None):
        """
        Dicas ativas do portal (globais ou do próprio portal)

        Returns:
            envelope com `[{id, title, body, sort_order}]`
        """
        portal = self.get_portal()
        return envelope_success(data=PublicTipSerializer(ContentService(portal).tips(), many=True).data)
