"""Escolha do leitor de feed: pelo integrador do anunciante, conferido pela estrutura do arquivo.

O feed é lido em streaming (``iterparse``): cada imóvel vira um dict assim que a tag dele fecha
e o elemento é descartado da árvore. Assim a memória fica proporcional ao tamanho de um imóvel,
não do arquivo inteiro (uma árvore ``ElementTree`` ocupa de 5 a 10 vezes o tamanho do XML).
"""

from __future__ import annotations

import io
from xml.etree import ElementTree as ET

from .base import InvalidFormat, child, children, local_name, parse
from .readers import (
    pi_item,
    read_pi,
    read_union,
    read_value_gaia,
    read_vista,
    read_viva_real,
    union_item,
    value_gaia_item,
    vista_item,
    viva_real_item,
)

# Leitores sobre a árvore inteira (``read_X(root)``): úteis em testes e feeds pequenos.
READERS = {
    "pi": read_pi,
    "value_gaia": read_value_gaia,
    "viva_real": read_viva_real,
    "union": read_union,
    "vista": read_vista,
}
# Leitores de um imóvel (``X_item(element)``): usados pelo streaming.
ITEM_READERS = {
    "pi": pi_item,
    "value_gaia": value_gaia_item,
    "viva_real": viva_real_item,
    "union": union_item,
    "vista": vista_item,
}

# legacy_id de core_integrator (Id_Integrador do legado) → formato.
BY_INTEGRATOR = {1: "pi", 2: "value_gaia", 3: "viva_real", 4: "union", 5: "vista"}
BY_NAME = (("gaia", "value_gaia"), ("viva", "viva_real"), ("union", "union"), ("vista", "vista"))
# PI e Value Gaia têm a mesma estrutura: entre eles vale o cadastro do integrador.
SAME_STRUCTURE = {"pi", "value_gaia"}


def format_for_integrator(integrator) -> str:
    """Formato esperado para o integrador (``pi`` quando não há integrador ou ele é o próprio portal)."""
    if integrator is None:
        return "pi"
    if integrator.legacy_id in BY_INTEGRATOR:
        return BY_INTEGRATOR[integrator.legacy_id]
    name = f"{integrator.slug} {integrator.name}".lower()
    return next((fmt for key, fmt in BY_NAME if key in name), "pi")


def _imoveis_item_format(item) -> str:
    """PI, Value Gaia ou Union a partir das tags de um ``<Imoveis><Imovel>``."""
    names = {local_name(c.tag) for c in item}
    if "Referencia" in names:
        return "union"
    if "TipoOferta" in names or "CondominioFechado" in names or "PrecoIptu" in names:
        return "value_gaia"
    return "pi"


def detect(root) -> str | None:
    """Formato pela estrutura do XML; ``None`` se não reconhecer."""
    if child(root, "Listings") is not None:
        return "viva_real"
    if children(root, "Imovel"):
        return "vista"
    items = children(child(root, "Imoveis"), "Imovel")
    if not items:
        return None
    return _imoveis_item_format(items[0])


def _detect_item(ancestors: list[str], name: str, item) -> str | None:
    """Formato pelo caminho do primeiro imóvel (``ancestors`` começa na raiz); ``None`` se não for um imóvel."""
    depth = len(ancestors)
    if depth == 1 and name == "Imovel":
        return "vista"
    if depth == 2 and name == "Listing" and ancestors[1] == "Listings":
        return "viva_real"
    if depth == 2 and name == "Imovel" and ancestors[1] == "Imoveis":
        return _imoveis_item_format(item)
    return None


def _choose(detected: str, expected: str) -> str:
    # A estrutura do arquivo prevalece sobre o cadastro (integrador errado não zera o cliente),
    # exceto entre PI e Value Gaia, que têm a mesma estrutura: aí vale o cadastro.
    if detected == expected or {detected, expected} <= SAME_STRUCTURE:
        return expected
    return detected


def read_stream(source, expected: str) -> tuple[str, list[dict]]:
    """
    Converte o feed em imóveis normalizados lendo o XML em streaming

    Args:
        source: arquivo aberto em modo binário (ou caminho)
        expected: formato do integrador cadastrado

    Returns:
        (formato usado, lista de imóveis)

    Raises:
        InvalidFormat: XML inválido ou estrutura não reconhecida
    """
    ancestors: list[str] = []  # nomes (sem namespace) dos elementos abertos, da raiz para baixo
    open_elements: list[ET.Element] = []
    root = None
    fmt = item_reader = item_path = None
    properties: list[dict] = []
    try:
        for event, elem in ET.iterparse(source, events=("start", "end")):  # noqa: S314 - feeds cadastrados pelo admin
            if event == "start":
                if root is None:
                    root = elem
                ancestors.append(local_name(elem.tag))
                open_elements.append(elem)
                continue
            name = ancestors.pop()
            open_elements.pop()
            if not ancestors:
                continue  # fechou a raiz
            if item_path is None:
                detected = _detect_item(ancestors, name, elem)
                if detected is None:
                    continue
                fmt = _choose(detected, expected)
                item_reader = ITEM_READERS[fmt]
                item_path = (len(ancestors), ancestors[-1], name)
            if (len(ancestors), ancestors[-1], name) == item_path:
                properties.append(item_reader(elem))
                # Solta o imóvel da árvore: o pai não guarda referência e a memória é liberada.
                open_elements[-1].remove(elem)
    except ET.ParseError as exc:
        raise InvalidFormat(f"XML inválido: {exc}") from exc
    if item_path is not None:
        return fmt, properties
    # Nenhum imóvel: a estrutura que sobrou na árvore (pequena) decide, como antes.
    detected = detect(root) if root is not None else None
    if detected is None:
        root_name = local_name(root.tag) if root is not None else "(vazio)"
        raise InvalidFormat(f"Estrutura não reconhecida (raiz <{root_name}>).")
    return _choose(detected, expected), []


def read_file(path, expected: str) -> tuple[str, list[dict]]:
    """``read_stream`` sobre um arquivo no disco (o feed baixado)."""
    with open(path, "rb") as fh:
        return read_stream(fh, expected)


def read(content: bytes, expected: str) -> tuple[str, list[dict]]:
    """
    Converte o feed bruto em imóveis normalizados

    Args:
        content: bytes baixados
        expected: formato do integrador cadastrado

    Returns:
        (formato usado, lista de imóveis)
    """
    return read_stream(io.BytesIO(content), expected)


__all__ = [
    "ITEM_READERS",
    "READERS",
    "InvalidFormat",
    "detect",
    "format_for_integrator",
    "parse",
    "read",
    "read_file",
    "read_stream",
]
