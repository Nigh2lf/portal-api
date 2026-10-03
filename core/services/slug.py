from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

SLUG_FALLBACK = "item"


def unique_slug(model, value, *, max_length, scope=None, exclude_pk=None):
    """
    Gera um slug único para o model a partir de `value`, acrescentando sufixo numérico se preciso

    Args:
        model: model alvo
        value: texto base (nome, título...)
        max_length: tamanho máximo do campo slug
        scope: filtros extras de unicidade (ex.: `{"state": state}`)
        exclude_pk: pk a ignorar na checagem (update)

    Returns:
        str
    """
    base = slugify(value)[:max_length] or SLUG_FALLBACK
    queryset = model.objects.filter(**(scope or {}))
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    slug = base
    counter = 2
    while queryset.filter(slug=slug).exists():
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug


class SluggedCrudService:
    model = None
    slug_source = "name"
    slug_scope_fields: tuple[str, ...] = ()

    def __init__(self, user=None):
        self.user = user

    def create(self, validated_data):
        """
        Cria o registro gerando o slug quando não informado

        Args:
            validated_data: dados já validados pelo serializer

        Returns:
            instância criada
        """
        self.ensure_slug(validated_data)
        return self.model.objects.create(**validated_data, created_by=self.user)

    def update(self, instance, validated_data):
        """
        Atualiza o registro; slug vazio é regenerado a partir do nome

        Args:
            instance: registro a atualizar
            validated_data: dados já validados pelo serializer

        Returns:
            instância atualizada
        """
        self.ensure_slug(validated_data, instance)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.updated_by = self.user
        instance.save()
        return instance

    def ensure_slug(self, data, instance=None):
        """Preenche `data["slug"]` quando ausente e garante unicidade no escopo."""
        max_length = self.model._meta.get_field("slug").max_length
        scope = {
            field: data.get(field, getattr(instance, field, None))
            for field in self.slug_scope_fields
        }
        exclude_pk = getattr(instance, "pk", None)
        slug = data.get("slug")

        if slug:
            queryset = self.model.objects.filter(slug=slug, **scope)
            if exclude_pk is not None:
                queryset = queryset.exclude(pk=exclude_pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"slug": [_("Já existe um registro com este slug.")]}
                )
            return

        if instance is not None and "slug" not in data and instance.slug:
            return

        source = data.get(self.slug_source, getattr(instance, self.slug_source, ""))
        data["slug"] = unique_slug(
            self.model, source, max_length=max_length, scope=scope, exclude_pk=exclude_pk
        )
