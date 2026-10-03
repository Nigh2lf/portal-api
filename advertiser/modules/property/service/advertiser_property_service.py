from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import Property, PropertyPhoto
from core.modules.property.service import PropertyService


class AdvertiserPropertyService(PropertyService):
    def __init__(self, advertiser, user=None):
        super().__init__(user=user)
        self.advertiser = advertiser

    def create(self, validated_data):
        """
        Cria o imóvel do anunciante da sessão, já publicado, respeitando os limites do plano

        Args:
            validated_data: dados já validados pelo AdvertiserPropertySerializer

        Returns:
            Property
        """
        validated_data["advertiser"] = self.advertiser
        validated_data["status"] = Property.Status.PUBLISHED
        self._validate_rules(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Atualiza o imóvel respeitando código único e limites do plano

        Args:
            instance: imóvel do anunciante
            validated_data: dados já validados pelo AdvertiserPropertySerializer

        Returns:
            Property
        """
        validated_data.pop("advertiser", None)
        self._validate_rules(validated_data, instance)
        return super().update(instance, validated_data)

    def add_photos(self, prop, files):
        """
        Anexa fotos ao imóvel se o total não ultrapassar o limite de fotos do plano

        Args:
            prop: imóvel
            files: arquivos de imagem já validados

        Returns:
            lista completa de PropertyPhoto do imóvel
        """
        limit = self.advertiser.effective_photo_limit
        current = PropertyPhoto.objects.filter(property=prop).count()
        if current + len(files) > limit:
            raise serializers.ValidationError(
                {"images": [_("Seu plano permite %(limit)d fotos por imóvel.") % {"limit": limit}]}
            )
        return super().add_photos(prop, files)

    def remove_all_photos(self, prop):
        """
        Apaga todas as fotos do imóvel (registros e arquivos hospedados)

        Args:
            prop: imóvel

        Returns:
            lista vazia
        """
        for photo in self.list_photos(prop):
            if photo.image:
                photo.image.delete(save=False)
            if photo.thumbnail:
                photo.thumbnail.delete(save=False)
        PropertyPhoto.objects.filter(property=prop).delete()
        return []

    def _validate_rules(self, data, instance=None):
        """Código único por anunciante e limites de imóveis ativos/destaques do plano."""
        errors = {}
        others = Property.objects.filter(advertiser=self.advertiser, deleted_at__isnull=True)
        if instance is not None:
            others = others.exclude(pk=instance.pk)

        reference_code = data.get("reference_code")
        if reference_code and others.filter(reference_code__iexact=reference_code).exists():
            errors["reference_code"] = [_("Já existe um imóvel com este código.")]

        def merged(field, default):
            value = data.get(field, getattr(instance, field, None))
            return default if value is None else value

        becomes_active = merged("is_active", True) and not (instance and instance.is_active)
        if becomes_active:
            limit = self.advertiser.effective_property_limit
            if others.filter(is_active=True).count() >= limit:
                errors["is_active"] = [
                    _("Seu plano permite %(limit)d imóveis ativos.") % {"limit": limit}
                ]

        becomes_featured = merged("is_featured", False) and not (
            instance and instance.is_featured
        )
        if becomes_featured:
            limit = self.advertiser.effective_featured_limit
            if others.filter(is_active=True, is_featured=True).count() >= limit:
                errors["is_featured"] = [
                    _("Seu plano permite %(limit)d imóveis em destaque.") % {"limit": limit}
                ]

        if errors:
            raise serializers.ValidationError(errors)
