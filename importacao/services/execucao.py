"""Orquestra a importação: um anunciante (manual ou cron) e a janela noturna (todos)."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from django.db.models import F
from django.utils import timezone

from core.models import Advertiser, PropertyPhoto, ScheduledTaskRun, XmlImportError, XmlImportRun
from core.services.images import gerar_miniaturas_capa
from core.services.public_cache import invalidation_batch
from importacao.services import arquivos
from importacao.services.aplicar import Aplicador
from importacao.services.download import ErroImportacao, baixar_e_normalizar
from importacao.services.trava import trava

logger = logging.getLogger(__name__)
FUSO = ZoneInfo("America/Sao_Paulo")
TRAVA_JANELA = "importacao:janela"


def anunciantes_com_xml():
    return (
        Advertiser.objects.filter(is_published=True, deleted_at__isnull=True, integration__is_active=True)
        .exclude(integration__xml_url="")
        .select_related("integration__integrator", "plan")
    )


def importar_anunciante(advertiser, simular=False, baixar=True, origem="manual"):
    """
    Fluxos 1 e 3 de um anunciante: baixa e normaliza o feed, compara com o banco e aplica

    Args:
        advertiser: anunciante com integração XML
        simular: só calcula a diferença e grava ``<id>.simulacao.json``; nada muda no banco
        baixar: ``False`` reaproveita o ``<id>.json`` já baixado
        origem: ``manual``, ``cron`` ou ``comando`` (vai para o histórico de cache)

    Returns:
        dict com o resumo (novos, alterados, iguais, excluídos, ignorados)
    """
    with trava(f"importacao:{advertiser.pk}") as obtida:
        if not obtida:
            raise ErroImportacao("Já existe uma importação em andamento para este anunciante.")
        run = None
        if not simular:
            run = XmlImportRun.objects.create(advertiser=advertiser, started_at=timezone.now())
            XmlImportError.objects.filter(advertiser=advertiser).exclude(run=run).delete()
        try:
            dados = baixar_e_normalizar(advertiser) if baixar else arquivos.ler(advertiser.pk)
            if dados is None:
                raise ErroImportacao("Nenhum arquivo baixado para este anunciante; rode com download.")
            if not dados["imoveis"]:
                raise ErroImportacao("Feed sem imóveis: nada foi alterado.")
            aplicador = Aplicador(advertiser)
            if simular:
                res = aplicador.executar(dados["imoveis"], simular=True)
            else:
                with invalidation_batch(user=f"importacao:{origem}"):
                    res = aplicador.executar(dados["imoveis"])
        except ErroImportacao as exc:
            if run:
                XmlImportError.objects.create(advertiser=advertiser, run=run, message=str(exc))
                run.finished_at = timezone.now()
                run.save(update_fields=["finished_at", "updated_at"])
            if simular:
                arquivos.salvar(advertiser.pk, {"erro": str(exc), "gerado_em": timezone.now().isoformat()}, "simulacao.json")
            raise

        if simular:
            detalhe = {**res.detalhes(), "formato": dados["formato"], "baixado_em": dados["baixado_em"], "gerado_em": timezone.now().isoformat()}
            arquivos.salvar(advertiser.pk, detalhe, "simulacao.json")
            return detalhe

        XmlImportError.objects.bulk_create(
            [XmlImportError(advertiser=advertiser, run=run, property_reference_code=i["codigo"][:45], message=i["motivo"]) for i in res.ignorados],
            batch_size=500,
        )
        run.finished_at = timezone.now()
        run.total_properties = res.total_feed
        run.valid_properties = len(res.novos) + len(res.alterados) + res.iguais
        run.invalid_properties = len(res.ignorados)
        run.save(update_fields=["finished_at", "total_properties", "valid_properties", "invalid_properties", "updated_at"])
        advertiser.integration.last_imported_at = run.finished_at
        advertiser.integration.save(update_fields=["last_imported_at", "updated_at"])

        capas = PropertyPhoto.objects.filter(property__advertiser=advertiser, is_cover=True, thumbnail="").select_related("property")
        miniaturas, sem_miniatura = gerar_miniaturas_capa(capas)
        return {**res.resumo(), "miniaturas": miniaturas, "capas_sem_miniatura": sem_miniatura, "formato": dados["formato"]}


def _horario(hhmm, padrao):
    try:
        h, m = (int(x) for x in str(hhmm).split(":"))
        return time(h, m)
    except (TypeError, ValueError):
        return padrao


def rodar_janela(ate=None, origem="cron"):
    """
    Importa os anunciantes com XML, quem está há mais tempo sem importar primeiro, até o fim da janela

    Não começa anunciante novo depois de ``ate`` (padrão: ``IMPORTACAO_JANELA_FIM`` de hoje,
    horário de Brasília); quem ficou de fora vai primeiro na noite seguinte. Só um processo
    roda por vez (trava no MySQL), mesmo com vários workers do gunicorn.

    Args:
        ate: datetime limite (com fuso) ou ``None``
        origem: rótulo para o histórico

    Returns:
        dict com o resumo da janela, ou ``{"pulado": motivo}``
    """
    with trava(TRAVA_JANELA) as obtida:
        if not obtida:
            return {"pulado": "Outra importação já está rodando."}
        agora = timezone.now().astimezone(FUSO)
        if ate is None:
            fim = _horario(settings.IMPORTACAO_JANELA_FIM, time(3, 0))
            ate = datetime.combine(agora.date(), fim, tzinfo=FUSO)
        tarefa = ScheduledTaskRun.objects.create(name="importacao_xml", started_at=timezone.now())
        hoje = agora.date()
        fila = anunciantes_com_xml().order_by(F("integration__last_imported_at").asc(nulls_first=True), "name")
        ok, falhas, pulados, restantes = 0, [], 0, 0
        for adv in fila:
            ultima = adv.integration.last_imported_at
            if ultima and ultima.astimezone(FUSO).date() == hoje:
                pulados += 1
                continue
            if timezone.now() >= ate:
                restantes += 1
                continue
            try:
                importar_anunciante(adv, origem=origem)
                ok += 1
            except ErroImportacao as exc:
                falhas.append(f"{adv.name}: {exc}")
            except Exception as exc:  # noqa: BLE001 - um anunciante com problema não para a janela
                logger.exception("importacao: falha inesperada em %s", adv.pk)
                falhas.append(f"{adv.name}: erro inesperado ({exc})")
        resumo = {"importados": ok, "falhas": len(falhas), "ja_importados_hoje": pulados, "para_proxima_noite": restantes}
        tarefa.status = ScheduledTaskRun.Status.FAILED if falhas and not ok else ScheduledTaskRun.Status.SUCCESS
        tarefa.finished_at = timezone.now()
        tarefa.details = "\n".join([str(resumo), *falhas])[:20000]
        tarefa.save(update_fields=["status", "finished_at", "details", "updated_at"])
        return resumo


def em_andamento(advertiser) -> bool:
    """``True`` se há importação (ou simulação) rodando agora para o anunciante."""
    with connection.cursor() as cur:
        cur.execute("SELECT IS_USED_LOCK(%s)", [f"importacao:{advertiser.pk}"])
        return cur.fetchone()[0] is not None


def iniciar_em_segundo_plano(advertiser_id, simular=False):
    """
    Dispara ``importar_anunciante`` numa thread (botão do admin): a requisição não espera o download

    Args:
        advertiser_id: pk do anunciante
        simular: só calcula a diferença
    """

    def rodar():
        try:
            importar_anunciante(anunciantes_com_xml().get(pk=advertiser_id), simular=simular, origem="manual")
        except ErroImportacao:
            pass  # já registrado na execução (ou na simulação)
        except Exception:  # noqa: BLE001
            logger.exception("importacao: falha na importação manual de %s", advertiser_id)
        finally:
            connection.close()

    threading.Thread(target=rodar, name=f"importacao-{advertiser_id}", daemon=True).start()
