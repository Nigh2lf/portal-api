from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import Portal, PortalCity, PortalMenuItem


class PortalService:
    def __init__(self, user=None):
        self.user = user

    def create(self, validated_data):
        """
        Cria o portal com cidades, portais combinados e itens de menu

        Args:
            validated_data: dados já validados pelo PortalSerializer

        Returns:
            Portal
        """
        cities = validated_data.pop("cities", None)
        combined_portals = validated_data.pop("combined_portals", None)
        menu_items = validated_data.pop("menu_items", None)

        portal = Portal.objects.create(**validated_data, created_by=self.user)
        self._sync_nested(portal, cities, combined_portals, menu_items)
        return portal

    def update(self, instance, validated_data):
        """
        Atualiza o portal; `cities`, `combined_portals` e `menu_items` enviados substituem a lista inteira

        Args:
            instance: portal a atualizar
            validated_data: dados já validados pelo PortalSerializer

        Returns:
            Portal
        """
        cities = validated_data.pop("cities", None)
        combined_portals = validated_data.pop("combined_portals", None)
        menu_items = validated_data.pop("menu_items", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.updated_by = self.user
        instance.save()

        self._sync_nested(instance, cities, combined_portals, menu_items)
        return instance

    def _sync_nested(self, portal, cities, combined_portals, menu_items):
        if cities is not None:
            self._sync_cities(portal, cities)
        if combined_portals is not None:
            self._sync_combined_portals(portal, combined_portals)
        if menu_items is not None:
            self._sync_menu_items(portal, menu_items)

    def _sync_cities(self, portal, cities):
        """Reamarra as cidades do portal preservando a ordem recebida em `sort_order`."""
        PortalCity.objects.filter(portal=portal).delete()
        PortalCity.objects.bulk_create(
            [
                PortalCity(portal=portal, city=city, sort_order=index, created_by=self.user)
                for index, city in enumerate(dict.fromkeys(cities))
            ]
        )

    @staticmethod
    def _sync_combined_portals(portal, combined_portals):
        if any(other.pk == portal.pk for other in combined_portals):
            raise serializers.ValidationError(
                {"combined_portals": [_("O portal não pode combinar a si mesmo.")]}
            )
        portal.combined_portals.set(combined_portals)

    def _sync_menu_items(self, portal, menu_items):
        PortalMenuItem.objects.filter(portal=portal).delete()
        PortalMenuItem.objects.bulk_create(
            [
                PortalMenuItem(
                    portal=portal,
                    created_by=self.user,
                    sort_order=item.get("sort_order", index),
                    label=item["label"],
                    path=item["path"],
                    is_active=item.get("is_active", True),
                )
                for index, item in enumerate(menu_items)
            ]
        )
