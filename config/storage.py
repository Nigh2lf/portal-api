"""Storage backends.

* ``MediaStorage``       — uploads de mídia privada (perfil etc.).
* ``PublicMediaStorage`` — uploads que precisam ser publicamente acessíveis
  (ex.: imagens de landing page, banners).

Nenhum dos backends envia ACL: o bucket usa "Bucket owner enforced" (ACLs
desabilitadas), então o cabeçalho de ACL é omitido. Acesso público é
controlado por bucket policy, não por ``public-read``.
"""

from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = False

    def path(self, name):
        return name


class PublicMediaStorage(S3Boto3Storage):
    """Bucket location dedicado a assets públicos.

    Use para imagens que serão renderizadas em páginas públicas (landing,
    e-mails). O acesso público vem da bucket policy (prefixo ``public/``), não
    de ACL — o bucket tem ACLs desabilitadas.
    """

    location = "public"
    default_acl = None
    file_overwrite = False
    querystring_auth = False  # URL pública direta, sem signature

    def path(self, name):
        return name
