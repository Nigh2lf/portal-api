"""Mixin para usar UUID como PK em models.

Uso:
    class MyModel(UUIDPrimaryKeyMixin, AbstractModel):
        ...

Evita expor IDs sequenciais em APIs públicas (mitiga enumeração).
"""

import uuid

from django.db import models


class UUIDPrimaryKeyMixin(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True
