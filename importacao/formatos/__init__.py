"""Escolha do leitor de feed: pelo integrador do anunciante, conferido pela estrutura do arquivo."""

from __future__ import annotations

from .base import FormatoInvalido, filho, filhos, local, parse
from .leitores import ler_pi, ler_union, ler_value_gaia, ler_viva_real, ler_vista

LEITORES = {
    "pi": ler_pi,
    "value_gaia": ler_value_gaia,
    "viva_real": ler_viva_real,
    "union": ler_union,
    "vista": ler_vista,
}

# legacy_id de core_integrator (Id_Integrador do legado) → formato.
POR_INTEGRADOR = {1: "pi", 2: "value_gaia", 3: "viva_real", 4: "union", 5: "vista"}
POR_NOME = (("gaia", "value_gaia"), ("viva", "viva_real"), ("union", "union"), ("vista", "vista"))


def formato_do_integrador(integrador) -> str:
    """Formato esperado para o integrador (``pi`` quando não há integrador ou ele é o próprio portal)."""
    if integrador is None:
        return "pi"
    if integrador.legacy_id in POR_INTEGRADOR:
        return POR_INTEGRADOR[integrador.legacy_id]
    nome = f"{integrador.slug} {integrador.name}".lower()
    return next((fmt for chave, fmt in POR_NOME if chave in nome), "pi")


def detectar(raiz) -> str | None:
    """Formato pela estrutura do XML; ``None`` se não reconhecer."""
    if filho(raiz, "Listings") is not None:
        return "viva_real"
    if filhos(raiz, "Imovel"):
        return "vista"
    itens = filhos(filho(raiz, "Imoveis"), "Imovel")
    if not itens:
        return None
    nomes = {local(c.tag) for c in itens[0]}
    if "Referencia" in nomes:
        return "union"
    if "TipoOferta" in nomes or "CondominioFechado" in nomes or "PrecoIptu" in nomes:
        return "value_gaia"
    return "pi"


def ler(conteudo: bytes, esperado: str) -> tuple[str, list[dict]]:
    """
    Converte o feed bruto em imóveis normalizados

    Args:
        conteudo: bytes baixados
        esperado: formato do integrador cadastrado

    Returns:
        (formato usado, lista de imóveis)
    """
    raiz = parse(conteudo)
    detectado = detectar(raiz)
    if detectado is None:
        raise FormatoInvalido(f"Estrutura não reconhecida (raiz <{local(raiz.tag)}>).")
    # A estrutura do arquivo prevalece sobre o cadastro (integrador errado não zera o cliente),
    # exceto entre PI e Value Gaia, que têm a mesma estrutura: aí vale o cadastro.
    mesma_estrutura = {"pi", "value_gaia"}
    formato = esperado if detectado == esperado or {detectado, esperado} <= mesma_estrutura else detectado
    return formato, LEITORES[formato](raiz)


__all__ = ["LEITORES", "FormatoInvalido", "detectar", "formato_do_integrador", "ler"]
