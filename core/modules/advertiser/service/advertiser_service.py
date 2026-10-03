from core.models import Advertiser, AdvertiserCity, AdvertiserIntegration
from core.services import SluggedCrudService

UNSET = object()


class AdvertiserService(SluggedCrudService):
    model = Advertiser

    def create(self, validated_data):
        """
        Cria o anunciante com a integração e as cidades de atuação

        Args:
            validated_data: dados já validados pelo AdvertiserSerializer

        Returns:
            Advertiser
        """
        integration = validated_data.pop("integration", UNSET)
        cities = validated_data.pop("advertiser_cities", None)

        advertiser = super().create(validated_data)
        self._sync_integration(advertiser, integration)
        if cities is not None:
            self._sync_cities(advertiser, cities)
        return advertiser

    def update(self, instance, validated_data):
        """
        Atualiza o anunciante; `integration` faz upsert e `cities` substitui a lista inteira

        Args:
            instance: anunciante a atualizar
            validated_data: dados já validados pelo AdvertiserSerializer

        Returns:
            Advertiser
        """
        integration = validated_data.pop("integration", UNSET)
        cities = validated_data.pop("advertiser_cities", None)

        advertiser = super().update(instance, validated_data)
        self._sync_integration(advertiser, integration)
        if cities is not None:
            self._sync_cities(advertiser, cities)
        return advertiser

    def _sync_integration(self, advertiser, data):
        """Cria/atualiza a integração; `None` remove; ausente mantém."""
        if data is UNSET:
            return

        if data is None:
            AdvertiserIntegration.objects.filter(advertiser=advertiser).delete()
        else:
            integration, created = AdvertiserIntegration.objects.get_or_create(
                advertiser=advertiser, defaults={**data, "created_by": self.user}
            )
            if not created:
                for field, value in data.items():
                    setattr(integration, field, value)
                integration.updated_by = self.user
                integration.save()

        advertiser._state.fields_cache.pop("integration", None)

    def _sync_cities(self, advertiser, cities):
        AdvertiserCity.objects.filter(advertiser=advertiser).delete()
        AdvertiserCity.objects.bulk_create(
            [
                AdvertiserCity(advertiser=advertiser, city=city, created_by=self.user)
                for city in dict.fromkeys(cities)
            ]
        )
        advertiser._prefetched_objects_cache = {}
