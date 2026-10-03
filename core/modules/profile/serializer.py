from rest_framework import serializers

from core.models import Menu, Permission, Profile


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "menu", "name", "type")


class MenuSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(source="permissions_set", many=True, read_only=True)

    class Meta:
        model = Menu
        fields = ("id", "name", "view", "permissions")


class ProfileSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )

    class Meta:
        model = Profile
        fields = ("id", "name", "is_active", "permissions", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id", "name", "is_active", "created_at")


class ProfileDetailSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = ("id", "name", "is_active", "permissions", "created_at", "updated_at")


class ProfileLookupSerializer(serializers.ModelSerializer):
    key = serializers.UUIDField(source="id", read_only=True)
    value = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = Profile
        fields = ("key", "value")
