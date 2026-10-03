"""Identificação e bloqueio de remetentes dos formulários públicos (antispam)."""

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from core.models import BlockedSender


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def is_sender_blocked(email, ip):
    """Verifica se o e-mail ou o IP constam em `BlockedSender` ativo."""
    cond = Q()
    if email:
        cond |= Q(email__iexact=email)
    if ip:
        cond |= Q(ip_address=ip)
    if not cond:
        return False
    return BlockedSender.objects.filter(is_active=True).filter(cond).exists()


def ensure_sender_allowed(email, ip):
    """Levanta 403 quando o remetente (e-mail ou IP) está bloqueado."""
    if is_sender_blocked(email, ip):
        raise PermissionDenied("Remetente bloqueado.")
