from django.db.models import Q
from django.utils import timezone

from core.models import BlogPost, Portal, Tip


class ContentService:
    def __init__(self, portal: Portal):
        self.portal = portal

    def _portal_scope(self):
        """Conteúdo global (portal nulo) ou do próprio portal."""
        return Q(portal__isnull=True) | Q(portal=self.portal)

    def posts(self):
        """Posts publicados, já com data de publicação alcançada, do mais recente ao mais antigo."""
        return (
            BlogPost.objects.filter(self._portal_scope(), is_published=True, published_at__lte=timezone.now())
            .order_by("-published_at", "-created_at")
        )

    def post_by_slug(self, slug):
        return self.posts().filter(slug=slug).first()

    def tips(self):
        return Tip.objects.filter(self._portal_scope(), is_active=True).order_by("sort_order", "-published_at")
