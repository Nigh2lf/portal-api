from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from core.classes.base_viewset import BaseModelViewSet
from core.classes.exception_handler import envelope_success
from core.classes.permission import CustomPermissionClass
from core.models import PortalMenuItem
from core.modules.portal_menu_item.serializer import (
    PortalMenuItemDetailSerializer,
    PortalMenuItemListSerializer,
    PortalMenuItemSerializer,
)


class PortalMenuItemViewSet(BaseModelViewSet):
    view_name = "portal_menu_item"
    router_user = ["ADMIN"]
    permission_classes = [IsAuthenticated, CustomPermissionClass]
    serializer_class = PortalMenuItemSerializer
    search_fields = ["label", "path"]
    filterset_fields = ["portal", "is_active"]
    ordering_fields = ["sort_order", "label", "updated_at"]
    ordering = ("portal", "sort_order")

    def get_serializer_class(self):
        if self.action == "list":
            return PortalMenuItemListSerializer
        if self.action == "retrieve":
            return PortalMenuItemDetailSerializer
        return PortalMenuItemSerializer

    def get_queryset(self):
        return PortalMenuItem.objects.select_related("portal")

    @action(detail=False, methods=["post"], url_path="reorder")
    @transaction.atomic
    def reorder(self, request):
        """
        Reordena os itens de um portal pela lista de ids recebida

        Returns:
            envelope com os itens do portal na nova ordem
        """
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            raise ValidationError({"ids": ["Informe a lista de ids na ordem desejada."]})
        itens = {str(i.pk): i for i in PortalMenuItem.objects.filter(pk__in=ids)}
        if len(itens) != len(set(ids)):
            raise ValidationError({"ids": ["Há ids inexistentes na lista."]})
        portais = {i.portal_id for i in itens.values()}
        if len(portais) != 1:
            raise ValidationError({"ids": ["Todos os itens devem ser do mesmo portal."]})
        for ordem, pk in enumerate(ids):
            item = itens[str(pk)]
            if item.sort_order != ordem:
                item.sort_order = ordem
                item.updated_by = request.user
                item.save(update_fields=["sort_order", "updated_by", "updated_at"])
        portal_id = next(iter(portais))
        lista = PortalMenuItem.objects.filter(portal_id=portal_id).select_related("portal").order_by("sort_order")
        return envelope_success(data=PortalMenuItemListSerializer(lista, many=True).data)
