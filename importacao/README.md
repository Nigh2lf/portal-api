# App `importacao` — importação dos XML dos anunciantes

Substitui `xml/salvartodosxml.php`, `xml/salvartodosxmllocal.php` e `xml/importarxml.php`
do legado. Models continuam em `core/models.py` (`AdvertiserIntegration`,
`XmlImportRun`, `XmlImportError`, `RejectedProperty`); aqui só há serviços e comandos.

## Fluxos

1. **Baixar e normalizar** (`services/download.py`): baixa `AdvertiserIntegration.xml_url`,
   escolhe o leitor (`formatos/`) e grava `media/importacao/<id do anunciante>.json`
   no formato normalizado (ver `formatos/base.py`), substituindo o anterior.
2. O snapshot do banco do legado (`PI-<id>.xml`) **não existe mais**: o fluxo 3 compara
   direto com o banco.
3. **Comparar e aplicar** (`services/aplicar.py`): casa pelo código do anunciante e grava
   em lote o que é novo ou mudou; exclui o que saiu do feed; registra os ignorados.
   Gera a miniatura (S3) só das capas novas ou trocadas.

`services/execucao.py` orquestra: `importar_anunciante` (um anunciante; manual, cron ou
comando) e `rodar_janela` (todos, por ordem de `last_imported_at`).

## Formatos (`formatos/leitores.py`)

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

- **Cron:** `core/cron/jobs.py::importar_xml_noturno`, às `IMPORTACAO_JANELA_INICIO`
  (01:00, horário de Brasília). Não inicia anunciante depois de `IMPORTACAO_JANELA_FIM`
  (03:00); quem ficou de fora vai primeiro na noite seguinte. Exige `RUN_CRON=true`.
  Com vários workers, `GET_LOCK` do MySQL garante uma execução só.
- **Admin:** tela "Importações XML" → "Importar agora" (simular ou importar), via
  `POST /api/v1/xml-import-runs/run/`, em segundo plano.
- **Comando:** `python manage.py importar_xml --anunciante <Id_Cliente|UUID> [--simular] [--sem-baixar]`,
  `--todos` ou `--janela`.

Sem e-mail de relatório por enquanto.
