"""Escolha do leitor de feed: pelo integrador do anunciante, conferido pela estrutura do arquivo."""

from __future__ import annotations

from .base import InvalidFormat, child, children, local_name, parse
from .readers import read_pi, read_union, read_value_gaia, read_vista, read_viva_real

READERS = {
    "pi": read_pi,
    "value_gaia": read_value_gaia,
    "viva_real": read_viva_real,
    "union": read_union,
    "vista": read_vista,
}

# legacy_id de core_integrator (Id_Integrador do legado) → formato.
BY_INTEGRATOR = {1: "pi", 2: "value_gaia", 3: "viva_real", 4: "union", 5: "vista"}
BY_NAME = (("gaia", "value_gaia"), ("viva", "viva_real"), ("union", "union"), ("vista", "vista"))


def format_for_integrator(integrator) -> str:
    """Formato esperado para o integrador (``pi`` quando não há integrador ou ele é o próprio portal)."""
    if integrator is None:
        return "pi"
    if integrator.legacy_id in BY_INTEGRATOR:
        return BY_INTEGRATOR[integrator.legacy_id]
    name = f"{integrator.slug} {integrator.name}".lower()
    return next((fmt for key, fmt in BY_NAME if key in name), "pi")


def detect(root) -> str | None:
    """Formato pela estrutura do XML; ``None`` se não reconhecer."""
    if child(root, "Listings") is not None:
        return "viva_real"
    if children(root, "Imovel"):
        return "vista"
    items = children(child(root, "Imoveis"), "Imovel")
    if not items:
        return None
    names = {local_name(c.tag) for c in items[0]}
    if "Referencia" in names:
        return "union"
    if "TipoOferta" in names or "CondominioFechado" in names or "PrecoIptu" in names:
        return "value_gaia"
    return "pi"


def read(content: bytes, expected: str) -> tuple[str, list[dict]]:
    """
    Converte o feed bruto em imóveis normalizados

    Args:
        content: bytes baixados
        expected: formato do integrador cadastrado

    Returns:
        (formato usado, lista de imóveis)
    """
    root = parse(content)
    detected = detect(root)
    if detected is None:
        raise InvalidFormat(f"Estrutura não reconhecida (raiz <{local_name(root.tag)}>).")
    # A estrutura do arquivo prevalece sobre o cadastro (integrador errado não zera o cliente),
    # exceto entre PI e Value Gaia, que têm a mesma estrutura: aí vale o cadastro.
    same_structure = {"pi", "value_gaia"}
    fmt = expected if detected == expected or {detected, expected} <= same_structure else detected
    return fmt, READERS[fmt](root)


__all__ = ["READERS", "InvalidFormat", "detect", "format_for_integrator", "read"]
