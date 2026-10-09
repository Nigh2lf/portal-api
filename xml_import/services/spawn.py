"""Roda ``manage.py import_xml`` num processo separado.

A importação (download, árvore do XML, miniaturas com Pillow) chega a centenas de MB, e o
Python não devolve ao sistema a memória que já pegou: se rodasse numa thread do gunicorn, o
worker ficaria com esse tamanho até reiniciar. Num processo filho a memória volta inteira
quando ele termina. O filho sobrevive à reciclagem do worker (sessão própria), mas não a um
redeploy do container: aí ``batches.mark_abandoned`` fecha o lote como falho.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys

from django.conf import settings

logger = logging.getLogger(__name__)


def spawn_import_command(*args) -> subprocess.Popen:
    """
    Dispara ``python manage.py import_xml <args>`` e devolve sem esperar

    Args:
        *args: argumentos do comando (``"--batch", id`` / ``"--window"`` / ``"--advertiser", id``)

    Returns:
        o ``Popen`` (saída vai para o stdout/stderr do servidor, ou seja, para os logs)
    """
    cmd = [sys.executable, str(settings.BASE_DIR / "manage.py"), "import_xml", *map(str, args)]
    # O filho não liga o APScheduler: só o processo web agenda jobs.
    env = {**os.environ, "RUN_CRON": "false"}
    kwargs: dict = {"cwd": str(settings.BASE_DIR), "env": env, "close_fds": True}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    logger.info("xml_import: iniciando processo separado: import_xml %s", " ".join(cmd[3:]))
    return subprocess.Popen(cmd, **kwargs)  # noqa: S603 - argumentos fixos, sem shell
