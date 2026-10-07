"""Arquivo JSON normalizado de cada anunciante, em ``MEDIA_ROOT/importacao/<id>.json``.

Fica no disco do servidor da API (não no S3): é refeito a cada importação e se
perde num deploy sem prejuízo, porque o fluxo 1 baixa de novo.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from django.conf import settings

PASTA = "importacao"


def pasta() -> Path:
    p = Path(settings.MEDIA_ROOT) / PASTA
    p.mkdir(parents=True, exist_ok=True)
    return p


def caminho(advertiser_id, sufixo: str = "json") -> Path:
    return pasta() / f"{advertiser_id}.{sufixo}"


def salvar(advertiser_id, dados: dict, sufixo: str = "json") -> Path:
    """
    Grava o JSON substituindo o anterior de forma atômica (escreve e renomeia)

    Args:
        advertiser_id: id do anunciante
        dados: conteúdo serializável
        sufixo: extensão (``json`` ou ``simulacao.json``)

    Returns:
        caminho do arquivo
    """
    destino = caminho(advertiser_id, sufixo)
    temp = destino.with_suffix(destino.suffix + ".tmp")
    temp.write_text(json.dumps(dados, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(temp, destino)
    return destino


def ler(advertiser_id, sufixo: str = "json") -> dict | None:
    p = caminho(advertiser_id, sufixo)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
