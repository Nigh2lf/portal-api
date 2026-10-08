"""Utilitários comuns aos leitores de feed e o formato normalizado de imóvel.

Formato normalizado (o que vai para ``media/xml_import/<id>.json``), um dict por imóvel::

    {
      "codigo": "AP123", "destaque": 0|1|2, "tipo": "Apartamento",
      "cidade": "Petrópolis", "bairro": "Centro", "uf": "RJ",
      "quartos": 2, "banheiros": 1, "suites": 0, "vagas": 1,
      "area_util": "80.00" | None, "area_total": None,
      "preco_venda": "450000.00" | None, "preco_locacao": None, "preco_temporada": None,
      "dentro_condominio": False,
      "infra_imovel": ["Piscina"], "infra_condominio": [],
      "descricao": "...",
      "fotos": [{"url": "https://...", "capa": True}],
      "taxas": [{"descricao": "IPTU", "valor": "1200.00", "obs": ""}]
    }

As chaves desse dict são o contrato dos arquivos JSON gravados e da simulação lida pelo painel.
"""

from __future__ import annotations

import html
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

PROPERTY_KEYS = (
    "codigo",
    "destaque",
    "tipo",
    "cidade",
    "bairro",
    "uf",
    "quartos",
    "banheiros",
    "suites",
    "vagas",
    "area_util",
    "area_total",
    "preco_venda",
    "preco_locacao",
    "preco_temporada",
    "dentro_condominio",
    "infra_imovel",
    "infra_condominio",
    "descricao",
    "fotos",
    "taxas",
)


class InvalidFormat(Exception):
    """O conteúdo baixado não é um feed do formato esperado."""


# ------------------------------------------------------------------ XML
def local_name(tag: str) -> str:
    """Nome da tag sem namespace (``{ns}Listing`` → ``Listing``)."""
    return tag.rsplit("}", 1)[-1]


def parse(content: bytes) -> ET.Element:
    try:
        return ET.fromstring(content)  # noqa: S314 - feeds XML cadastrados pelo admin, sem entidades externas
    except ET.ParseError as exc:
        raise InvalidFormat(f"XML inválido: {exc}") from exc


def child(element: ET.Element | None, *path: str) -> ET.Element | None:
    """Desce pelos nomes (sem namespace, sensível a maiúsculas); ``None`` se faltar algum."""
    current = element
    for name in path:
        if current is None:
            return None
        current = next((c for c in current if local_name(c.tag) == name), None)
    return current


def children(element: ET.Element | None, name: str) -> list[ET.Element]:
    return [] if element is None else [c for c in element if local_name(c.tag) == name]


def text(element: ET.Element | None, *path: str) -> str:
    target = child(element, *path) if path else element
    if target is None:
        return ""
    return "".join(target.itertext()).strip()


# --------------------------------------------------------------- valores
def number(value) -> Decimal | None:
    """
    Converte valores dos feeds em Decimal: ``1.500.000``, ``1500.00``, ``1.500,00``, ``R$ 1.500``

    Args:
        value: texto ou número

    Returns:
        Decimal ou ``None`` quando vazio/zero/inválido
    """
    s = str(value or "").strip()
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        # O separador que aparece por último é o decimal.
        s = (
            s.replace(".", "").replace(",", ".")
            if s.rfind(",") > s.rfind(".")
            else s.replace(",", "")
        )
    elif "," in s:
        parts = s.split(",")
        s = s.replace(",", ".") if len(parts) == 2 and len(parts[1]) <= 2 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        # "1.500.000" ou "150.000": ponto como milhar.
        s = s.replace(".", "")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return d if d > 0 else None


def integer(value) -> int:
    d = number(value)
    return int(d) if d is not None else 0


def decimal_str(d: Decimal | None) -> str | None:
    return None if d is None else str(d.quantize(Decimal("0.01")))


def clean_text(value: str) -> str:
    """HTML dos feeds vira texto: entidades resolvidas, tags removidas, quebras de linha mantidas."""
    s = html.unescape(str(value or ""))
    s = re.sub(r"(?i)<br\s*/?>|</p>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def feature_list(value: str) -> list[str]:
    """``"Piscina;Sauna;"`` → ``["Piscina", "Sauna"]`` (sem repetidos, na ordem)."""
    seen, out = set(), []
    for part in str(value or "").split(";"):
        name = clean_text(part).strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            out.append(name)
    return out


def normalize_name(value: str) -> str:
    """Chave de comparação de nomes: minúsculas, sem acento e sem espaços extras."""
    s = unicodedata.normalize("NFD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def property_record(**fields) -> dict:
    """Monta um imóvel normalizado com todas as chaves (valores ausentes viram o padrão)."""
    record = {
        "codigo": "",
        "destaque": 0,
        "tipo": "",
        "cidade": "",
        "bairro": "",
        "uf": "",
        "quartos": 0,
        "banheiros": 0,
        "suites": 0,
        "vagas": 0,
        "area_util": None,
        "area_total": None,
        "preco_venda": None,
        "preco_locacao": None,
        "preco_temporada": None,
        "dentro_condominio": False,
        "infra_imovel": [],
        "infra_condominio": [],
        "descricao": "",
        "fotos": [],
        "taxas": [],
    }
    record.update(fields)
    record["codigo"] = str(record["codigo"] or "").strip()
    return record


def photo(url: str, cover: bool) -> dict | None:
    url = (url or "").strip().replace("\t", "")
    return {"url": url[:500], "capa": bool(cover)} if len(url) > 10 else None


def fee(description: str, value, notes: str = "") -> dict | None:
    v = number(value)
    return (
        {"descricao": description, "valor": decimal_str(v), "obs": (notes or "")[:300]}
        if v
        else None
    )


# Tipos de Value Gaia e Vista (tabela PadronizarTipo do legado).
GAIA_VISTA_TYPES = {
    "Apartamento": "Apartamento",
    "Apartamento Duplex": "Apartamento",
    "Apartamento Triplex": "Apartamento",
    "Sobrado": "Apartamento",
    "Penthouse": "Apartamento",
    "Casa": "Casa",
    "Bangalô": "Casa",
    "Edícula": "Casa",
    "Loja": "Loja",
    "Cobertura": "Cobertura",
    "": "Terreno Comercial",
    "Flat": "Flat",
    "Sala": "Sala",
    "Salão": "Sala",
    "Terreno": "Terreno Residencial",
    "Fazenda": "Fazenda / Sítio",
    "Sítio": "Fazenda / Sítio",
    "Barracão": "Galpão",
    "Galpão": "Galpão",
    "Haras": "Haras",
    "Chácara": "Chácara",
    "Kitnet": "Kitnet / Conjugado",
    "Hotel": "Hotel",
    "Pousada": "Pousada",
    "Andar Corporativo": "Imóvel Comercial",
    "Ponto": "Imóvel Comercial",
    "Prédio": "Imóvel Comercial",
    "Resort": "Imóvel Comercial",
    "Studio": "Imóvel Comercial",
    "Ilha": "Imóvel Comercial",
    "Box/Garagem": "Imóvel Comercial",
    "Área": "Área",
    "Conjunto": "Área",
    "Laje": "Área",
    "Loft": "Área",
    "Pavilhão": "Área",
    "Rancho": "Área",
    "Village": "Área",
}


def gaia_vista_type(value: str) -> str:
    v = (value or "").strip()
    return GAIA_VISTA_TYPES.get(v, v)
