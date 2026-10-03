from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import Menu, Profile
from core.modules.profile.serializer import (
    MenuSerializer,
    ProfileDetailSerializer,
    ProfileListSerializer,
    ProfileSerializer,
)
from core.modules.profile.service import ProfileService


class ProfileViewSet(BaseModelViewSet):
    view_name = "profile"
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = ProfileSerializer
    search_fields = ["id", "name"]
    ordering = ("id",)

    def get_serializer_class(self):
        if self.action == "list":
            return ProfileListSerializer
        if self.action == "retrieve":
            return ProfileDetailSerializer
        return ProfileSerializer

    def get_queryset(self):
        return Profile.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        """
        Cria o profile com as permissions recebidas no payload

        Returns:
            envelope com os dados do profile criado
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.instance = self._service().create(serializer.validated_data)

    def update(self, request, *args, **kwargs):
        """
        Atualiza o profile; enviar `permissions` substitui a lista inteira

        Returns:
            envelope com os dados do profile atualizado
        """
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.instance = self._service().update(
            serializer.instance, serializer.validated_data
        )

    @action(detail=False, methods=["get"], url_path="menus-permissions")
    def list_permissions(self, request):
        """
        Lista os menus com suas permissions para montar a tela de profile

        Returns:
            envelope com `[{id, name, view, permissions: [...]}]`
        """
        menus = Menu.objects.prefetch_related("permissions_set")
        serializer = MenuSerializer(menus, many=True)
        return envelope_success(data=serializer.data)

    def _service(self) -> ProfileService:
        return ProfileService()
