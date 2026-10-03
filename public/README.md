# App `public` — endpoints do site público

Tudo que o `portal-web` consome **sem login** mora aqui, separado do `core`
(que é o painel administrativo e o anunciante logado).

Regras:

- Views herdam `BaseViewSet`/`BaseModelViewSet` do `core.classes`, mas usam
  `permission_classes = [AllowAny]` com o comentário `# allow-any: <motivo>`,
  `authentication_classes = []` e `throttle_scope = "public"`.
- Nada de escrita, salvo registro de eventos (clique em anúncio, lead, busca).
- Models continuam em `core/models.py`; aqui só há view, serializer, service e docs.
- Rotas em `public/urls.py` (router próprio), montadas em `/api/v1/public/`.
- Estrutura por módulo: `public/modules/<modulo>/{view.py, serializer.py, service/, docs/index.md}`.

Módulos: `portal` (configuração do portal, home, banners, anúncios, catálogo).
