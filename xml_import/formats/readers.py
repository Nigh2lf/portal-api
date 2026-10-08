"""Leitores de cada formato de feed → lista de imóveis no formato normalizado (ver ``base``).

Portados dos conversores do legado (``xml/Padroes/*-PI.php``), com os bugs documentados
corrigidos: feed ou foto únicos não se perdem, "Sale/Rent" guarda venda e aluguel,
flags repetidas não duplicam características.
"""

from __future__ import annotations

from .base import (
    child,
    children,
    clean_text,
    decimal_str,
    feature_list,
    fee,
    gaia_vista_type,
    integer,
    number,
    photo,
    property_record,
    text,
)


def _photos(items):
    return [p for p in items if p]


def _fees(items):
    return [f for f in items if f]


# ------------------------------------------------------------ PI (nativo)
def read_pi(root):
    """Formato do próprio portal (TrustImóvel / ``<Carga><Imoveis><Imovel>``)."""
    items = children(child(root, "Imoveis"), "Imovel")
    out = []
    for item in items:
        photos = _photos(
            photo(text(p, "URLArquivo"), text(p, "Principal") == "1")
            for p in children(child(item, "Fotos"), "Foto")
        )
        fees = _fees(
            fee(
                text(t, "TaxaDescricao"),
                text(t, "TaxaValor"),
                text(t, "TaxaOBS") or text(t, "TaxaObs"),
            )
            for t in children(child(item, "Taxas"), "Taxa")
        )
        out.append(
            property_record(
                codigo=text(item, "CodigoImovel"),
                destaque=min(2, integer(text(item, "DestaquePortal"))),
                tipo=text(item, "TipoImovel"),
                cidade=text(item, "Cidade"),
                bairro=text(item, "Bairro"),
                uf=text(item, "UF"),
                quartos=integer(text(item, "QtdDormitorios")),
                banheiros=integer(text(item, "QtdBanheiros")),
                suites=integer(text(item, "QtdSuites")),
                vagas=integer(text(item, "QtdVagas")),
                area_util=decimal_str(number(text(item, "AreaUtil"))),
                area_total=decimal_str(number(text(item, "AreaTotal"))),
                preco_venda=decimal_str(number(text(item, "PrecoVenda"))),
                preco_locacao=decimal_str(number(text(item, "PrecoLocacao"))),
                preco_temporada=decimal_str(number(text(item, "PrecoLocacaoTemporada"))),
                dentro_condominio=text(item, "DentroCondominio") == "1",
                infra_imovel=feature_list(text(item, "InfraEstruturaImovel")),
                infra_condominio=feature_list(text(item, "InfraEstruturaCondominio")),
                descricao=clean_text(text(item, "Observacao")),
                fotos=photos,
                taxas=fees,
            )
        )
    return out


# ------------------------------------------------------------ Value Gaia
GAIA_FLAGS = [
    ("PortaoEletronico", "Portão Eletrônico"),
    ("FrenteMar", "Frente para o Mar"),
    ("BeiraMar", "Beira do Mar"),
    ("PeDireitoDuplo", "Pé Direito Duplo"),
    ("Deposito", "Depósito"),
    ("Mezanino", "Mezanino"),
    ("Terraco", "Terraço"),
    ("JardimInverno", "Jardim de Inverno"),
    ("ServicoCozinha", "Serviço de Cozinha"),
    ("DormitorioEmpregada", "Dormitório de Empregada"),
    ("Zelador", "Zelador"),
    ("Adega", "Adega"),
    ("Solarium", "Solarium"),
    ("Sacada", "Sacada"),
    ("Lavabo", "Lavabo"),
    ("DormitorioReversivel", "Dormitório Reversível"),
    ("ArmarioCorredor", "Armário no Corredor"),
    ("ArmarioCloset", "Closet"),
    ("ArmarioDormitorio", "Armário no Dormitório"),
    ("ArmarioBanheiro", "Armário no Banheiro"),
    ("ArmarioSala", "Armário na Sala"),
    ("ArmarioEscritorio", "Armário no Escritório"),
    ("ArmarioHomeTheater", "Armário no Home Theater"),
    ("ArmarioDormitorioEmpregada", "Armário no Dormitório de Empregada"),
    ("ArmarioAreaServico", "Armário na Área de Serviço"),
    ("PisoAquecido", "Piso Aquecido"),
    ("Agua", "Água"),
    ("ArCondicionado", "Ar Condicionado"),
    ("ArmarioCozinha", "Armário de Cozinha"),
    ("Churrasqueira", "Churrasqueira"),
    ("Copa", "Copa"),
    ("EntradaCaminhoes", "Entrada para Caminhões"),
    ("Escritorio", "Escritório"),
    ("Esgoto", "Esgoto"),
    ("Piscina", "Piscina"),
    ("QuadraPoliEsportiva", "Quadra Poliesportiva"),
    ("Quintal", "Quintal"),
    ("Sauna", "Sauna"),
    ("Varanda", "Varanda"),
    ("Vestiario", "Vestiário"),
    ("WCEmpregada", "Banheiro de Empregada"),
    ("Hidromassagem", "Hidromassagem"),
    ("AreaServico", "Área de Serviço"),
    ("CampoFutebol", "Campo de Futebol"),
    ("Caseiro", "Caseiro"),
    ("Despensa", "Despensa"),
    ("Doca", "Doca"),
    ("Mobiliado", "Mobiliado"),
    ("Lareira", "Lareira"),
    ("Interfone", "Interfone"),
]


def read_value_gaia(root):
    out = []
    for item in children(child(root, "Imoveis"), "Imovel"):
        photos = []
        for p in children(child(item, "Fotos"), "Foto"):
            url = text(p, "URLArquivo") or text(p, "UrlArquivo")
            photos.append(photo(url, text(p, "Principal") == "1"))
        out.append(
            property_record(
                codigo=text(item, "CodigoImovel"),
                destaque=1 if text(item, "TipoOferta") in ("2", "3") else 0,
                tipo=gaia_vista_type(text(item, "TipoImovel")),
                cidade=text(item, "Cidade"),
                bairro=text(item, "Bairro"),
                uf=text(item, "Estado"),
                quartos=integer(text(item, "QtdDormitorios")),
                banheiros=integer(text(item, "QtdBanheiros")),
                suites=integer(text(item, "QtdSuites")),
                vagas=integer(text(item, "QtdVagas")),
                area_util=decimal_str(number(text(item, "AreaUtil"))),
                area_total=decimal_str(number(text(item, "AreaTotal"))),
                preco_venda=decimal_str(number(text(item, "PrecoVenda"))),
                preco_locacao=decimal_str(number(text(item, "PrecoLocacao"))),
                preco_temporada=decimal_str(number(text(item, "PrecoLocacaoTemporada"))),
                dentro_condominio=child(item, "CondominioFechado") is not None
                and text(item, "CondominioFechado") not in ("0", "false", "False"),
                infra_imovel=[name for tag, name in GAIA_FLAGS if text(item, tag) == "1"],
                descricao=clean_text(text(item, "Observacao")),
                fotos=_photos(photos),
                taxas=_fees(
                    [
                        fee("IPTU", text(item, "PrecoIptu")),
                        fee("Condomínio", text(item, "PrecoCondominio")),
                    ]
                ),
            )
        )
    return out


# --------------------------------------------------------------- Viva Real
VIVA_REAL_TYPES = {
    "residential/apartment": "Apartamento",
    "residential/home": "Casa",
    "residential/farmranch": "Chácara",
    "residential/farm/ranch": "Chácara",
    "residential/condo": "Casa",
    "residential/flat": "Flat",
    "residential/landlot": "Terreno Residencial",
    "residential/land/lot": "Terreno Residencial",
    "residential/sobrado": "Casa",
    "residential/penthouse": "Cobertura",
    "residential/kitnet": "Kitnet / Conjugado",
    "residential/agricultural": "Fazenda / Sítio",
    "commercial/hotel": "Hotel",
    "commercial/residentialincome": "Imóvel Comercial",
    "commercial/consultorio": "Consultório",
    "commercial/office": "Sala",
    "commercial/agricultural": "Sítio",
    "commercial/industrial": "Galpão",
    "commercial/building": "Imóvel Comercial",
    "commercial/loja": "Loja",
    "commercial/landlot": "Terreno Comercial",
    "commercial/land/lot": "Terreno Comercial",
    "commercial/business": "Imóvel Comercial",
    "commercial/retail": "Imóvel Comercial",
}

VIVA_REAL_FEATURES = {
    "Gym": "Academia",
    "Heating": "Aquecimento",
    "Air Conditioning": "Ar condicionado",
    "Maid's Quarters": "Área de serviço",
    "BBQ": "Churrasqueira",
    "Movie Theater": "Cinema",
    "TV Security": "Circuito de segurança",
    "Internet Connection": "Conexão à internet",
    "Gated Community": "Conjunto fechado",
    "Kitchen": "Cozinha",
    "Warehouse": "Depósito",
    "Elevator": "Elevador",
    "Gourmet Area": "Espaço Gourmet",
    "Juvenile Area": "Espaço Juvenil",
    "Green space / Park": "Espaço verde / Parque",
    "Reflective Pool": "Espelhos D'água",
    "Generator": "Gerador elétrico",
    "Lawn": "Grama",
    "Media Room": "Home cinema",
    "Home Office": "Home Office",
    "Intercom": "Interfone",
    "Garden": "Jardim",
    "Cybercafe": "Lan house",
    "Fireplace": "Lareira",
    "Laundry": "Lavanderia",
    "Massage Room": "Sala de Massagem",
    "Furnished": "Mobiliado",
    "Close to schools": "Perto de escola",
    "Close to shopping centers": "Perto de Shopping Center",
    "Close to main roads/avenues": "Perto de vias de acesso",
    "Pool": "Piscina",
    "Swimming Pool": "Piscina Adulto",
    "Wading Pool": "Piscina Infantil",
    "Jogging track": "Pista de caminhada",
    "Playground": "Playground",
    "Fully Wired": "Cabeamento completo",
    "Close to hospitals": "Próximo a hospitais",
    "Tennis court": "Quadra de tênis",
    "Sports Court": "Quadra poliesportiva",
    "Backyard": "Quintal",
    "Reception room": "Recepção",
    "Balcony/Terrace": "Sacada",
    "Party Room": "Salão de Festas",
    "Game room": "Salão de Jogos Adulto",
    "Game room for kids": "Salão de Jogos para Crianças",
    "Sauna": "Sauna",
    "24 Hour Security": "Segurança 24 horas",
    "Cleaning Services": "Serviços de Limpeza",
    "Alarm System": "Sistema de alarme",
    "Spa": "Spa",
    "Squash": "Squash",
    "Cable Television": "TV a cabo",
    "Veranda": "Varanda Gourmet",
    "Doorman": "Portaria",
    "Exterior View": "Vista exterior",
    "Mountain View": "Vista para a montanha",
    "Lake View": "Vista para lago",
    "Ocean View": "Vista para o mar",
    "Parking Garage": "Garagem",
}


def read_viva_real(root):
    out = []
    for item in children(child(root, "Listings"), "Listing"):
        details = child(item, "Details")
        raw_type = text(details, "PropertyType")
        transaction = text(item, "TransactionType")
        for_sale = transaction in ("For Sale", "Sale/Rent")
        for_rent = transaction in ("For Rent", "Sale/Rent")
        rent_elements = children(details, "RentalPrice")
        photos = []
        for i, media in enumerate(
            x
            for x in children(child(item, "Media"), "Item")
            if "youtu" not in text(x) and x.get("medium") != "video"
        ):
            photos.append(photo(text(media), i == 0))
        location = child(item, "Location")
        state_code = ""
        state = child(location, "State")
        if state is not None:
            state_code = state.get("abbreviation") or text(state)
        out.append(
            property_record(
                codigo=text(item, "ListingID"),
                destaque=1
                if text(item, "PublicationType").upper() in ("PREMIUM", "SUPER_PREMIUM")
                or text(item, "Featured") == "true"
                else 0,
                tipo=VIVA_REAL_TYPES.get(raw_type.lower().replace(" ", ""), raw_type),
                cidade=text(location, "City"),
                bairro=text(location, "Neighborhood"),
                uf=state_code,
                quartos=integer(text(details, "Bedrooms")),
                banheiros=integer(text(details, "Bathrooms")),
                suites=integer(text(details, "Suites")),
                vagas=integer(text(details, "Garage")),
                area_util=decimal_str(number(text(details, "LivingArea"))),
                area_total=decimal_str(number(text(details, "LotArea"))),
                preco_venda=decimal_str(number(text(details, "ListPrice"))) if for_sale else None,
                preco_locacao=decimal_str(number(text(rent_elements[0])))
                if for_rent and rent_elements
                else None,
                dentro_condominio=raw_type.strip() == "Residential / Condo",
                infra_imovel=feature_list(
                    ";".join(
                        VIVA_REAL_FEATURES.get(text(f), text(f))
                        for f in children(child(details, "Features"), "Feature")
                    )
                ),
                descricao=clean_text(text(details, "Description")),
                fotos=_photos(photos),
                taxas=_fees(
                    [
                        fee("Condomínio", text(details, "PropertyAdministrationFee")),
                        fee("IPTU", text(details, "YearlyTax")),
                    ]
                ),
            )
        )
    return out


# ------------------------------------------------------------------ Union
UNION_FLAGS = {
    "Aquecedorcentral": "Aquecedor Central",
    "Aquecedorsolar": "Aquecedor Solar",
    "Arcondicionado": "Ar Condicionado",
    "Arealazer": "Área de Lazer",
    "Armariosala": "Armário na Sala",
    "Armariobanheiro": "Armário no Banheiro",
    "Armariocloset": "Closet",
    "Armariocozinha": "Armário de Cozinha",
    "Armariodormitorio": "Armário no Dormitório",
    "Assoalho": "Assoalho",
    "Banheiroauxiliar": "Banheiro Auxiliar",
    "Banheiroempregada": "Banheiro de Empregada",
    "Bar": "Bar",
    "Brinquedoteca": "Brinquedoteca",
    "Cachoeira": "Cachoeira",
    "Campofutebol": "Campo de Futebol",
    "Casacaseiro": "Casa de Caseiro",
    "Celeiro": "Celeiro",
    "Churrasqueira": "Churrasqueira",
    "CircuitoTV": "Circuito de TV",
    "Contrapiso": "Contrapiso",
    "Copa": "Copa",
    "Curral": "Curral",
    "Deck": "Deck",
    "Despensa": "Despensa",
    "Dormitoriosempregada": "Dormitório de Empregada",
    "Elevadorcarga": "Elevador de Carga",
    "Escritorio": "Escritório",
    "Forno": "Forno",
    "Garagembarco": "Garagem de Barco",
    "Gerador": "Gerador",
    "Hall": "Hall",
    "Hidro": "Hidromassagem",
    "Jardim": "Jardim",
    "Lareira": "Lareira",
    "Lavanderia": "Lavanderia",
    "Mobiliado": "Mobiliado",
    "Piscinaaquecida": "Piscina Aquecida",
    "Piscina": "Piscina",
    "Playground": "Playground",
    "Quadrapoliesportiva": "Quadra Poliesportiva",
    "Quadrasquash": "Quadra de Squash",
    "Quintal": "Quintal",
    "SalaTV": "Sala de TV",
    "Sauna": "Sauna",
    "TVCabo": "TV a Cabo",
}


def _union_price(item, flag, field):
    return decimal_str(number(text(item, field))) if text(item, flag) == "1" else None


def read_union(root):
    out = []
    for item in children(child(root, "Imoveis"), "Imovel"):
        photos = [
            photo(text(p, "URL"), text(p, "Principal") == "1")
            for p in children(child(item, "Fotos"), "Foto")
        ]
        out.append(
            property_record(
                codigo=text(item, "Referencia"),
                destaque=1 if text(item, "Destaque") == "1" else 0,
                tipo=clean_text(text(item, "Tipo")),
                cidade=text(item, "Cidade"),
                bairro=text(item, "Bairro"),
                uf=text(item, "UnidadeFederativa"),
                quartos=integer(text(item, "Dormitorios")),
                banheiros=integer(text(item, "Banheiro2")),
                suites=integer(text(item, "Suite")),
                vagas=integer(text(item, "Garagem")),
                area_util=decimal_str(
                    number(text(item, "Areacosntruida") or text(item, "Areaconstruida"))
                ),
                area_total=decimal_str(number(text(item, "Areaterreno"))),
                preco_venda=_union_price(item, "Venda", "Valorvenda"),
                preco_locacao=_union_price(item, "Locacao", "Valorlocacao"),
                preco_temporada=_union_price(item, "Temporada", "Valortemporada"),
                dentro_condominio=text(item, "Condominio") == "1",
                infra_imovel=[name for tag, name in UNION_FLAGS.items() if text(item, tag) == "1"],
                descricao=clean_text(text(item, "Anuncioparainternet")),
                fotos=_photos(photos),
                taxas=_fees(
                    [
                        fee("Condomínio", text(item, "Valorcondominio")),
                        fee("IPTU", text(item, "Valoriptu")),
                    ]
                ),
            )
        )
    return out


# ------------------------------------------------------------------ Vista
VISTA_FLAGS = [
    ("ArCondicionado", "Ar Condicionado"),
    ("AreaServico", "Área de Serviço"),
    ("ArmarioEmbutido", "Armário Embutido"),
    ("Churrasqueira", "Churrasqueira"),
    ("Closet", "Closet"),
    ("Copa", "Copa"),
    ("Despensa", "Despensa"),
    ("FrenteMar", "De Frente para o Mar"),
    ("Guarita", "Guarita"),
    ("Heliponto", "Heliponto"),
    ("Hidromassagem", "Hidromassagem"),
    ("HomeTheater", "Home Theater"),
    ("InfraInternet", "Internet"),
    ("Interfone", "Interfone"),
    ("Jardim", "Jardim"),
    ("Lancamento", "Lançamento"),
    ("Lareira", "Lareira"),
    ("Mezanino", "Mezanino"),
    ("Mobiliado", "Mobiliado"),
    ("Piscina", "Piscina"),
    ("Playground", "Playground"),
    ("QuadraPoliEsportiva", "Quadra Poliesportiva"),
    ("QuadraTenis", "Quadra de Tênis"),
    ("Quintal", "Quintal"),
    ("SalaGinastica", "Sala de Ginástica"),
    ("SalaJantar", "Sala de Jantar"),
    ("SalaoFestas", "Salão de Festas"),
    ("SalaoJogos", "Salão de Jogos"),
    ("Sauna", "Sauna"),
    ("Telefone", "Telefone"),
    ("Terraco", "Terraço"),
    ("TVCabo", "TV a Cabo"),
    ("Varanda", "Varanda"),
    ("WCEmpregada", "Banheiro de Empregada"),
]


def read_vista(root):
    out = []
    for item in children(root, "Imovel"):
        photos = [
            photo(text(p, "URL"), i == 0)
            for i, p in enumerate(children(child(item, "Fotos"), "Foto"))
        ]
        featured = text(item, "Destaque")
        out.append(
            property_record(
                codigo=text(item, "CodigoImovel"),
                destaque=1 if featured and featured != "Nao" else 0,
                tipo=gaia_vista_type(text(item, "TipoImovel")),
                cidade=text(item, "Cidade"),
                bairro=text(item, "Bairro"),
                uf=text(item, "UF"),
                quartos=integer(text(item, "QtdDormitorios")),
                banheiros=integer(text(item, "QtdBanheiros")),
                suites=integer(text(item, "QtdSuites")),
                vagas=integer(text(item, "QtdVagas")),
                area_util=decimal_str(number(text(item, "AreaUtil"))),
                area_total=decimal_str(number(text(item, "AreaTotal"))),
                preco_venda=decimal_str(number(text(item, "PrecoVenda"))),
                preco_locacao=decimal_str(number(text(item, "PrecoLocacao"))),
                preco_temporada=decimal_str(number(text(item, "PrecoLocacaoTemporada"))),
                dentro_condominio=child(item, "PrecoCondominio") is not None
                and number(text(item, "PrecoCondominio")) is not None,
                infra_imovel=[name for tag, name in VISTA_FLAGS if text(item, tag) == "Sim"],
                descricao=clean_text(text(item, "Descricao")),
                fotos=_photos(photos),
                taxas=_fees(
                    [
                        fee("IPTU", text(item, "ValorIptu")),
                        fee("Condomínio", text(item, "PrecoCondominio")),
                    ]
                ),
            )
        )
    return out
