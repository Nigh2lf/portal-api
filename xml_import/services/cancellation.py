"""Cancelamento cooperativo da importação.

Quem roda a importação recebe um ``cancel_check`` (função sem argumentos que devolve ``True``
quando o admin pediu para parar) e chama ``check_cancelled`` nos pontos seguros: entre anunciantes,
depois do download e a cada bloco de imóveis comparados. Nunca dentro da gravação
(``Applier._save`` roda em ``transaction.atomic``), para não deixar anunciante meio aplicado.
"""

from __future__ import annotations

from collections.abc import Callable

CancelCheck = Callable[[], bool] | None


class ImportCancelled(Exception):
    """O admin cancelou o lote; a importação para no próximo ponto seguro."""


def check_cancelled(cancel_check: CancelCheck) -> None:
    """
    Levanta ``ImportCancelled`` se o cancelamento foi pedido

    Args:
        cancel_check: função que consulta o pedido de cancelamento, ou ``None`` (nunca cancela)
    """
    if cancel_check is not None and cancel_check():
        raise ImportCancelled("Importação cancelada pelo administrador.")
