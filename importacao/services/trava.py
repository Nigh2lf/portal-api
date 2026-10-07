"""Trava entre processos (os workers do gunicorn) usando ``GET_LOCK`` do MySQL."""

from __future__ import annotations

from contextlib import contextmanager

from django.db import connection


@contextmanager
def trava(nome: str, espera: int = 0):
    """
    Garante que só um processo execute o bloco; os demais recebem ``False`` e não esperam

    Args:
        nome: nome da trava (global no servidor MySQL)
        espera: segundos aguardando a trava

    Returns:
        ``True`` se a trava foi obtida
    """
    # GET_LOCK pertence à conexão: o bloco não pode fechar a conexão do Django no meio.
    with connection.cursor() as cur:
        cur.execute("SELECT GET_LOCK(%s, %s)", [nome, espera])
        obtida = cur.fetchone()[0] == 1
    try:
        yield obtida
    finally:
        if obtida:
            with connection.cursor() as cur:
                cur.execute("SELECT RELEASE_LOCK(%s)", [nome])
