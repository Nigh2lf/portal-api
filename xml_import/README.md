# App `xml_import` — importação dos XML dos anunciantes

Substitui `xml/salvartodosxml.php`, `xml/salvartodosxmllocal.php` e `xml/importarxml.php`
do legado. Models continuam em `core/models.py` (`AdvertiserIntegration`, `XmlImportBatch`,
`XmlImportRun`, `XmlImportError`, `RejectedProperty`); aqui só há serviços e comandos.

## Fluxos

1. **Baixar e normalizar** (`services/download.py`): baixa `AdvertiserIntegration.xml_url`,
   escolhe o leitor (`formats/`) e grava `media/xml_import/<id do anunciante>.json`
   no formato normalizado (ver `formats/base.py`), substituindo o anterior.
2. O snapshot do banco do legado (`PI-<id>.xml`) **não existe mais**: o fluxo 3 compara
   direto com o banco.
3. **Comparar e aplicar** (`services/apply.py`): casa pelo código do anunciante e grava
   em lote o que é novo ou mudou; exclui o que saiu do feed; registra os ignorados.
   Gera a miniatura (S3) só das capas novas ou trocadas.

`services/execution.py` orquestra um anunciante (`import_advertiser`) e a janela noturna
(`run_window`). `services/batches.py` cuida dos **lotes** (`XmlImportBatch`): fila de
anunciantes, contadores de progresso, batimento (`heartbeat_at`) e cancelamento
cooperativo (`services/cancellation.py`), checado entre anunciantes, depois do download e a
cada 200 imóveis comparados, nunca durante a gravação de um anunciante.

## Formatos (`formats/readers.py`)

| Integrador (`legacy_id`) | Formato | Itens |
|---|---|---|
| 1 Petrópolis Imóveis (TrustImóvel) | `pi` | `Imoveis/Imovel` |
| 2 Value Gaia | `value_gaia` | `Imoveis/Imovel` |
| 3 Viva Real (VRSync) | `viva_real` | `Listings/Listing` |
| 4 Union Software | `union` | `Imoveis/Imovel` |
| 5 Vista (feed vistahost) | `vista` | `Imovel` direto na raiz |

A estrutura do arquivo prevalece sobre o integrador cadastrado (exceto PI × Value
Gaia, que têm a mesma estrutura). Tabelas de tipo e de características portadas do
legado; bugs documentados corrigidos (item/foto único, "Sale/Rent", flags repetidas).

As chaves do JSON normalizado (`codigo`, `preco_venda`, `fotos`...) e da simulação
(`novos`, `alterados`, `codigos_alterados`...) são contrato de dados lido pelo painel e
ficam em português; identificadores de código são em inglês.

## Regras

- Limite do plano: entram os N primeiros do feed; fotos até o limite; destaque e
  superdestaque na ordem do feed até os limites do anunciante.
- Cidade desconhecida ou sem preço: ignorado (o imóvel existente fica como está).
  Código barrado em `RejectedProperty`: ignorado. Tudo vira `XmlImportError` da execução.
- Tipo desconhecido → "Outros"; bairro desconhecido → texto em `neighborhood_name`.
  Nomes casam sem acento/maiúsculas, também pelos `import_aliases`.
- Fora do feed (ou acima do limite) → **excluído** (as estatísticas ficam no anunciante:
  visitas, cliques e mensagens têm `SET_NULL`). Feed sem imóveis não exclui nada.
- Código repetido no banco para o mesmo anunciante: fica um, os demais são excluídos.

## Execução

- **Cron:** `core/cron/jobs.py::nightly_xml_import`, às `XML_IMPORT_WINDOW_START`
  (01:00, horário de Brasília). Não inicia anunciante depois de `XML_IMPORT_WINDOW_END`
  (03:00); quem ficou de fora vai primeiro na noite seguinte. Exige `RUN_CRON=true`.
  Com vários workers, `GET_LOCK` do MySQL garante uma execução só.
- **Admin:** tela "Importações XML" → "Importar agora" (todos os anunciantes ou os
  escolhidos; simulação com um só), via `POST /api/v1/xml-import-runs/batches/`.
  Progresso em `GET .../batches/active/`; cancelar em `POST .../batches/<id>/cancel/`.
- **Comando:** `python manage.py import_xml --advertiser <Id_Cliente|UUID> [--simulate] [--no-download]`,
  `--all` ou `--window`.

Sem e-mail de relatório por enquanto.
