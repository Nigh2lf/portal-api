from rest_framework.decorators import action

from core.classes.exception_handler import envelope_success


class LookupOptionsMixin:
    lookup_value_field = "name"

    @action(detail=False, methods=["get"], url_path="lookup")
    def options_list(self, request, *args, **kwargs):
        """
        Lista `[{key, value}]` sem paginação para preencher selects

        Returns:
            envelope com `[{key: id, value: <lookup_value_field>}]`
        """
        queryset = self.filter_queryset(self.get_queryset())
        model = queryset.model
        if any(f.name == "is_active" for f in model._meta.fields):
            queryset = queryset.filter(is_active=True)

        rows = queryset.order_by(self.lookup_value_field).values_list(
            "id", self.lookup_value_field
        )
        return envelope_success(data=[{"key": key, "value": value} for key, value in rows])
