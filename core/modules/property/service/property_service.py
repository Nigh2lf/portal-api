from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from core.models import Property, PropertyFee, PropertyPhoto
from core.services import SluggedCrudService, unique_slug
from core.services.images import ensure_cover_thumbnail

PURPOSE_LABELS = (
    ("sale_price", "à venda"),
    ("rent_price", "para alugar"),
    ("seasonal_rent_price", "para temporada"),
)
TITLE_SOURCE_FIELDS = (
    "title",
    "slug",
    "reference_code",
    "property_type",
    "city",
    "neighborhood",
    "neighborhood_name",
    *(field for field, _label in PURPOSE_LABELS),
)


class PropertyService(SluggedCrudService):
    model = Property

    def create(self, validated_data):
        """
        Cria o imóvel com características e taxas; título e slug são gerados quando ausentes

        Args:
            validated_data: dados já validados pelo PropertySerializer

        Returns:
            Property
        """
        features = validated_data.pop("features", None)
        fees = validated_data.pop("fees", None)

        prop = super().create(validated_data)
        self._sync_nested(prop, features, fees)
        return prop

    def update(self, instance, validated_data):
        """
        Atualiza o imóvel; `features` e `fees` enviados substituem a lista inteira

        Args:
            instance: imóvel a atualizar
            validated_data: dados já validados pelo PropertySerializer

        Returns:
            Property
        """
        features = validated_data.pop("features", None)
        fees = validated_data.pop("fees", None)

        prop = super().update(instance, validated_data)
        self._sync_nested(prop, features, fees)
        return prop

    def ensure_slug(self, data, instance=None):
        """Gera título e slug ("<título> <referência>") quando não informados."""
        merged = {
            field: data.get(field, getattr(instance, field, None)) for field in TITLE_SOURCE_FIELDS
        }
        if not merged["title"]:
            data["title"] = self.build_title(merged)
            merged["title"] = data["title"]

        if merged["slug"]:
            super().ensure_slug(data, instance)
            return

        max_length = Property._meta.get_field("slug").max_length
        data["slug"] = unique_slug(
            Property,
            f"{merged['title']} {merged['reference_code']}",
            max_length=max_length,
            exclude_pk=getattr(instance, "pk", None),
        )

    @staticmethod
    def build_title(merged):
        """Monta "<tipo> <à venda|para alugar|para temporada> em <bairro>, <cidade> - <UF>"."""
        purpose = next((label for field, label in PURPOSE_LABELS if merged.get(field)), "")
        city = merged["city"]
        neighborhood = (
            merged["neighborhood"].name if merged.get("neighborhood") else merged["neighborhood_name"]
        )
        location = f"{neighborhood}, {city.name}" if neighborhood else city.name
        parts = [merged["property_type"].name, purpose, "em", f"{location} - {city.state.code}"]
        max_length = Property._meta.get_field("title").max_length
        return " ".join(part for part in parts if part)[:max_length]

    def _sync_nested(self, prop, features, fees):
        if features is not None:
            prop.features.set(features)
        if fees is not None:
            PropertyFee.objects.filter(property=prop).delete()
            PropertyFee.objects.bulk_create(
                [PropertyFee(property=prop, created_by=self.user, **fee) for fee in fees]
            )
        prop._prefetched_objects_cache = {}

    # ------------------------------------------------------------------
    # Fotos
    # ------------------------------------------------------------------
    def list_photos(self, prop):
        """Fotos do imóvel em ordem de exibição (consulta fresca, sem cache de prefetch)."""
        return list(
            PropertyPhoto.objects.filter(property=prop).order_by("sort_order", "created_at")
        )

    def add_photos(self, prop, files):
        """
        Anexa as imagens ao imóvel no fim da ordenação; a primeira vira capa se ainda não houver

        Args:
            prop: imóvel
            files: arquivos de imagem já validados

        Returns:
            lista completa de PropertyPhoto do imóvel
        """
        existing = self.list_photos(prop)
        next_order = existing[-1].sort_order + 1 if existing else 0
        has_cover = any(photo.is_cover for photo in existing)

        for index, file in enumerate(files):
            photo = PropertyPhoto.objects.create(
                property=prop,
                image=file,
                sort_order=next_order + index,
                is_cover=not has_cover and index == 0,
                created_by=self.user,
            )
            if photo.is_cover:
                ensure_cover_thumbnail(photo)
        return self.list_photos(prop)

    def remove_photo(self, prop, photo_id):
        """
        Apaga a foto (registro e arquivos); se era capa, promove a próxima

        Args:
            prop: imóvel
            photo_id: UUID da foto

        Returns:
            lista completa de PropertyPhoto do imóvel
        """
        photo = self._get_photo(prop, photo_id)
        was_cover = photo.is_cover
        if photo.image:
            photo.image.delete(save=False)
        if photo.thumbnail:
            photo.thumbnail.delete(save=False)
        photo.delete()

        remaining = self.list_photos(prop)
        if was_cover and remaining:
            remaining[0].is_cover = True
            remaining[0].save(update_fields=["is_cover", "updated_at"])
            ensure_cover_thumbnail(remaining[0])
        return remaining

    def set_cover(self, prop, photo_id):
        """
        Define a foto como capa única do imóvel

        Args:
            prop: imóvel
            photo_id: UUID da foto

        Returns:
            lista completa de PropertyPhoto do imóvel
        """
        photo = self._get_photo(prop, photo_id)
        PropertyPhoto.objects.filter(property=prop).exclude(pk=photo.pk).update(is_cover=False)
        photo.is_cover = True
        photo.updated_by = self.user
        photo.save(update_fields=["is_cover", "updated_by", "updated_at"])
        ensure_cover_thumbnail(photo)
        return self.list_photos(prop)

    def reorder_photos(self, prop, ids):
        """
        Reordena as fotos conforme a lista de UUIDs; fotos fora da lista vão para o fim

        Args:
            prop: imóvel
            ids: UUIDs das fotos na nova ordem

        Returns:
            lista completa de PropertyPhoto do imóvel
        """
        photos = {photo.pk: photo for photo in self.list_photos(prop)}
        unknown = [str(pk) for pk in ids if pk not in photos]
        if unknown:
            raise serializers.ValidationError(
                {"ids": [_("Fotos não pertencem ao imóvel: %(ids)s") % {"ids": ", ".join(unknown)}]}
            )

        ordered = list(dict.fromkeys(ids))
        ordered += [pk for pk in photos if pk not in set(ordered)]
        for index, pk in enumerate(ordered):
            photos[pk].sort_order = index
        PropertyPhoto.objects.bulk_update(photos.values(), ["sort_order"])
        return self.list_photos(prop)

    @staticmethod
    def _get_photo(prop, photo_id):
        try:
            return PropertyPhoto.objects.get(property=prop, pk=photo_id)
        except (PropertyPhoto.DoesNotExist, ValueError) as exc:
            raise NotFound(_("Foto não encontrada para este imóvel.")) from exc

    @staticmethod
    def summary():
        """
        Totais do painel: imóveis cadastrados e quantos aparecem no site

        ``visible`` segue a regra do site (``public.services.scope.visible_properties``) sem o
        recorte por portal e cidade: publicado, ativo e de anunciante publicado.

        Returns:
            dict com ``total``, ``visible``, ``hidden_by_advertiser``, ``inactive`` e ``of_xml_advertisers``
        """
        on_air = Q(status=Property.Status.PUBLISHED, is_active=True)
        advertiser_on = Q(advertiser__is_published=True, advertiser__deleted_at__isnull=True)
        return Property.objects.filter(deleted_at__isnull=True).aggregate(
            total=Count("id"),
            visible=Count("id", filter=on_air & advertiser_on),
            hidden_by_advertiser=Count("id", filter=on_air & ~advertiser_on),
            inactive=Count("id", filter=~on_air),
            of_xml_advertisers=Count("id", filter=Q(advertiser__integration__is_active=True)),
        )
