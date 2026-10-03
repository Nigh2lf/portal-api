"""ViewSet de `PublicAsset` (imagens públicas).

Leitura pública (landing page); escrita restrita a admin.
"""

from rest_framework import permissions
from rest_framework.parsers import FormParser, MultiPartParser

from core.classes.base_viewset import BaseModelViewSet
from core.classes.permission import CustomPermissionClass
from core.models import PublicAsset
from core.serializers import PublicAssetSerializer


class PublicAssetViewSet(BaseModelViewSet):
    view_name = "public_asset"
    queryset = PublicAsset.objects.all()
    serializer_class = PublicAssetSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated, CustomPermissionClass]

    def get_permissions(self):
        # allow-any: PublicAsset serve logos/banners exibidos em landing pages anônimas.
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        qs = PublicAsset.objects.all()
        if self.action in ("list", "retrieve") and not (
            self.request.user.is_authenticated and getattr(self.request.user, "is_staff", False)
        ):
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user, **self._audit_kwargs("created_by"))
