# Changelog

Todas as mudanças relevantes deste boilerplate são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
o versionamento segue [SemVer](https://semver.org/lang/pt-BR/) — `MAJOR.MINOR.PATCH`.

> A versão atual é exposta em código por `core.__version__` (ver
> [core/__init__.py](core/__init__.py)) e em [pyproject.toml](pyproject.toml).
> Mantenha as duas em sincronia ao bumpar a versão.

Para projetos derivados: registre no `README` ou em um `BOILERPLATE_VERSION`
de qual versão deste boilerplate vocês saíram.

## [Unreleased]

### Adicionado
- `GET /api/v1/{users,advertisers,properties}/summary/`: contadores de total e ativos para o
  painel inicial do admin (uma consulta agregada cada, permissão `READ` da própria tela).

### Mudou
- Desempenho das rotas que passavam de 800 ms no `LogRequest` de produção:
  `GET /api/v1/advertisers/` conta os imóveis por subconsulta em vez de `LEFT JOIN` +
  `GROUP BY` (380 ms → 1 ms no banco; a contagem da paginação deixa de fazer o join);
  os relacionados (`.../properties/{slug}/related/`) escolhem os 6 ids mais próximos em
  preço no banco e só eles carregam fotos e características (antes 200 imóveis e ~4.500
  fotos), agora entre todos os imóveis do mesmo tipo e cidade, não só os 200 mais recentes;
  `portal_ids`/`city_ids` usam as relações já pré-carregadas do portal em cache (duas
  consultas a menos por leitura pública fora do cache).
- Cards de imóvel (busca, relacionados, favoritos, destaques da home e listagem do admin)
  carregam só a foto de capa; a galeria inteira fica para o detalhe
  (`with_card_data(..., all_photos=True)`). Na busca de 30 imóveis eram 535 fotos lidas, agora 30.
  A home passa a usar `visible_properties`/`with_card_data` em vez de cópias das mesmas regras.
- `PropertyPhoto` (**exige migration**): sem índice em `legacy_id`, sem índice nem constraint em
  `created_by`/`updated_by` (as colunas ficam) e com índice novo
  `(property, is_cover, sort_order)`. Tira ~65 MB de índices que só existiam para serem
  mantidos na importação. `PropertyFee`, `PropertyView`, `PropertyContactClick` e `SearchLog`
  também perdem índice e constraint de autoria (`UnindexedAuditMixin`).
- Busca pública: contadores das abas, preço máximo e total saem de uma consulta agregada em
  vez de três. Totais por anunciante (diretório, hotsite e detalhe do imóvel) e
  `views_count` do painel deixam de usar `Count` com join + `distinct`.
- `public_cache.cached`: pedidos simultâneos da mesma chave no mesmo processo montam o valor
  uma vez só; os demais esperam e reaproveitam.

### Removido
- Agendador interno (APScheduler): pacote `core/cron/`, `RUN_CRON`,
  `LOG_REQUESTS_PURGE_SCHEDULE`, `MODEL_AUDIT_PURGE_SCHEDULE`, `docs/cron.md` e a dependência
  `APScheduler`. A importação noturna (`import_xml --window --origin cron`) e a limpeza de logs
  (novo comando `purge_logs`, que inclui `SearchLog` com `SEARCH_LOG_RETENTION_DAYS`) passam a
  depender de execução manual ou agendador externo.
- `import_legacy`: imóvel que a importação XML já criou (mesmo código, sem `legacy_id`)
  é mantido e só recebe o `legacy_id`, em vez de estourar a chave única
  `(advertiser, reference_code)`; código repetido no legado fica o primeiro. No fim o
  cache público é limpo inteiro e o site avisado (`invalidation_batch(everything=True,
  wait_site=True)`), já que gravações em lote não disparam os sinais de invalidação.
- Importação XML (`xml_import`) sem segurar memória no worker do gunicorn: painel e
  cron rodam `manage.py import_xml` num processo separado (`XML_IMPORT_SUBPROCESS`;
  novas opções `--batch` e `--origin`); o feed é baixado em blocos e lido em streaming
  (`iterparse`, um imóvel por vez) em vez de montar a árvore inteira; miniaturas de capa
  decodificam o JPEG já reduzido (`draft`) com 3 threads em vez de 6; log de memória por
  anunciante no lote. Start command do Railway com `MALLOC_ARENA_MAX=2` e
  `--max-requests 500`.

### Adicionado
- MFA opcional no Django Admin via `django-otp` (`ADMIN_MFA_ENABLED`). Apps
  `django_otp`, `otp_totp` e `otp_static` ficam sempre instalados; o
  `OTPAdminSite` é ativado apenas quando o flag está `True`. Detalhes em
  [docs/auth-permissions.md](docs/auth-permissions.md#mfa-no-django-admin).
- Paginação padrão `core.classes.pagination.StandardPagination` com `page_size`
  via query param e envelope amigável (`count`, `total_pages`, `page`,
  `page_size`, `next`, `previous`, `results`).
- Filtros padrão habilitados: `DjangoFilterBackend`, `SearchFilter`,
  `OrderingFilter`. Basta declarar `filterset_fields` / `search_fields` /
  `ordering_fields` no ViewSet.
- Versionamento explícito da API via `URLPathVersioning`. Default `v1`,
  versões permitidas configuráveis por env `API_ALLOWED_VERSIONS`.
- Comando `seed_demo` cria três usuários de demonstração (idempotente):
  - `admin@admin.com` / senha `admin` em **texto puro** — superuser do
    Django Admin (`is_staff=True`). Login direto em `/admin/`.
  - `admin@<projeto>.com` / senha `admin` (front envia MD5↑) — admin da
    API, role ADMIN. `<projeto>` derivado de `PROJECT_NAME`.
  - `a@a.com` / senha `a` (front envia MD5↑) — usuário comum da API.
  Usuários da API seguem a convenção Noclaf: o front envia a senha em
  MD5 uppercase e o Django aplica PBKDF2 por cima.

## [0.1.0] - 2026-05-05

### Adicionado
- Auditoria automática `created_by` / `updated_by` via `AbstractModel` +
  `BaseModelViewSet`.
- Log de requests HTTP (`LogRequest` + `RequestLoggerMiddleware`) com redação
  de PII e snapshot de usuário.
- Auditoria de mudanças em models (`LogModelChange` + `signals_audit` +
  `CurrentUserMiddleware`).
- Cron com schedules configuráveis (`LOG_REQUESTS_PURGE_SCHEDULE`,
  `MODEL_AUDIT_PURGE_SCHEDULE`).
- Bases abstratas e tabelas de infra concentradas em `core/models_base.py`.

### Mudou
- `models.py` reorganizado em 3 seções (Identidade, RBAC, Conteúdo público).
  Bases e tabelas de log saíram daqui.

### Removido
- Código morto: `SIB_API_KEY`, `permission_type_user.py`,
  `ChangePasswordSerializer`.

[Unreleased]: ../../compare/v0.1.0...HEAD
[0.1.0]: ../../releases/tag/v0.1.0
