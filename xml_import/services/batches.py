"""Lotes da importação XML: todos os anunciantes ou os escolhidos, com progresso e cancelamento.

- O lote (``XmlImportBatch``) guarda a fila de anunciantes e os contadores; cada anunciante vira
  um ``XmlImportRun`` ligado ao lote quando começa (os que não rodaram ganham ``CANCELLED`` ou
  ``SKIPPED`` no fim, para o histórico ficar completo).
- Só um lote roda por vez (``WINDOW_LOCK`` no MySQL). Lotes criados enquanto outro roda ficam
  ``QUEUED`` e esperam a trava.
- Cancelar é cooperativo: o admin marca ``CANCELLING`` e o processo para no próximo ponto seguro
  (entre anunciantes, depois do download, a cada bloco de imóveis comparados), nunca no meio da
  gravação de um anunciante.
- ``heartbeat_at`` é renovado a cada checagem; um lote ``RUNNING`` sem batimento há
  ``ABANDONED_AFTER`` (container reiniciado no deploy, por exemplo) é fechado como ``FAILED`` por
  ``active_batch``.
- O lote pedido pelo painel roda num processo separado (``manage.py import_xml --batch``, ver
  ``spawn.py``), para a memória da importação não ficar presa no worker do gunicorn. Com
  ``XML_IMPORT_SUBPROCESS=false`` roda numa thread do próprio worker.
"""

from __future__ import annotations

import gc
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone

from core.models import Advertiser, XmlImportBatch, XmlImportRun
from xml_import.services.cancellation import ImportCancelled
from xml_import.services.download import ImportFailed
from xml_import.services.execution import (
    TIMEZONE,
    WINDOW_LOCK,
    advertisers_with_xml,
    import_advertiser,
)
from xml_import.services.lock import lock
from xml_import.services.memory import describe as describe_memory

logger = logging.getLogger(__name__)

# Lote RUNNING sem batimento há mais que isso foi abandonado (processo morreu).
ABANDONED_AFTER = timedelta(minutes=15)
# Quanto um lote na fila espera a trava de outro lote (segundos).
LOCK_WAIT = 4 * 60 * 60

Status = XmlImportBatch.Status
RunStatus = XmlImportRun.Status


class EmptyBatch(Exception):
    """Nenhum anunciante com XML ativo para importar."""


class BatchNotCancellable(Exception):
    """O lote já terminou (ou já está cancelando)."""


def advertiser_queue(advertiser_ids=None):
    """
    Anunciantes do lote, na ordem de execução

    Args:
        advertiser_ids: UUIDs escolhidos, ou ``None`` para todos os anunciantes com XML ativo

    Returns:
        (lista de anunciantes, UUIDs pedidos que não têm XML ativo)
    """
    qs = advertisers_with_xml()
    if advertiser_ids is None:
        return list(
            qs.order_by(F("integration__last_imported_at").asc(nulls_first=True), "name")
        ), []
    requested = [str(i) for i in advertiser_ids]
    by_id = {str(a.pk): a for a in qs.filter(pk__in=requested)}
    ordered = sorted(by_id.values(), key=lambda a: a.name.lower())
    return ordered, [i for i in dict.fromkeys(requested) if i not in by_id]


def advertisers_in_active_batches():
    """UUIDs (texto) dos anunciantes que ainda vão rodar ou estão rodando em algum lote ativo."""
    pending = set()
    for batch in XmlImportBatch.objects.filter(status__in=XmlImportBatch.ACTIVE_STATUSES):
        done_ids = set(map(str, batch.runs.values_list("advertiser_id", flat=True)))
        if batch.current_advertiser_id:
            done_ids.discard(str(batch.current_advertiser_id))
        pending.update(i for i in batch.advertiser_ids if i not in done_ids)
    return pending


def create_batch(
    *, advertiser_ids=None, origin=XmlImportBatch.Origin.MANUAL, user=None, deadline_at=None
):
    """
    Cria o lote ``QUEUED`` com a fila resolvida; não executa

    Args:
        advertiser_ids: UUIDs escolhidos, ou ``None`` para todos
        origin: painel, cron ou comando
        user: quem pediu (``created_by``)
        deadline_at: não começa anunciante novo depois deste horário (janela noturna)

    Returns:
        o ``XmlImportBatch`` criado

    Raises:
        EmptyBatch: nenhum anunciante com XML ativo
    """
    advertisers, _ = advertiser_queue(advertiser_ids)
    if not advertisers:
        raise EmptyBatch("Nenhum anunciante com XML ativo para importar.")
    return XmlImportBatch.objects.create(
        origin=origin,
        scope=XmlImportBatch.Scope.ALL if advertiser_ids is None else XmlImportBatch.Scope.SELECTED,
        advertiser_ids=[str(a.pk) for a in advertisers],
        total_advertisers=len(advertisers),
        deadline_at=deadline_at,
        created_by=user,
    )


def cancel_batch(batch):
    """
    Pede o cancelamento: ``QUEUED`` cancela na hora; ``RUNNING`` vira ``CANCELLING`` e para no próximo ponto seguro

    Args:
        batch: ``XmlImportBatch``

    Returns:
        o lote atualizado

    Raises:
        BatchNotCancellable: já terminou ou já está cancelando
    """
    if batch.status == Status.QUEUED:
        updated = XmlImportBatch.objects.filter(pk=batch.pk, status=Status.QUEUED).update(
            status=Status.CANCELLED,
            finished_at=timezone.now(),
            cancelled=F("total_advertisers"),
            done=F("total_advertisers"),
        )
        if updated:
            _close_pending(batch, RunStatus.CANCELLED, "Lote cancelado antes de começar.")
    elif batch.status == Status.RUNNING:
        updated = XmlImportBatch.objects.filter(pk=batch.pk, status=Status.RUNNING).update(
            status=Status.CANCELLING
        )
    else:
        updated = 0
    if not updated:
        raise BatchNotCancellable("Este lote não está na fila nem em execução.")
    batch.refresh_from_db()
    return batch


def _cancel_check(batch_id):
    """Renova o batimento e responde se o admin pediu para parar (uma consulta por checagem)."""

    def cancel_check():
        XmlImportBatch.objects.filter(pk=batch_id).update(heartbeat_at=timezone.now())
        return XmlImportBatch.objects.filter(pk=batch_id, status=Status.CANCELLING).exists()

    return cancel_check


def _close_pending(batch, status, message):
    """Cria as execuções dos anunciantes que não chegaram a rodar, para o histórico do lote ficar completo."""
    done_ids = set(map(str, batch.runs.values_list("advertiser_id", flat=True)))
    pending = [i for i in batch.advertiser_ids if i not in done_ids]
    if not pending:
        return 0
    now = timezone.now()
    XmlImportRun.objects.bulk_create(
        [
            XmlImportRun(
                advertiser=advertiser,
                batch=batch,
                status=status,
                error_message=message,
                started_at=now,
                finished_at=now,
            )
            for advertiser in Advertiser.objects.filter(pk__in=pending)
        ]
    )
    return len(pending)


def _run_not_executed(batch, advertiser, status, message):
    now = timezone.now()
    XmlImportRun.objects.create(
        advertiser=advertiser,
        batch=batch,
        status=status,
        error_message=message,
        started_at=now,
        finished_at=now,
    )


def run_batch(batch_id, origin_label="manual", lock_wait=LOCK_WAIT):
    """
    Roda o lote até o fim (síncrono): chame numa thread, no cron ou no comando

    Args:
        batch_id: pk do ``XmlImportBatch`` (precisa estar ``QUEUED``)
        origin_label: rótulo para o histórico de cache (``manual``, ``cron``, ``comando``)
        lock_wait: segundos esperando outro lote terminar; ``0`` desiste na hora

    Returns:
        dict com o resumo (``importados``, ``falhas``, ``ja_importados_hoje``, ``para_proxima_noite``,
        ``cancelados``) ou ``{"pulado": motivo}``
    """
    batch = XmlImportBatch.objects.filter(pk=batch_id).first()
    if batch is None or batch.status != Status.QUEUED:
        return {"pulado": "Lote não está na fila."}
    with lock(WINDOW_LOCK, wait=lock_wait) as acquired:
        if not acquired:
            _finish(batch, Status.FAILED, "Outra importação já está rodando.", RunStatus.SKIPPED)
            return {"pulado": "Outra importação já está rodando."}
        started = XmlImportBatch.objects.filter(pk=batch.pk, status=Status.QUEUED).update(
            status=Status.RUNNING, started_at=timezone.now(), heartbeat_at=timezone.now()
        )
        if not started:  # cancelado enquanto esperava a trava
            return {"pulado": "Lote cancelado antes de começar."}
        batch.refresh_from_db()
        return _process(batch, origin_label)


def _process(batch, origin_label):
    cancel_check = _cancel_check(batch.pk)
    by_id = {str(a.pk): a for a in advertisers_with_xml().filter(pk__in=batch.advertiser_ids)}
    today = timezone.now().astimezone(TIMEZONE).date()
    already_today = next_night = 0
    failures = []
    interrupted = False

    for advertiser_id in batch.advertiser_ids:
        if cancel_check():
            interrupted = True
            break
        advertiser = by_id.get(advertiser_id)
        if advertiser is None:
            removed = Advertiser.objects.filter(pk=advertiser_id).first()
            if removed is not None:
                _run_not_executed(batch, removed, RunStatus.FAILED, "Anunciante sem XML ativo.")
            batch.failed += 1
        elif (
            batch.origin == XmlImportBatch.Origin.CRON
            and (last := advertiser.integration.last_imported_at)
            and last.astimezone(TIMEZONE).date() == today
        ):
            _run_not_executed(batch, advertiser, RunStatus.SKIPPED, "Já importado hoje.")
            batch.skipped += 1
            already_today += 1
        elif batch.deadline_at and timezone.now() >= batch.deadline_at:
            _run_not_executed(
                batch, advertiser, RunStatus.SKIPPED, "Fim da janela; fica para a próxima noite."
            )
            batch.skipped += 1
            next_night += 1
        else:
            batch.current_advertiser = advertiser
            batch.save(update_fields=["current_advertiser", "updated_at"])
            try:
                import_advertiser(
                    advertiser, origin_label=origin_label, batch=batch, cancel_check=cancel_check
                )
                batch.ok += 1
            except ImportCancelled:
                batch.cancelled += 1
                batch.done += 1
                interrupted = True
                break
            except ImportFailed as exc:
                batch.failed += 1
                failures.append(f"{advertiser.name}: {exc}")
            except Exception as exc:  # noqa: BLE001 - um anunciante com problema não para o lote
                logger.exception(
                    "xml_import: falha inesperada em %s (lote %s)", advertiser.pk, batch.pk
                )
                batch.failed += 1
                failures.append(f"{advertiser.name}: erro inesperado ({exc})")
        batch.done += 1
        batch.heartbeat_at = timezone.now()
        batch.save(
            update_fields=[
                "done",
                "ok",
                "failed",
                "skipped",
                "cancelled",
                "heartbeat_at",
                "updated_at",
            ]
        )
        # Solta a árvore do feed e as fotos do anunciante antes do próximo; o log mostra
        # qual anunciante pesa (o pico só cresce).
        gc.collect()
        logger.info(
            "xml_import: lote %s, %d/%d (%s): memória %s",
            batch.pk,
            batch.done,
            batch.total_advertisers,
            advertiser.name if advertiser is not None else advertiser_id,
            describe_memory(),
        )

    batch.refresh_from_db(fields=["status"])
    if interrupted or batch.status == Status.CANCELLING:
        remaining = _close_pending(batch, RunStatus.CANCELLED, "Lote cancelado pelo administrador.")
        batch.cancelled += remaining
        batch.done += remaining
        status = Status.CANCELLED
    elif batch.ok == 0 and batch.failed > 0:
        status = Status.FAILED
    elif batch.failed > 0:
        status = Status.PARTIAL
    else:
        status = Status.SUCCESS
    _finish(batch, status, "\n".join(failures))
    return {
        "importados": batch.ok,
        "falhas": batch.failed,
        "ja_importados_hoje": already_today,
        "para_proxima_noite": next_night,
        "cancelados": batch.cancelled,
    }


def _finish(batch, status, message, pending_as=None):
    if pending_as is not None:
        closed = _close_pending(batch, pending_as, message)
        if pending_as == RunStatus.CANCELLED:
            batch.cancelled += closed
        else:
            batch.skipped += closed
        batch.done += closed
    batch.status = status
    batch.error_message = message[:20000]
    batch.finished_at = timezone.now()
    batch.current_advertiser = None
    batch.save(
        update_fields=[
            "status",
            "error_message",
            "finished_at",
            "current_advertiser",
            "done",
            "ok",
            "failed",
            "skipped",
            "cancelled",
            "updated_at",
        ]
    )


def run_batch_safely(batch_id, origin_label="manual"):
    """
    ``run_batch`` que nunca deixa o lote ``RUNNING`` para sempre: erro inesperado fecha como ``FAILED``

    Args:
        batch_id: pk do lote ``QUEUED``
        origin_label: rótulo para o histórico de cache

    Returns:
        o resumo de ``run_batch``, ou ``{"erro": mensagem}``
    """
    try:
        return run_batch(batch_id, origin_label=origin_label)
    except Exception:  # noqa: BLE001
        logger.exception("xml_import: falha no lote %s", batch_id)
        message = "Erro inesperado no processamento do lote."
        batch = XmlImportBatch.objects.filter(
            pk=batch_id, status__in=XmlImportBatch.ACTIVE_STATUSES
        ).first()
        if batch:
            _finish(batch, Status.FAILED, message, RunStatus.SKIPPED)
        return {"erro": message}


def start_batch_in_background(batch_id, origin_label="manual"):
    """
    Dispara o lote sem esperar: a requisição do painel responde na hora

    Num processo separado (padrão, ``XML_IMPORT_SUBPROCESS``) ou numa thread do worker.
    O disparo espera o commit da transação atual, para o processo filho enxergar o lote.

    Args:
        batch_id: pk do lote ``QUEUED``
        origin_label: rótulo para o histórico de cache (só na thread; o processo lê do lote)
    """
    if getattr(settings, "XML_IMPORT_SUBPROCESS", True):
        from xml_import.services.spawn import spawn_import_command

        transaction.on_commit(lambda: spawn_import_command("--batch", batch_id))
        return

    def run():
        try:
            run_batch_safely(batch_id, origin_label=origin_label)
        finally:
            connection.close()

    threading.Thread(target=run, name=f"xml-import-batch-{batch_id}", daemon=True).start()


def mark_abandoned():
    """Fecha como ``FAILED`` os lotes em execução sem batimento há ``ABANDONED_AFTER`` (processo morreu no meio)."""
    limit = timezone.now() - ABANDONED_AFTER
    abandoned = XmlImportBatch.objects.filter(
        status__in=(Status.RUNNING, Status.CANCELLING), heartbeat_at__lt=limit
    )
    for batch in abandoned:
        logger.warning(
            "xml_import: lote %s sem batimento desde %s; fechado como FAILED",
            batch.pk,
            batch.heartbeat_at,
        )
        batch.runs.filter(status=RunStatus.RUNNING).update(
            status=RunStatus.FAILED,
            error_message="Processo reiniciado durante a importação.",
            finished_at=timezone.now(),
        )
        _finish(
            batch,
            Status.FAILED,
            "Processo reiniciado durante a importação (sem batimento).",
            RunStatus.SKIPPED,
        )


def active_batch():
    """O lote em andamento (ou na fila) mais antigo, depois de fechar os abandonados; ``None`` se não houver."""
    mark_abandoned()
    return (
        XmlImportBatch.objects.filter(status__in=XmlImportBatch.ACTIVE_STATUSES)
        .select_related("current_advertiser", "created_by")
        .order_by("created_at")
        .first()
    )
