from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Q
from django.utils import timezone

from core.models import (
    ContactChannel,
    Property,
    PropertyContactClick,
    PropertyInquiry,
    PropertyRequest,
    PropertyView,
)

STATS_TZ = ZoneInfo("America/Sao_Paulo")


def _next_month(dt):
    return (dt.replace(day=28) + timedelta(days=4)).replace(day=1)


def _previous_month(dt):
    return (dt - timedelta(days=1)).replace(day=1)


class AdvertiserStatsService:
    def __init__(self, advertiser):
        self.advertiser = advertiser

    def monthly(self, months):
        """
        Totais por mês (America/Sao_Paulo), do mais recente para o mais antigo

        Args:
            months: quantidade de meses, incluindo o atual

        Returns:
            lista de {year_month, properties, views, phone_clicks, whatsapp_clicks, inquiries, property_requests}
        """
        ranges = self._month_ranges(months)
        views = self._count_by_range(self._views(), ranges)
        phone = self._count_by_range(self._clicks(ContactChannel.PHONE), ranges)
        whatsapp = self._count_by_range(self._clicks(ContactChannel.WHATSAPP), ranges)
        inquiries = self._count_by_range(self._inquiries(), ranges)
        requests = self._count_by_range(self._requests(), ranges)
        properties = self._active_properties_until(ranges)

        return [
            {
                "year_month": start.strftime("%Y-%m"),
                "properties": properties[index],
                "views": views[index],
                "phone_clicks": phone[index],
                "whatsapp_clicks": whatsapp[index],
                "inquiries": inquiries[index],
                "property_requests": requests[index],
            }
            for index, (start, _end) in enumerate(ranges)
        ]

    def period(self, start_date, end_date):
        """
        Totais do período (datas inclusivas, America/Sao_Paulo) e ranking por imóvel

        Args:
            start_date: primeiro dia
            end_date: último dia

        Returns:
            {start, end, properties, views, phone_clicks, whatsapp_clicks, inquiries,
             property_requests, total_leads, by_property}
        """
        in_range = self._range_q(
            datetime.combine(start_date, time.min, tzinfo=STATS_TZ),
            datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=STATS_TZ),
        )
        views_qs = self._views().filter(in_range)
        clicks_qs = self._clicks().filter(in_range)
        inquiries_qs = self._inquiries().filter(in_range)

        clicks = clicks_qs.aggregate(
            phone=Count("id", filter=Q(channel=ContactChannel.PHONE)),
            whatsapp=Count("id", filter=Q(channel=ContactChannel.WHATSAPP)),
        )
        inquiries = inquiries_qs.count()
        requests = self._requests().filter(in_range).count()

        return {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "properties": self._active_properties().count(),
            "views": views_qs.count(),
            "phone_clicks": clicks["phone"],
            "whatsapp_clicks": clicks["whatsapp"],
            "inquiries": inquiries,
            "property_requests": requests,
            "total_leads": inquiries + clicks["phone"] + clicks["whatsapp"] + requests,
            "by_property": self._by_property(views_qs, clicks_qs, inquiries_qs),
        }

    def _by_property(self, views_qs, clicks_qs, inquiries_qs):
        """Agrupa os eventos por imóvel (id ou, para imóveis apagados, o código) e ordena por visualizações."""
        rows = {}

        def add(event, field):
            # Eventos sem imóvel (ex.: clique no contato do hotsite) entram só nos totais.
            key = event["property_id"] or event["property_reference_code"]
            if not key:
                return
            row = rows.setdefault(
                key,
                {
                    "property": event["property_id"],
                    "reference_code": event["property_reference_code"],
                    "title": "",
                    "slug": None,
                    "views": 0,
                    "phone_clicks": 0,
                    "whatsapp_clicks": 0,
                    "inquiries": 0,
                },
            )
            row[field] += event["total"]

        group = ("property_id", "property_reference_code")
        for event in views_qs.values(*group).annotate(total=Count("id")):
            add(event, "views")
        for event in clicks_qs.values(*group, "channel").annotate(total=Count("id")):
            add(event, "phone_clicks" if event["channel"] == ContactChannel.PHONE else "whatsapp_clicks")
        for event in inquiries_qs.values(*group).annotate(total=Count("id")):
            add(event, "inquiries")

        property_ids = [key for key, row in rows.items() if row["property"]]
        if property_ids:
            details = Property.objects.filter(pk__in=property_ids).values(
                "id", "reference_code", "title", "slug"
            )
            for detail in details:
                row = rows[detail["id"]]
                row.update(
                    reference_code=detail["reference_code"],
                    title=detail["title"],
                    slug=detail["slug"],
                )

        return sorted(rows.values(), key=lambda row: (row["views"], row["inquiries"]), reverse=True)

    def _views(self):
        return PropertyView.objects.filter(advertiser=self.advertiser)

    def _clicks(self, channel=None):
        queryset = PropertyContactClick.objects.filter(advertiser=self.advertiser)
        return queryset.filter(channel=channel) if channel else queryset

    def _inquiries(self):
        return PropertyInquiry.objects.filter(advertiser=self.advertiser)

    def _requests(self):
        if not self.advertiser.receives_property_requests:
            return PropertyRequest.objects.none()
        return PropertyRequest.objects.filter(
            is_partner_broadcast=True, portal_id=self.advertiser.portal_id
        )

    def _active_properties(self):
        return Property.objects.filter(
            advertiser=self.advertiser, deleted_at__isnull=True, is_active=True
        )

    def _active_properties_until(self, ranges):
        """Imóveis ativos hoje que já existiam ao fim de cada mês."""
        result = self._active_properties().aggregate(
            **{
                f"r{index}": Count("id", filter=Q(created_at__lt=end))
                for index, (_start, end) in enumerate(ranges)
            }
        )
        return [result[f"r{index}"] for index in range(len(ranges))]

    @staticmethod
    def _month_ranges(months):
        start = timezone.now().astimezone(STATS_TZ).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        ranges = []
        for _ in range(months):
            ranges.append((start, _next_month(start)))
            start = _previous_month(start)
        return ranges

    @staticmethod
    def _range_q(start, end, field="created_at"):
        return Q(**{f"{field}__gte": start, f"{field}__lt": end})

    @classmethod
    def _count_by_range(cls, queryset, ranges):
        result = queryset.aggregate(
            **{
                f"r{index}": Count("id", filter=cls._range_q(start, end))
                for index, (start, end) in enumerate(ranges)
            }
        )
        return [result[f"r{index}"] for index in range(len(ranges))]
