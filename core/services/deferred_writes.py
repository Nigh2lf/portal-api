"""Gravações de estatística fora do caminho da resposta (busca, visualização de imóvel).

Uma única thread de fundo executa as gravações em fila. Como ela vive enquanto o
processo vive, reaproveita a conexão com o banco (``CONN_MAX_AGE``) e a resposta ao
visitante não espera o banco. Perder alguns registros se o processo cair é aceitável:
são contadores, não dados de negócio.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="deferred-writes")


def _run(fn, args, kwargs, in_worker=True):
    # Só a thread de fundo recicla a própria conexão. Inline (DEFERRED_WRITES_ENABLED=False,
    # usado nos testes) roda na thread da requisição e fechar a conexão ali quebraria a
    # transação em andamento.
    if in_worker:
        close_old_connections()
    try:
        fn(*args, **kwargs)
    except Exception:  # noqa: BLE001 - estatística nunca derruba nada
        logger.exception("deferred_writes: falha ao gravar")


def defer(fn, *args, **kwargs):
    """
    Agenda ``fn(*args, **kwargs)`` na thread de gravações

    Args:
        fn: função que grava (ex.: ``Model.objects.create``)
        args: argumentos posicionais
        kwargs: argumentos nomeados
    """
    if not getattr(settings, "DEFERRED_WRITES_ENABLED", True):
        _run(fn, args, kwargs, in_worker=False)
        return
    _executor.submit(_run, fn, args, kwargs)
