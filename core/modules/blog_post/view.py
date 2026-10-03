from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import BlogPost
from core.modules.blog_post.serializer import (
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogPostSerializer,
)
from core.modules.blog_post.service import BlogPostService


class BlogPostViewSet(BaseModelViewSet):
    view_name = "blog_post"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = BlogPostSerializer
    search_fields = ["title", "slug", "excerpt", "author_name"]
    filterset_fields = ["portal", "is_published"]
    ordering_fields = ["title", "published_at", "is_published", "created_at"]
    ordering = ("-published_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return BlogPostListSerializer
        if self.action == "retrieve":
            return BlogPostDetailSerializer
        return BlogPostSerializer

    def get_queryset(self):
        return BlogPost.objects.select_related("portal")

    def create(self, request, *args, **kwargs):
        """
        Cria o post; `slug` ausente é gerado a partir de `title`

        Returns:
            envelope com os dados do post criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o post; `slug` vazio é regenerado

        Returns:
            envelope com os dados do post atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    def _service(self) -> BlogPostService:
        return BlogPostService(user=self.request.user)
