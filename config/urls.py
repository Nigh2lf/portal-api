"""URL configuration.

Versionamento da API segue ``URLPathVersioning`` (DRF):

    /api/v1/...   -> config/urls_v1.py
    /api/v2/...   -> config/urls_v2.py  (criar quando precisar)

Para adicionar uma nova versão:

1. Crie ``config/urls_vN.py`` (copie de ``urls_v1.py`` como ponto de partida).
2. Inclua abaixo: ``path("api/vN/", include(...))`` apontando para o novo módulo.
3. Adicione ``vN`` em ``API_ALLOWED_VERSIONS`` (env, csv) — default ``v1``.
4. Em views que precisam diferenciar comportamento, use ``request.version``.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(("config.urls_v1", "v1"), namespace="v1")),
]

# Servir media local apenas em desenvolvimento; produção usa S3.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
