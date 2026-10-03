# Public Assets

Arquivos públicos versionados (logos, banners, ícones) servidos com URL estável.

## Por que existe

- `MediaStorage` (default do `User.profile_image` etc.) é **privado**: gera URL assinada que expira. Ótimo para PII, ruim para uma logo de e-mail.
- `PublicMediaStorage` (usado por `PublicAsset`) serve com URL pública direta e sem querystring. URL imutável, cacheável, sem expiração. O acesso público vem da bucket policy (prefixo `public/`), não de ACL.

## Model

[core/models.py](../core/models.py) → `PublicAsset`:

| Campo | Notas |
|---|---|
| `id` | UUID. |
| `name` | Identificador semântico (ex: `email_logo`, `app_banner_home`). Único? Não — você decide. Os services do boilerplate procuram pelo **primeiro ativo**. |
| `description` | Opcional. |
| `file` | `FileField` — em `save()` o storage é resolvido automaticamente: `PublicMediaStorage` se S3, `FileSystemStorage(location="public")` caso contrário. |
| `is_active` | Para esconder sem apagar. |
| timestamps | `created_at`, `updated_at`. |
| autoria | `created_by`, `updated_by` (do `AbstractModel`); `uploaded_by` mantido por compatibilidade. |

## Cadastrar

### Via Django Admin

`/admin/core/publicasset/add/` — upload do arquivo + nome + ativo.

### Via API

| Método | Path | Auth |
|---|---|---|
| GET | `/api/v1/public-assets/` | público (filtra `is_active=True`) |
| GET | `/api/v1/public-assets/{id}/` | público |
| POST | `/api/v1/public-assets/` | `IsAdminRole` |
| PUT/PATCH | `/api/v1/public-assets/{id}/` | `IsAdminRole` |
| DELETE | `/api/v1/public-assets/{id}/` | `IsAdminRole` |

POST recebe `multipart/form-data` com campo `file`.

## Casos de uso embutidos

| Nome | Quem consome |
|---|---|
| `email_logo` | Header de todos os e-mails (ver [emails.md](emails.md#logo)). |

Para criar um novo "asset bem-conhecido", basta consultá-lo no service:

```python
from core.models import PublicAsset

asset = PublicAsset.objects.filter(name="banner_home", is_active=True).first()
if asset and asset.file:
    url = asset.file.url
```

## S3 vs Filesystem

Quando `AWS_STORAGE_BUCKET_NAME` está setado:

- Path no bucket: `public/<arquivo>`.
- Sem ACL no upload (bucket com ACLs desabilitadas). Acesso público via bucket policy no prefixo `public/`.
- URL: sem assinatura (`?X-Amz-Signature` não aparece).

Quando não está (dev local):

- Path: `<MEDIA_ROOT>/public/<arquivo>`.
- Servir via `MEDIA_URL` (Django dev server cuida disso com `DEBUG=True`).

> Em produção sem S3, configure seu reverse proxy (nginx) para servir `/media/public/`.
