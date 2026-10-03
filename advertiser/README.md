# App `advertiser` — painel do anunciante (área logada do site)

Tudo que o `portal-web` consome **com o anunciante logado** mora aqui, separado
do `core` (painel administrativo) e do `public` (site sem login).

Regras:

- Views herdam `BaseViewSet`/`BaseModelViewSet` do `core.classes` com
  `permission_classes = [IsAuthenticated, CustomPermissionClass]`,
  `router_user = ["USER", "ADMIN"]`, `view_name` único (`advertiser_*`) e
  `view_read = True` (quem vê a tela, opera nela).
- O anunciante é sempre o do usuário da sessão (`user.advertiser_profile`, via
  `advertiser.services.current_advertiser`). Nenhum id vindo do cliente define
  a quem um registro pertence: todo queryset é filtrado por esse anunciante.
- Os `Menu`/`Permission` dos `view_name` não saem do `seedpermissions` (as
  views não estão no router do `core`): rode `manage.py seed_advertiser_profile`,
  que também os vincula ao perfil `ANUNCIANTE`.
- Models continuam em `core/models.py`; aqui só há view, serializer, service e docs.
- Rotas em `advertiser/urls.py` (router próprio), montadas em `/api/v1/advertiser/`.
- Estrutura por módulo: `advertiser/modules/<modulo>/{view.py, serializer.py, service/, docs/index.md}`.

Módulos: `me` (dados, senha, uso do plano), `property` (imóveis e fotos),
`inquiry` (ofertas recebidas + CSV), `property_request` (encomendas de
parceiros), `stats` (estatísticas mensais e por período), `import_report`
(relatório da importação XML).
