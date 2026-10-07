"""Utilitários comuns aos leitores de feed e o formato normalizado de imóvel.

Formato normalizado (o que vai para ``media/importacao/<id>.json``), um dict por imóvel::

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
"""

from __future__ import annotations

import html
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

CHAVES_IMOVEL = (
    "codigo", "destaque", "tipo", "cidade", "bairro", "uf", "quartos", "banheiros", "suites", "vagas",
    "area_util", "area_total", "preco_venda", "preco_locacao", "preco_temporada", "dentro_condominio",
    "infra_imovel", "infra_condominio", "descricao", "fotos", "taxas",
)


class FormatoInvalido(Exception):
    """O conteúdo baixado não é um feed do formato esperado."""


# ------------------------------------------------------------------ XML
def local(tag: str) -> str:
    """Nome da tag sem namespace (``{ns}Listing`` → ``Listing``)."""
    return tag.rsplit("}", 1)[-1]


def parse(conteudo: bytes) -> ET.Element:
    try:
        return ET.fromstring(conteudo)
    except ET.ParseError as exc:
        raise FormatoInvalido(f"XML inválido: {exc}") from exc


def filho(el: ET.Element | None, *caminho: str) -> ET.Element | None:
    """Desce pelos nomes (sem namespace, sensível a maiúsculas); ``None`` se faltar algum."""
    atual = el
    for nome in caminho:
        if atual is None:
            return None
        atual = next((c for c in atual if local(c.tag) == nome), None)
    return atual


def filhos(el: ET.Element | None, nome: str) -> list[ET.Element]:
    return [] if el is None else [c for c in el if local(c.tag) == nome]


def texto(el: ET.Element | None, *caminho: str) -> str:
    alvo = filho(el, *caminho) if caminho else el
    if alvo is None:
        return ""
    return "".join(alvo.itertext()).strip()


# --------------------------------------------------------------- valores
def numero(valor) -> Decimal | None:
    """
    Converte valores dos feeds em Decimal: ``1.500.000``, ``1500.00``, ``1.500,00``, ``R$ 1.500``

    Args:
        valor: texto ou número

    Returns:
        Decimal ou ``None`` quando vazio/zero/inválido
    """
    s = str(valor or "").strip()
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        # O separador que aparece por último é o decimal.
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        partes = s.split(",")
        s = s.replace(",", ".") if len(partes) == 2 and len(partes[1]) <= 2 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        # "1.500.000" ou "150.000": ponto como milhar.
        s = s.replace(".", "")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return d if d > 0 else None


def inteiro(valor) -> int:
    d = numero(valor)
    return int(d) if d is not None else 0


def decimal_str(d: Decimal | None) -> str | None:
    return None if d is None else str(d.quantize(Decimal("0.01")))


def limpar_texto(valor: str) -> str:
    """HTML dos feeds vira texto: entidades resolvidas, tags removidas, quebras de linha mantidas."""
    s = html.unescape(str(valor or ""))
    s = re.sub(r"(?i)<br\s*/?>|</p>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def lista_infra(valor: str) -> list[str]:
    """``"Piscina;Sauna;"`` → ``["Piscina", "Sauna"]`` (sem repetidos, na ordem)."""
    vistos, saida = set(), []
    for parte in str(valor or "").split(";"):
        nome = limpar_texto(parte).strip()
        chave = nome.lower()
        if nome and chave not in vistos:
            vistos.add(chave)
            saida.append(nome)
    return saida


def normalizar_nome(valor: str) -> str:
    """Chave de comparação de nomes: minúsculas, sem acento e sem espaços extras."""
    s = unicodedata.normalize("NFD", str(valor or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def imovel(**campos) -> dict:
    """Monta um imóvel normalizado com todas as chaves (valores ausentes viram o padrão)."""
    base = {
        "codigo": "", "destaque": 0, "tipo": "", "cidade": "", "bairro": "", "uf": "",
        "quartos": 0, "banheiros": 0, "suites": 0, "vagas": 0,
        "area_util": None, "area_total": None,
        "preco_venda": None, "preco_locacao": None, "preco_temporada": None,
        "dentro_condominio": False, "infra_imovel": [], "infra_condominio": [],
        "descricao": "", "fotos": [], "taxas": [],
    }
    base.update(campos)
    base["codigo"] = str(base["codigo"] or "").strip()
    return base


def foto(url: str, capa: bool) -> dict | None:
    url = (url or "").strip().replace("\t", "")
    return {"url": url[:500], "capa": bool(capa)} if len(url) > 10 else None


def taxa(descricao: str, valor, obs: str = "") -> dict | None:
    v = numero(valor)
    return {"descricao": descricao, "valor": decimal_str(v), "obs": (obs or "")[:300]} if v else None


# Tipos de Value Gaia e Vista (tabela PadronizarTipo do legado).
TIPOS_GAIA_VISTA = {
    "Apartamento": "Apartamento", "Apartamento Duplex": "Apartamento", "Apartamento Triplex": "Apartamento",
    "Sobrado": "Apartamento", "Penthouse": "Apartamento",
    "Casa": "Casa", "Bangalô": "Casa", "Edícula": "Casa",
    "Loja": "Loja", "Cobertura": "Cobertura", "": "Terreno Comercial", "Flat": "Flat",
    "Sala": "Sala", "Salão": "Sala", "Terreno": "Terreno Residencial",
    "Fazenda": "Fazenda / Sítio", "Sítio": "Fazenda / Sítio",
    "Barracão": "Galpão", "Galpão": "Galpão", "Haras": "Haras", "Chácara": "Chácara", "Kitnet": "Kitnet / Conjugado",
    "Hotel": "Hotel", "Pousada": "Pousada",
    "Andar Corporativo": "Imóvel Comercial", "Ponto": "Imóvel Comercial", "Prédio": "Imóvel Comercial",
    "Resort": "Imóvel Comercial", "Studio": "Imóvel Comercial", "Ilha": "Imóvel Comercial",
    "Box/Garagem": "Imóvel Comercial",
    "Área": "Área", "Conjunto": "Área", "Laje": "Área", "Loft": "Área", "Pavilhão": "Área",
    "Rancho": "Área", "Village": "Área",
}


def tipo_gaia_vista(valor: str) -> str:
    v = (valor or "").strip()
    return TIPOS_GAIA_VISTA.get(v, v)
