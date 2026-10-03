# App `public` — endpoints do site público

Tudo que o `portal-web` consome **sem login** mora aqui, separado do `core`
(que é o painel administrativo e o anunciante logado).

Regras:

- Views herdam `BaseViewSet`/`BaseModelViewSet` do `core.classes`, mas usam
  `permission_classes = [AllowAny]` com o comentário `# allow-any: <motivo>`,
  `authentication_classes = []` e `throttle_scope = "public"`.
- Nada de escrita, salvo registro de eventos (clique em anúncio, busca), formulários
  (lead, contato, encomenda) e o cadastro de anunciante.
- Formulários passam por `public/services/sender.py` (IP do cliente + `BlockedSender`).
- Models continuam em `core/models.py`; aqui só há view, serializer, service e docs.
- Rotas em `public/urls.py` (router próprio), montadas em `/api/v1/public/`.
- Estrutura por módulo: `public/modules/<modulo>/{view.py, serializer.py, service/, docs/index.md}`.

Módulos: `portal` (configuração do portal, home, banners, anúncios, catálogo),
`property` (busca, detalhe, favoritos, eventos), `advertiser` (imobiliárias e
hotsite), `content` (blog e dicas), `plan` (planos e tabela de publicidade),
`lead` (fale conosco, encomenda, quero anunciar) e `register` (cadastro de
anunciante com login imediato).

## Cache

Toda leitura nova deste app passa por `core.services.public_cache.cached`,
com o escopo certo (veja a tabela em `ARQUITETURA.md`, seção 14) e em
`params` tudo o que muda a resposta (filtros, página, limite). O portal da
requisição vem de `public.services.scope.cached_portal(slug)`.

- O que for guardado precisa ser serializável com pickle: guarde o
  `serializer.data`, não querysets.
- Efeitos colaterais (estatística, clique) ficam **fora** do `builder`, senão
  só o primeiro acesso seria contado. Grave-os com
  `core.services.deferred_writes.defer`.
- Model novo que aparece no site precisa entrar em `HANDLERS` de
  `core/signals_public_cache.py`.
