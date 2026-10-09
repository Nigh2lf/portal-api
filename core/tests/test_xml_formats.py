"""Leitores de feed XML (app ``xml_import``): streaming dá o mesmo resultado da árvore inteira."""

from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest

from xml_import import formats
from xml_import.formats import InvalidFormat

PI = b"""<?xml version="1.0" encoding="UTF-8"?>
<Carga>
  <Cabecalho><Versao>1</Versao></Cabecalho>
  <Imoveis>
    <Imovel>
      <CodigoImovel>AP1</CodigoImovel><DestaquePortal>3</DestaquePortal>
      <TipoImovel>Apartamento</TipoImovel><Cidade>Petr\xc3\xb3polis</Cidade><Bairro>Centro</Bairro><UF>RJ</UF>
      <QtdDormitorios>2</QtdDormitorios><QtdBanheiros>1</QtdBanheiros><QtdVagas>1</QtdVagas>
      <AreaUtil>80,5</AreaUtil><PrecoVenda>450.000,00</PrecoVenda>
      <DentroCondominio>1</DentroCondominio>
      <InfraEstruturaImovel>Piscina;Sauna;Piscina</InfraEstruturaImovel>
      <Observacao>Linda &lt;b&gt;vista&lt;/b&gt;</Observacao>
      <Fotos>
        <Foto><URLArquivo>https://x.test/fotos/1.jpg</URLArquivo><Principal>0</Principal></Foto>
        <Foto><URLArquivo>https://x.test/fotos/2.jpg</URLArquivo><Principal>1</Principal></Foto>
      </Fotos>
      <Taxas><Taxa><TaxaDescricao>IPTU</TaxaDescricao><TaxaValor>1.200,00</TaxaValor></Taxa></Taxas>
    </Imovel>
    <Imovel>
      <CodigoImovel>CA2</CodigoImovel><TipoImovel>Casa</TipoImovel><Cidade>Teres\xc3\xb3polis</Cidade><UF>RJ</UF>
      <PrecoLocacao>2500</PrecoLocacao>
    </Imovel>
  </Imoveis>
</Carga>"""

GAIA = b"""<Carga><Imoveis>
  <Imovel><CodigoImovel>G1</CodigoImovel><TipoOferta>2</TipoOferta><TipoImovel>Casa</TipoImovel>
    <Cidade>Petropolis</Cidade><Estado>RJ</Estado><PrecoVenda>300000</PrecoVenda>
    <CondominioFechado>1</CondominioFechado><Piscina>1</Piscina><PrecoIptu>800</PrecoIptu>
    <Fotos><Foto><UrlArquivo>https://x.test/g/1.jpg</UrlArquivo><Principal>1</Principal></Foto></Fotos>
  </Imovel>
</Imoveis></Carga>"""

UNION = b"""<Carga><Imoveis>
  <Imovel><Referencia>U1</Referencia><Destaque>1</Destaque><Tipo>Apartamento</Tipo>
    <Cidade>Petropolis</Cidade><UnidadeFederativa>RJ</UnidadeFederativa>
    <Venda>1</Venda><Valorvenda>500000</Valorvenda><Locacao>0</Locacao><Valorlocacao>2000</Valorlocacao>
    <Dormitorios>3</Dormitorios><Piscina>1</Piscina><Condominio>1</Condominio>
    <Fotos><Foto><URL>https://x.test/u/1.jpg</URL><Principal>1</Principal></Foto></Fotos>
  </Imovel>
</Imoveis></Carga>"""

VIVA = b"""<ListingDataFeed xmlns="http://www.vivareal.com/schemas/1.0/VRSync">
  <Header><Provider>x</Provider></Header>
  <Listings>
    <Listing>
      <ListingID>V1</ListingID><TransactionType>Sale/Rent</TransactionType>
      <PublicationType>PREMIUM</PublicationType>
      <Media><Item medium="image">https://x.test/v/1.jpg</Item><Item medium="video">https://youtu.be/abc</Item></Media>
      <Details>
        <PropertyType>Residential / Condo</PropertyType><Description>Casa &amp; lazer</Description>
        <ListPrice>700000</ListPrice><RentalPrice period="Monthly">3000</RentalPrice>
        <Bedrooms>3</Bedrooms><Bathrooms>2</Bathrooms><Garage>2</Garage><LivingArea>120</LivingArea>
        <Features><Feature>Pool</Feature><Feature>BBQ</Feature></Features>
        <YearlyTax>1500</YearlyTax>
      </Details>
      <Location><City>Petropolis</City><Neighborhood>Itaipava</Neighborhood><State abbreviation="RJ">Rio de Janeiro</State></Location>
    </Listing>
  </Listings>
</ListingDataFeed>"""

VISTA = b"""<Imoveis>
  <Imovel><CodigoImovel>VS1</CodigoImovel><Destaque>Sim</Destaque><TipoImovel>Casa</TipoImovel>
    <Cidade>Petropolis</Cidade><UF>RJ</UF><PrecoVenda>900000</PrecoVenda><PrecoCondominio>500</PrecoCondominio>
    <Piscina>Sim</Piscina><Descricao>Ampla</Descricao>
    <Fotos><Foto><URL>https://x.test/vs/1.jpg</URL></Foto><Foto><URL>https://x.test/vs/2.jpg</URL></Foto></Fotos>
  </Imovel>
  <Imovel><CodigoImovel>VS2</CodigoImovel><TipoImovel>Apartamento</TipoImovel><Cidade>Petropolis</Cidade><UF>RJ</UF>
    <PrecoLocacao>1800</PrecoLocacao>
  </Imovel>
</Imoveis>"""

FEEDS = {"pi": PI, "value_gaia": GAIA, "union": UNION, "viva_real": VIVA, "vista": VISTA}


@pytest.mark.parametrize("fmt", sorted(FEEDS))
def test_streaming_matches_tree_reader(fmt):
    content = FEEDS[fmt]
    used, streamed = formats.read(content, fmt)
    assert used == fmt
    assert streamed == formats.READERS[fmt](ET.fromstring(content))
    assert streamed, "o feed de exemplo tem imóveis"
    assert all(set(p) == set(formats.base.PROPERTY_KEYS) for p in streamed)


def test_pi_values():
    _, items = formats.read(PI, "pi")
    first, second = items
    assert first["codigo"] == "AP1"
    assert first["destaque"] == 2  # limitado a 2
    assert first["cidade"] == "Petrópolis"
    assert first["area_util"] == "80.50"
    assert first["preco_venda"] == "450000.00"
    assert first["dentro_condominio"] is True
    assert first["infra_imovel"] == ["Piscina", "Sauna"]
    assert first["descricao"] == "Linda vista"
    assert first["fotos"] == [
        {"url": "https://x.test/fotos/1.jpg", "capa": False},
        {"url": "https://x.test/fotos/2.jpg", "capa": True},
    ]
    assert first["taxas"] == [{"descricao": "IPTU", "valor": "1200.00", "obs": ""}]
    assert second["codigo"] == "CA2"
    assert second["preco_locacao"] == "2500.00"
    assert second["preco_venda"] is None


def test_viva_real_values():
    _, items = formats.read(VIVA, "viva_real")
    (item,) = items
    assert item["codigo"] == "V1"
    assert item["destaque"] == 1
    assert item["tipo"] == "Casa"
    assert item["uf"] == "RJ"
    assert item["preco_venda"] == "700000.00"
    assert item["preco_locacao"] == "3000.00"
    assert item["dentro_condominio"] is True
    assert item["fotos"] == [{"url": "https://x.test/v/1.jpg", "capa": True}]
    assert item["infra_imovel"] == ["Piscina", "Churrasqueira"]


def test_structure_wins_over_registered_format():
    # Cadastro diz Viva Real, arquivo é Union: vale o arquivo.
    assert formats.read(UNION, "viva_real")[0] == "union"
    # PI e Value Gaia têm a mesma estrutura: vale o cadastro.
    assert formats.read(PI, "value_gaia")[0] == "value_gaia"
    assert formats.read(GAIA, "pi")[0] == "pi"


def test_empty_listings_is_recognized_without_items():
    fmt, items = formats.read(b"<ListingDataFeed><Listings/></ListingDataFeed>", "viva_real")
    assert (fmt, items) == ("viva_real", [])


def test_unknown_structure_and_invalid_xml():
    with pytest.raises(InvalidFormat, match="Estrutura não reconhecida"):
        formats.read(b"<Carga><Imoveis/></Carga>", "pi")
    with pytest.raises(InvalidFormat, match="XML inválido"):
        formats.read(b"<Carga><Imoveis><Imovel>", "pi")


def test_read_file_streams_from_disk(tmp_path):
    path = tmp_path / "feed.xml"
    path.write_bytes(VISTA)
    fmt, items = formats.read_file(path, "vista")
    assert fmt == "vista"
    assert [i["codigo"] for i in items] == ["VS1", "VS2"]
    assert items[0]["fotos"][0]["capa"] is True
    assert items[0]["taxas"] == [{"descricao": "Condomínio", "valor": "500.00", "obs": ""}]
