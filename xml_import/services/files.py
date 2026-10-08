"""Arquivo JSON normalizado de cada anunciante, em ``MEDIA_ROOT/xml_import/<id>.json``.

Fica no disco do servidor da API (não no S3): é refeito a cada importação e se
perde num deploy sem prejuízo, porque o fluxo 1 baixa de novo.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from django.conf import settings

FOLDER = "xml_import"


def folder() -> Path:
    p = Path(settings.MEDIA_ROOT) / FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p


def path(advertiser_id, suffix: str = "json") -> Path:
    return folder() / f"{advertiser_id}.{suffix}"


def save(advertiser_id, data: dict, suffix: str = "json") -> Path:
    """
    Grava o JSON substituindo o anterior de forma atômica (escreve e renomeia)

    Args:
        advertiser_id: id do anunciante
        data: conteúdo serializável
        suffix: extensão (``json`` ou ``simulacao.json``)

    Returns:
        caminho do arquivo
    """
    target = path(advertiser_id, suffix)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(temp, target)
    return target


def read(advertiser_id, suffix: str = "json") -> dict | None:
    p = path(advertiser_id, suffix)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
