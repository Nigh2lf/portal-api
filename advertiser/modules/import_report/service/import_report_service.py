from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound

from advertiser.modules.import_report.serializer import (
    ImportErrorSerializer,
    ImportInvalidPropertySerializer,
)
from core.models import AdvertiserIntegration, RejectedProperty, XmlImportError, XmlImportRun

MAX_ERRORS = 200


def build_import_report(advertiser):
    """
    Relatório da última importação XML do anunciante

    Args:
        advertiser: anunciante da sessão

    Returns:
        {xml_url, last_imported_at, total, valid, invalid, errors}; 404 sem integração XML
    """
    integration = (
        AdvertiserIntegration.objects.filter(advertiser=advertiser).exclude(xml_url="").first()
    )
    if integration is None:
        raise NotFound(_("Anunciante sem integração XML."))

    run = XmlImportRun.objects.filter(advertiser=advertiser).order_by("-started_at").first()
    errors = (
        run.errors.order_by("-created_at")[:MAX_ERRORS] if run else XmlImportError.objects.none()
    )
    rejected = RejectedProperty.objects.filter(advertiser=advertiser).order_by(
        "property_reference_code"
    )

    return {
        "xml_url": integration.xml_url,
        "last_imported_at": integration.last_imported_at or (run.finished_at if run else None),
        "total": run.total_properties if run else 0,
        "valid": run.valid_properties if run else 0,
        "invalid": ImportInvalidPropertySerializer(rejected, many=True).data,
        "errors": ImportErrorSerializer(errors, many=True).data,
    }
