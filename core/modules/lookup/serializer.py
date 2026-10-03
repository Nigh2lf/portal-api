"""Serializers enxutos dos endpoints de lookup.

Regra: lookup devolve o mínimo para preencher um select — id + rótulo. Nada de
``fields = "__all__"`` (W007) e nada de campo sensível (W008).
"""

from rest_framework import serializers

from core.models import User


class UserLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "email")
