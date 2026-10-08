"""Orquestra a importação de um anunciante (manual, lote ou cron). Lotes vivem em ``batches.py``."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from django.utils import timezone

from core.models import (
    Advertiser,
    PropertyPhoto,
    ScheduledTaskRun,
    XmlImportBatch,
    XmlImportError,
    XmlImportRun,
)
from core.services.images import gerar_miniaturas_capa
from core.services.public_cache import invalidation_batch
from xml_import.services import files
from xml_import.services.apply import Applier
from xml_import.services.cancellation import ImportCancelled, check_cancelled
from xml_import.services.download import ImportFailed, download_and_normalize
from xml_import.services.lock import lock

logger = logging.getLogger(__name__)
TIMEZONE = ZoneInfo("America/Sao_Paulo")
WINDOW_LOCK = "xml_import:window"


def advertisers_with_xml():
    return (
        Advertiser.objects.filter(
            is_published=True, deleted_at__isnull=True, integration__is_active=True
        )
        .exclude(integration__xml_url="")
        .select_related("integration__integrator", "plan")
    )


def _close_run(run, status, message=""):
    run.status = status
    run.error_message = message[:2000]
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error_message", "finished_at", "updated_at"])


def import_advertiser(
    advertiser, simulate=False, download=True, origin_label="manual", batch=None, cancel_check=None
):
    """
    Fluxos 1 e 3 de um anunciante: baixa e normaliza o feed, compara com o banco e aplica

    Args:
        advertiser: anunciante com integração XML
        simulate: só calcula a diferença e grava ``<id>.simulacao.json``; nada muda no banco
        download: ``False`` reaproveita o ``<id>.json`` já baixado
        origin_label: ``manual``, ``cron`` ou ``comando`` (vai para o histórico de cache)
        batch: lote ao qual a execução pertence (``XmlImportRun.batch``)
        cancel_check: consulta de cancelamento; checada depois do download e durante a comparação

    Returns:
        dict com o resumo (novos, alterados, iguais, excluídos, ignorados)

    Raises:
        ImportFailed: download, formato ou feed vazio (a execução fica ``FAILED``)
        ImportCancelled: o lote foi cancelado antes da gravação (a execução fica ``CANCELLED``)
    """
    with lock(f"xml_import:{advertiser.pk}") as acquired:
        if not acquired:
            raise ImportFailed("Já existe uma importação em andamento para este anunciante.")
        run = None
        if not simulate:
            run = XmlImportRun.objects.create(
                advertiser=advertiser,
                batch=batch,
                status=XmlImportRun.Status.RUNNING,
                started_at=timezone.now(),
            )
            XmlImportError.objects.filter(advertiser=advertiser).exclude(run=run).delete()
        try:
            data = download_and_normalize(advertiser) if download else files.read(advertiser.pk)
            if data is None:
                raise ImportFailed(
                    "Nenhum arquivo baixado para este anunciante; rode com download."
                )
            if not data["imoveis"]:
                raise ImportFailed("Feed sem imóveis: nada foi alterado.")
            check_cancelled(cancel_check)
            applier = Applier(advertiser)
            if simulate:
                result = applier.run(data["imoveis"], simulate=True, cancel_check=cancel_check)
            else:
                with invalidation_batch(user=f"xml_import:{origin_label}"):
                    result = applier.run(data["imoveis"], cancel_check=cancel_check)
        except ImportFailed as exc:
            if run:
                XmlImportError.objects.create(advertiser=advertiser, run=run, message=str(exc))
                _close_run(run, XmlImportRun.Status.FAILED, str(exc))
            if simulate:
                files.save(
                    advertiser.pk,
                    {"erro": str(exc), "gerado_em": timezone.now().isoformat()},
                    "simulacao.json",
                )
            raise
        except ImportCancelled as exc:
            if run:
                _close_run(run, XmlImportRun.Status.CANCELLED, str(exc))
            raise
        except Exception as exc:  # noqa: BLE001 - a execução não pode ficar "em andamento" para sempre
            if run:
                _close_run(run, XmlImportRun.Status.FAILED, f"Erro inesperado: {exc}")
            raise

        if simulate:
            detail = {
                **result.details(),
                "formato": data["formato"],
                "baixado_em": data["baixado_em"],
                "gerado_em": timezone.now().isoformat(),
            }
            files.save(advertiser.pk, detail, "simulacao.json")
            return detail

        XmlImportError.objects.bulk_create(
            [
                XmlImportError(
                    advertiser=advertiser,
                    run=run,
                    property_reference_code=i["codigo"][:45],
                    message=i["motivo"],
                )
                for i in result.ignored
            ],
            batch_size=500,
        )
        run.status = XmlImportRun.Status.SUCCESS
        run.finished_at = timezone.now()
        run.total_properties = result.total_feed
        run.valid_properties = len(result.created) + len(result.changed) + result.unchanged
        run.invalid_properties = len(result.ignored)
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "total_properties",
                "valid_properties",
                "invalid_properties",
                "updated_at",
            ]
        )
        advertiser.integration.last_imported_at = run.finished_at
        advertiser.integration.save(update_fields=["last_imported_at", "updated_at"])

        covers = PropertyPhoto.objects.filter(
            property__advertiser=advertiser, is_cover=True, thumbnail=""
        ).select_related("property")
        thumbnails, without_thumbnail = gerar_miniaturas_capa(covers)
        return {
            **result.summary(),
            "miniaturas": thumbnails,
            "capas_sem_miniatura": without_thumbnail,
            "formato": data["formato"],
        }


def _parse_time(hhmm, default):
    try:
        h, m = (int(x) for x in str(hhmm).split(":"))
        return time(h, m)
    except (TypeError, ValueError):
        return default


def window_end(now=None):
    """Datetime (com fuso) do fim da janela noturna de hoje, ``XML_IMPORT_WINDOW_END`` em Brasília."""
    now = (now or timezone.now()).astimezone(TIMEZONE)
    end = _parse_time(settings.XML_IMPORT_WINDOW_END, time(3, 0))
    return datetime.combine(now.date(), end, tzinfo=TIMEZONE)


def run_window(until=None, origin_label="cron"):
    """
    Importa todos os anunciantes com XML como um lote, quem está há mais tempo sem importar primeiro

    Não começa anunciante novo depois de ``until`` (padrão: fim da janela de hoje); quem ficou de
    fora vai primeiro na noite seguinte. Só um lote roda por vez (trava no MySQL), mesmo com
    vários workers do gunicorn. O resultado também vai para ``ScheduledTaskRun`` (histórico do cron).

    Args:
        until: datetime limite (com fuso) ou ``None``
        origin_label: ``cron`` ou ``comando``

    Returns:
        dict com o resumo da janela, ou ``{"pulado": motivo}``
    """
    from xml_import.services.batches import EmptyBatch, create_batch, run_batch

    origin = XmlImportBatch.Origin.CRON if origin_label == "cron" else XmlImportBatch.Origin.COMMAND
    try:
        batch = create_batch(
            origin=origin, deadline_at=until if until is not None else window_end()
        )
    except EmptyBatch as exc:
        return {"pulado": str(exc)}
    task = ScheduledTaskRun.objects.create(name="importacao_xml", started_at=timezone.now())
    summary = run_batch(batch.pk, origin_label=origin_label, lock_wait=0)
    batch.refresh_from_db()
    failed = batch.status == XmlImportBatch.Status.FAILED or "pulado" in summary
    task.status = ScheduledTaskRun.Status.FAILED if failed else ScheduledTaskRun.Status.SUCCESS
    task.finished_at = timezone.now()
    task.details = "\n".join([f"lote {batch.pk}", str(summary), batch.error_message])[:20000]
    task.save(update_fields=["status", "finished_at", "details", "updated_at"])
    return summary


def in_progress(advertiser) -> bool:
    """``True`` se há importação (ou simulação) rodando agora para o anunciante."""
    with connection.cursor() as cur:
        cur.execute("SELECT IS_USED_LOCK(%s)", [f"xml_import:{advertiser.pk}"])
        return cur.fetchone()[0] is not None


def start_in_background(advertiser_id, simulate=False):
    """
    Dispara ``import_advertiser`` numa thread (simulação pelo admin): a requisição não espera o download

    Importação de verdade pelo painel passa por lote (``batches.create_batch`` + ``start_batch_in_background``).

    Args:
        advertiser_id: pk do anunciante
        simulate: só calcula a diferença
    """

    def run():
        try:
            import_advertiser(
                advertisers_with_xml().get(pk=advertiser_id),
                simulate=simulate,
                origin_label="manual",
            )
        except ImportFailed:
            pass  # já registrado na execução (ou na simulação)
        except Exception:  # noqa: BLE001
            logger.exception("xml_import: falha na importação manual de %s", advertiser_id)
        finally:
            connection.close()

    threading.Thread(target=run, name=f"xml-import-{advertiser_id}", daemon=True).start()
