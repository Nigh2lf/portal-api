# Modelo de dados — portais de imóveis

Models em `core/models.py` (seções 4 a 13). Todos herdam
`AbstractModel` (UUID PK, `created_at`, `updated_at`, `created_by`, `updated_by`).
Entidades migradas do legado carregam `legacy_id` (`LegacyIdMixin`) para a carga
de dados e para os redirects 301.

Fonte do legado: `new/db-portal-202610031131.sql` (MySQL `portal`, 44 tabelas, 14 views).

## Diagrama (resumo)

```
Portal ──< PortalCity >── City ──< Neighborhood
  │  └──< PortalMenuItem, PortalHomeCache, Banner, Ad, Tip, BlogPost
  │
  └──< Advertiser ──1 User (core.User, login JWT)
         ├── Plan
         ├──1 AdvertiserIntegration ── Integrator
         ├──< AdvertiserCity
         ├──< Property ──< PropertyPhoto, PropertyFee
         │       ├── PropertyType, City, Neighborhood
         │       └──M2M Feature (scope PROPERTY | CONDOMINIUM)
         ├──< PropertyInquiry, PropertyView, PropertyContactClick, PropertyViewMonthly
         └──< XmlImportRun ──< XmlImportError; XmlFetchLog; RejectedProperty; IntegrationLog

Portal ──< ContactMessage, PropertyRequest, AdvertiserLead, SearchLog
AdPlacement ──< Ad ──< AdImpression, AdClick, AdImpressionMonthly
BlockedSender, State, ScheduledTaskRun
```

## Legado → novo

| Tabela legada | Model | Observações |
|---|---|---|
| `Portal` + `Global.php` | `Portal`, `PortalCity`, `PortalMenuItem` | `Cidades` (CSV) vira `PortalCity`; `Id_PortalCombinado` vira M2M `combined_portals`; SMTP/senha saem do banco (env). Tudo que era hard-coded no `Global.php` (SEO, redes, GA4, logo, slug de imobiliárias) entra aqui. |
| `PreProcessamento` | `PortalHomeCache` | `Fonte` vira `kind` (choices); `Json` vira `payload` JSONField. |
| `banner` | `Banner` | Agora pode ser por portal. |
| `UF` | `State` | |
| `cidade` | `City` | `Regras` vira `import_aliases` (JSON). Ganha `slug`. |
| `bairro` | `Neighborhood` | Idem. `bairro_Antigo` descartada. |
| `Produto` | `Plan` | `Preco` int vira `monthly_price` decimal (nulo = sob consulta). Flags viram booleanos. |
| `Integrador` | `Integrator` | |
| `cliente` | `Advertiser` | `TipoCliente` 1/2/3 vira `type` OWNER/BROKER/AGENCY. `Portal` (flag) vira `is_published`. `TermoDeUso` vira `accepted_terms_at`. `Senha` md5 vira `legacy_password_md5` (temporário); login real em `core.User`. `Imobiliaria_Petropolis/Teresopolis` descartados (não usados no PHP). `NoImoveis/NoFotos/Destaques` viram overrides nulos por padrão. |
| `cliente` (URL_XML, TokenGaia, Vista_*, SalvarTodasImagens, NaoSalvarMiniaturas, ArquivoLocal) | `AdvertiserIntegration` | Separado por ser 1:1 e opcional. |
| `clientecidadeportal` | `AdvertiserCity` | |
| `imoveltipo` | `PropertyType` | `Regras` vira `import_aliases`; ganha `is_residential`. |
| `imovelinfra`, `imovelinfracondominio` | `Feature` | Uma tabela com `scope`. No imóvel vira M2M em vez de string `a;b;c`. |
| `imovel` + view `imovelportal` | `Property` | Preços de `varchar` para decimal. `Suite/Banheiro/Garagem` de varchar para inteiro. `ImovelTipo/Cidade/Bairro/UF` (texto denormalizado) descartados: ficam só as FKs + `neighborhood_name` para "outro bairro". `Imagem/Imagem_Mini/ImagemExcluir` (JSON) viram `PropertyPhoto`. `FeiraoImoveis/PrecoFeirao/FlagTeste/ImagemLocal/Regiao` descartados. Ganha `slug`, `title`, `status`, `published_at`. |
| `imovelfoto` + JSON `imovel.Imagem` | `PropertyPhoto` | `NoImagem` vira `sort_order`; `Mini` vira `is_cover`. |
| `imoveltaxa` | `PropertyFee` | `Valor` decimal; `Obs` vira `period` (choices) + `notes`. |
| `mensagem` | `PropertyInquiry` | FK real para `Property` (nulo se o imóvel sumir) + `property_reference_code`. Ganha `contact_preferences`. |
| `Contato` | `ContactMessage` + `PropertyRequest` | A tabela misturava contato e encomenda; separadas. |
| `EncomendaImovel` | `PropertyRequest` | `Preferencialmente` vira `funding`; `Assunto` deixa de ser texto e vira campos tipados. |
| `LeadSite` | `AdvertiserLead` | Ganha `portal` e `company`. |
| `BloqueioRemetente`, `BloqueioAcesso` | `BlockedSender` | Unificadas. |
| `PublicidadeCategoria` + tabela de preços (`Publicidade.php`) | `AdPlacement` | Código (PH1, BH1...), página, tipo, tamanho e preço. |
| `Publicidade` | `Ad` | |
| `PublicidadeAcesso`, `PublicidadeClick`, `PublicidadeAcessoAgrupada` | `AdImpression`, `AdClick`, `AdImpressionMonthly` | |
| `EstatisticaImovelAcesso` | `PropertyView` | |
| `EstatisticaImovelClick` | `PropertyContactClick` | `WhatsApp` (flag) vira `channel` PHONE/WHATSAPP. |
| `EstatisticaImovelAcessoAgrupada` | `PropertyViewMonthly` | Ganha cliques e mensagens no mesmo agregado. |
| `PesquisasSalvas` + view `PesquisasSalvasFormatado` | `SearchLog` | FKs em vez de ids soltos; `Quarto` vira JSON. |
| `ControleImportacao` | `XmlImportRun` | |
| `ErroImportacao` | `XmlImportError` | `Query` vira `payload`; ganha `message` e FK para a execução. |
| `ControleXMLLocal`, `ImportacaoXML` | `XmlFetchLog` | |
| view `imovelrejeitado` | `RejectedProperty` | Era view; vira tabela de moderação. |
| `ControleTarefasAutomaticas` | `ScheduledTaskRun` | Ganha `status` e `details`. |
| `API_Retorno` | `IntegrationLog` | Ganha `service`. |
| `dica` | `Tip` | |
| WordPress `wp_posts` | `BlogPost` | Migra do banco `blogportal`. |

## Descartados

| Legado | Motivo |
|---|---|
| `Empreendimento`, `MensagemEmpreendimento`, `EstatisticaEmpreedimentoAcesso`, `EstatisticaEmpreendimentoClick` | Funcionalidade morta: 2 registros, rota sem arquivo PHP. Se voltar, entra como `Development`. |
| `EstatisticaFeiraoAcesso`, `imovel.FeiraoImoveis`, `PrecoFeirao`, `*.Feirao` | Evento de 2019, sem página. |
| `bairro_Antigo` | Backup manual. |
| `cliente.Imobiliaria_Petropolis`, `cliente.Imobiliaria_Teresopolis`, `cliente.TrustImovel` | Não lidos em lugar nenhum do PHP. |
| Views `AcessoMes`, `CliqueMes`, `MensagemDia`, `MensagemMes`, `BuscaPorCampo`, `RelevanciaImovel`, `imoveisrepetidos`, `imovelfotomini`, `imoveltotal`, `imovelvalorcorreto`, `AtualizacaoImoveisCliente` | Relatórios ad hoc; viram queries no ORM/anotações quando forem necessários. |

## Decisões que valem a pena confirmar

1. **Objetivo derivado dos preços** (`sale_price`, `rent_price`, `seasonal_rent_price`), como no legado. Alternativa: campo `purpose` explícito + um preço só. Mantive o legado porque um imóvel pode estar à venda e para alugar ao mesmo tempo.
2. **Features como M2M** em vez de string separada por `;`. Exige tabela de catálogo com `slug` estável para a importação XML mapear nomes.
3. **Fotos em tabela própria** (`PropertyPhoto`) em vez de JSON na coluna. Permite ordenar, marcar capa e gerar miniaturas por registro.
4. **`Advertiser` separado de `User`**: o `User` do boilerplate cuida de login, senha e verificação de e-mail; o `Advertiser` é o cadastro de negócio. Um anunciante sem login (importado) tem `user` nulo.
5. **Limites por anunciante como override nulo** (`property_limit` etc.). O legado copiava os valores do plano no cadastro; aqui o plano é a fonte e o override só existe quando um cliente negocia algo diferente.
6. **Contato e encomenda separados** (`ContactMessage` × `PropertyRequest`); no legado era uma tabela com 18 colunas opcionais.
7. **Estatísticas brutas ficam** (`PropertyView`, `PropertyContactClick`, `AdImpression`) porque o painel filtra por período; o cron condensa em `*Monthly` e purga as brutas depois de N dias.
8. Favoritos continuam em cookie (sem tabela), como no legado.
