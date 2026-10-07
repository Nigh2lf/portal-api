"""Leitores de cada formato de feed → lista de imóveis no formato normalizado (ver ``base``).

Portados dos conversores do legado (``xml/Padroes/*-PI.php``), com os bugs documentados
corrigidos: feed ou foto únicos não se perdem, "Sale/Rent" guarda venda e aluguel,
flags repetidas não duplicam características.
"""

from __future__ import annotations

from .base import (
    decimal_str,
    filho,
    filhos,
    foto,
    imovel,
    inteiro,
    limpar_texto,
    lista_infra,
    numero,
    taxa,
    texto,
    tipo_gaia_vista,
)


def _fotos(lista):
    return [f for f in lista if f]


def _taxas(lista):
    return [t for t in lista if t]


# ------------------------------------------------------------ PI (nativo)
def ler_pi(raiz):
    """Formato do próprio portal (TrustImóvel / ``<Carga><Imoveis><Imovel>``)."""
    itens = filhos(filho(raiz, "Imoveis"), "Imovel")
    saida = []
    for it in itens:
        fotos = _fotos(foto(texto(f, "URLArquivo"), texto(f, "Principal") == "1") for f in filhos(filho(it, "Fotos"), "Foto"))
        taxas = _taxas(taxa(texto(t, "TaxaDescricao"), texto(t, "TaxaValor"), texto(t, "TaxaOBS") or texto(t, "TaxaObs")) for t in filhos(filho(it, "Taxas"), "Taxa"))
        saida.append(
            imovel(
                codigo=texto(it, "CodigoImovel"),
                destaque=min(2, inteiro(texto(it, "DestaquePortal"))),
                tipo=texto(it, "TipoImovel"),
                cidade=texto(it, "Cidade"),
                bairro=texto(it, "Bairro"),
                uf=texto(it, "UF"),
                quartos=inteiro(texto(it, "QtdDormitorios")),
                banheiros=inteiro(texto(it, "QtdBanheiros")),
                suites=inteiro(texto(it, "QtdSuites")),
                vagas=inteiro(texto(it, "QtdVagas")),
                area_util=decimal_str(numero(texto(it, "AreaUtil"))),
                area_total=decimal_str(numero(texto(it, "AreaTotal"))),
                preco_venda=decimal_str(numero(texto(it, "PrecoVenda"))),
                preco_locacao=decimal_str(numero(texto(it, "PrecoLocacao"))),
                preco_temporada=decimal_str(numero(texto(it, "PrecoLocacaoTemporada"))),
                dentro_condominio=texto(it, "DentroCondominio") == "1",
                infra_imovel=lista_infra(texto(it, "InfraEstruturaImovel")),
                infra_condominio=lista_infra(texto(it, "InfraEstruturaCondominio")),
                descricao=limpar_texto(texto(it, "Observacao")),
                fotos=fotos,
                taxas=taxas,
            )
        )
    return saida


# ------------------------------------------------------------ Value Gaia
FLAGS_GAIA = [
    ("PortaoEletronico", "Portão Eletrônico"), ("FrenteMar", "Frente para o Mar"), ("BeiraMar", "Beira do Mar"),
    ("PeDireitoDuplo", "Pé Direito Duplo"), ("Deposito", "Depósito"), ("Mezanino", "Mezanino"), ("Terraco", "Terraço"),
    ("JardimInverno", "Jardim de Inverno"), ("ServicoCozinha", "Serviço de Cozinha"),
    ("DormitorioEmpregada", "Dormitório de Empregada"), ("Zelador", "Zelador"), ("Adega", "Adega"),
    ("Solarium", "Solarium"), ("Sacada", "Sacada"), ("Lavabo", "Lavabo"), ("DormitorioReversivel", "Dormitório Reversível"),
    ("ArmarioCorredor", "Armário no Corredor"), ("ArmarioCloset", "Closet"), ("ArmarioDormitorio", "Armário no Dormitório"),
    ("ArmarioBanheiro", "Armário no Banheiro"), ("ArmarioSala", "Armário na Sala"), ("ArmarioEscritorio", "Armário no Escritório"),
    ("ArmarioHomeTheater", "Armário no Home Theater"), ("ArmarioDormitorioEmpregada", "Armário no Dormitório de Empregada"),
    ("ArmarioAreaServico", "Armário na Área de Serviço"), ("PisoAquecido", "Piso Aquecido"), ("Agua", "Água"),
    ("ArCondicionado", "Ar Condicionado"), ("ArmarioCozinha", "Armário de Cozinha"), ("Churrasqueira", "Churrasqueira"),
    ("Copa", "Copa"), ("EntradaCaminhoes", "Entrada para Caminhões"), ("Escritorio", "Escritório"), ("Esgoto", "Esgoto"),
    ("Piscina", "Piscina"), ("QuadraPoliEsportiva", "Quadra Poliesportiva"), ("Quintal", "Quintal"), ("Sauna", "Sauna"),
    ("Varanda", "Varanda"), ("Vestiario", "Vestiário"), ("WCEmpregada", "Banheiro de Empregada"),
    ("Hidromassagem", "Hidromassagem"), ("AreaServico", "Área de Serviço"), ("CampoFutebol", "Campo de Futebol"),
    ("Caseiro", "Caseiro"), ("Despensa", "Despensa"), ("Doca", "Doca"), ("Mobiliado", "Mobiliado"),
    ("Lareira", "Lareira"), ("Interfone", "Interfone"),
]


def ler_value_gaia(raiz):
    saida = []
    for it in filhos(filho(raiz, "Imoveis"), "Imovel"):
        fotos = []
        for f in filhos(filho(it, "Fotos"), "Foto"):
            url = texto(f, "URLArquivo") or texto(f, "UrlArquivo")
            fotos.append(foto(url, texto(f, "Principal") == "1"))
        saida.append(
            imovel(
                codigo=texto(it, "CodigoImovel"),
                destaque=1 if texto(it, "TipoOferta") in ("2", "3") else 0,
                tipo=tipo_gaia_vista(texto(it, "TipoImovel")),
                cidade=texto(it, "Cidade"),
                bairro=texto(it, "Bairro"),
                uf=texto(it, "Estado"),
                quartos=inteiro(texto(it, "QtdDormitorios")),
                banheiros=inteiro(texto(it, "QtdBanheiros")),
                suites=inteiro(texto(it, "QtdSuites")),
                vagas=inteiro(texto(it, "QtdVagas")),
                area_util=decimal_str(numero(texto(it, "AreaUtil"))),
                area_total=decimal_str(numero(texto(it, "AreaTotal"))),
                preco_venda=decimal_str(numero(texto(it, "PrecoVenda"))),
                preco_locacao=decimal_str(numero(texto(it, "PrecoLocacao"))),
                preco_temporada=decimal_str(numero(texto(it, "PrecoLocacaoTemporada"))),
                dentro_condominio=filho(it, "CondominioFechado") is not None and texto(it, "CondominioFechado") not in ("0", "false", "False"),
                infra_imovel=[nome for tag, nome in FLAGS_GAIA if texto(it, tag) == "1"],
                descricao=limpar_texto(texto(it, "Observacao")),
                fotos=_fotos(fotos),
                taxas=_taxas([taxa("IPTU", texto(it, "PrecoIptu")), taxa("Condomínio", texto(it, "PrecoCondominio"))]),
            )
        )
    return saida


# --------------------------------------------------------------- Viva Real
TIPOS_VIVA_REAL = {
    "residential/apartment": "Apartamento", "residential/home": "Casa", "residential/farmranch": "Chácara",
    "residential/farm/ranch": "Chácara", "residential/condo": "Casa", "residential/flat": "Flat",
    "residential/landlot": "Terreno Residencial", "residential/land/lot": "Terreno Residencial",
    "residential/sobrado": "Casa", "residential/penthouse": "Cobertura", "residential/kitnet": "Kitnet / Conjugado", "residential/agricultural": "Fazenda / Sítio",
    "commercial/hotel": "Hotel", "commercial/residentialincome": "Imóvel Comercial",
    "commercial/consultorio": "Consultório", "commercial/office": "Sala", "commercial/agricultural": "Sítio",
    "commercial/industrial": "Galpão", "commercial/building": "Imóvel Comercial", "commercial/loja": "Loja",
    "commercial/landlot": "Terreno Comercial", "commercial/land/lot": "Terreno Comercial",
    "commercial/business": "Imóvel Comercial", "commercial/retail": "Imóvel Comercial",
}

INFRA_VIVA_REAL = {
    "Gym": "Academia", "Heating": "Aquecimento", "Air Conditioning": "Ar condicionado", "Maid's Quarters": "Área de serviço",
    "BBQ": "Churrasqueira", "Movie Theater": "Cinema", "TV Security": "Circuito de segurança",
    "Internet Connection": "Conexão à internet", "Gated Community": "Conjunto fechado", "Kitchen": "Cozinha",
    "Warehouse": "Depósito", "Elevator": "Elevador", "Gourmet Area": "Espaço Gourmet", "Juvenile Area": "Espaço Juvenil",
    "Green space / Park": "Espaço verde / Parque", "Reflective Pool": "Espelhos D'água", "Generator": "Gerador elétrico",
    "Lawn": "Grama", "Media Room": "Home cinema", "Home Office": "Home Office", "Intercom": "Interfone",
    "Garden": "Jardim", "Cybercafe": "Lan house", "Fireplace": "Lareira", "Laundry": "Lavanderia",
    "Massage Room": "Sala de Massagem", "Furnished": "Mobiliado", "Close to schools": "Perto de escola",
    "Close to shopping centers": "Perto de Shopping Center", "Close to main roads/avenues": "Perto de vias de acesso",
    "Pool": "Piscina", "Swimming Pool": "Piscina Adulto", "Wading Pool": "Piscina Infantil",
    "Jogging track": "Pista de caminhada", "Playground": "Playground", "Fully Wired": "Cabeamento completo",
    "Close to hospitals": "Próximo a hospitais", "Tennis court": "Quadra de tênis", "Sports Court": "Quadra poliesportiva",
    "Backyard": "Quintal", "Reception room": "Recepção", "Balcony/Terrace": "Sacada", "Party Room": "Salão de Festas",
    "Game room": "Salão de Jogos Adulto", "Game room for kids": "Salão de Jogos para Crianças", "Sauna": "Sauna",
    "24 Hour Security": "Segurança 24 horas", "Cleaning Services": "Serviços de Limpeza", "Alarm System": "Sistema de alarme",
    "Spa": "Spa", "Squash": "Squash", "Cable Television": "TV a cabo", "Veranda": "Varanda Gourmet", "Doorman": "Portaria",
    "Exterior View": "Vista exterior", "Mountain View": "Vista para a montanha", "Lake View": "Vista para lago",
    "Ocean View": "Vista para o mar", "Parking Garage": "Garagem",
}


def ler_viva_real(raiz):
    saida = []
    for it in filhos(filho(raiz, "Listings"), "Listing"):
        det = filho(it, "Details")
        tipo_bruto = texto(det, "PropertyType")
        transacao = texto(it, "TransactionType")
        venda = transacao in ("For Sale", "Sale/Rent")
        aluguel = transacao in ("For Rent", "Sale/Rent")
        aluguel_el = filhos(det, "RentalPrice")
        fotos = []
        for i, m in enumerate(x for x in filhos(filho(it, "Media"), "Item") if "youtu" not in texto(x) and x.get("medium") != "video"):
            fotos.append(foto(texto(m), i == 0))
        loc = filho(it, "Location")
        uf = ""
        estado = filho(loc, "State")
        if estado is not None:
            uf = estado.get("abbreviation") or texto(estado)
        saida.append(
            imovel(
                codigo=texto(it, "ListingID"),
                destaque=1 if texto(it, "PublicationType").upper() in ("PREMIUM", "SUPER_PREMIUM") or texto(it, "Featured") == "true" else 0,
                tipo=TIPOS_VIVA_REAL.get(tipo_bruto.lower().replace(" ", ""), tipo_bruto),
                cidade=texto(loc, "City"),
                bairro=texto(loc, "Neighborhood"),
                uf=uf,
                quartos=inteiro(texto(det, "Bedrooms")),
                banheiros=inteiro(texto(det, "Bathrooms")),
                suites=inteiro(texto(det, "Suites")),
                vagas=inteiro(texto(det, "Garage")),
                area_util=decimal_str(numero(texto(det, "LivingArea"))),
                area_total=decimal_str(numero(texto(det, "LotArea"))),
                preco_venda=decimal_str(numero(texto(det, "ListPrice"))) if venda else None,
                preco_locacao=decimal_str(numero(texto(aluguel_el[0]))) if aluguel and aluguel_el else None,
                dentro_condominio=tipo_bruto.strip() == "Residential / Condo",
                infra_imovel=lista_infra(";".join(INFRA_VIVA_REAL.get(texto(f), texto(f)) for f in filhos(filho(det, "Features"), "Feature"))),
                descricao=limpar_texto(texto(det, "Description")),
                fotos=_fotos(fotos),
                taxas=_taxas([taxa("Condomínio", texto(det, "PropertyAdministrationFee")), taxa("IPTU", texto(det, "YearlyTax"))]),
            )
        )
    return saida


# ------------------------------------------------------------------ Union
FLAGS_UNION = {
    "Aquecedorcentral": "Aquecedor Central", "Aquecedorsolar": "Aquecedor Solar", "Arcondicionado": "Ar Condicionado",
    "Arealazer": "Área de Lazer", "Armariosala": "Armário na Sala", "Armariobanheiro": "Armário no Banheiro",
    "Armariocloset": "Closet", "Armariocozinha": "Armário de Cozinha", "Armariodormitorio": "Armário no Dormitório",
    "Assoalho": "Assoalho", "Banheiroauxiliar": "Banheiro Auxiliar", "Banheiroempregada": "Banheiro de Empregada",
    "Bar": "Bar", "Brinquedoteca": "Brinquedoteca", "Cachoeira": "Cachoeira", "Campofutebol": "Campo de Futebol",
    "Casacaseiro": "Casa de Caseiro", "Celeiro": "Celeiro", "Churrasqueira": "Churrasqueira", "CircuitoTV": "Circuito de TV",
    "Contrapiso": "Contrapiso", "Copa": "Copa", "Curral": "Curral", "Deck": "Deck", "Despensa": "Despensa",
    "Dormitoriosempregada": "Dormitório de Empregada", "Elevadorcarga": "Elevador de Carga", "Escritorio": "Escritório",
    "Forno": "Forno", "Garagembarco": "Garagem de Barco", "Gerador": "Gerador", "Hall": "Hall", "Hidro": "Hidromassagem",
    "Jardim": "Jardim", "Lareira": "Lareira", "Lavanderia": "Lavanderia", "Mobiliado": "Mobiliado",
    "Piscinaaquecida": "Piscina Aquecida", "Piscina": "Piscina", "Playground": "Playground",
    "Quadrapoliesportiva": "Quadra Poliesportiva", "Quadrasquash": "Quadra de Squash", "Quintal": "Quintal",
    "SalaTV": "Sala de TV", "Sauna": "Sauna", "TVCabo": "TV a Cabo",
}


def _preco_union(it, flag, campo):
    return decimal_str(numero(texto(it, campo))) if texto(it, flag) == "1" else None


def ler_union(raiz):
    saida = []
    for it in filhos(filho(raiz, "Imoveis"), "Imovel"):
        fotos = [foto(texto(f, "URL"), texto(f, "Principal") == "1") for f in filhos(filho(it, "Fotos"), "Foto")]
        saida.append(
            imovel(
                codigo=texto(it, "Referencia"),
                destaque=1 if texto(it, "Destaque") == "1" else 0,
                tipo=limpar_texto(texto(it, "Tipo")),
                cidade=texto(it, "Cidade"),
                bairro=texto(it, "Bairro"),
                uf=texto(it, "UnidadeFederativa"),
                quartos=inteiro(texto(it, "Dormitorios")),
                banheiros=inteiro(texto(it, "Banheiro2")),
                suites=inteiro(texto(it, "Suite")),
                vagas=inteiro(texto(it, "Garagem")),
                area_util=decimal_str(numero(texto(it, "Areacosntruida") or texto(it, "Areaconstruida"))),
                area_total=decimal_str(numero(texto(it, "Areaterreno"))),
                preco_venda=_preco_union(it, "Venda", "Valorvenda"),
                preco_locacao=_preco_union(it, "Locacao", "Valorlocacao"),
                preco_temporada=_preco_union(it, "Temporada", "Valortemporada"),
                dentro_condominio=texto(it, "Condominio") == "1",
                infra_imovel=[nome for tag, nome in FLAGS_UNION.items() if texto(it, tag) == "1"],
                descricao=limpar_texto(texto(it, "Anuncioparainternet")),
                fotos=_fotos(fotos),
                taxas=_taxas([taxa("Condomínio", texto(it, "Valorcondominio")), taxa("IPTU", texto(it, "Valoriptu"))]),
            )
        )
    return saida


# ------------------------------------------------------------------ Vista
FLAGS_VISTA = [
    ("ArCondicionado", "Ar Condicionado"), ("AreaServico", "Área de Serviço"), ("ArmarioEmbutido", "Armário Embutido"),
    ("Churrasqueira", "Churrasqueira"), ("Closet", "Closet"), ("Copa", "Copa"), ("Despensa", "Despensa"),
    ("FrenteMar", "De Frente para o Mar"), ("Guarita", "Guarita"), ("Heliponto", "Heliponto"),
    ("Hidromassagem", "Hidromassagem"), ("HomeTheater", "Home Theater"), ("InfraInternet", "Internet"),
    ("Interfone", "Interfone"), ("Jardim", "Jardim"), ("Lancamento", "Lançamento"), ("Lareira", "Lareira"),
    ("Mezanino", "Mezanino"), ("Mobiliado", "Mobiliado"), ("Piscina", "Piscina"), ("Playground", "Playground"),
    ("QuadraPoliEsportiva", "Quadra Poliesportiva"), ("QuadraTenis", "Quadra de Tênis"), ("Quintal", "Quintal"),
    ("SalaGinastica", "Sala de Ginástica"), ("SalaJantar", "Sala de Jantar"), ("SalaoFestas", "Salão de Festas"),
    ("SalaoJogos", "Salão de Jogos"), ("Sauna", "Sauna"), ("Telefone", "Telefone"), ("Terraco", "Terraço"),
    ("TVCabo", "TV a Cabo"), ("Varanda", "Varanda"), ("WCEmpregada", "Banheiro de Empregada"),
]


def ler_vista(raiz):
    saida = []
    for it in filhos(raiz, "Imovel"):
        fotos = [foto(texto(f, "URL"), i == 0) for i, f in enumerate(filhos(filho(it, "Fotos"), "Foto"))]
        destaque = texto(it, "Destaque")
        saida.append(
            imovel(
                codigo=texto(it, "CodigoImovel"),
                destaque=1 if destaque and destaque != "Nao" else 0,
                tipo=tipo_gaia_vista(texto(it, "TipoImovel")),
                cidade=texto(it, "Cidade"),
                bairro=texto(it, "Bairro"),
                uf=texto(it, "UF"),
                quartos=inteiro(texto(it, "QtdDormitorios")),
                banheiros=inteiro(texto(it, "QtdBanheiros")),
                suites=inteiro(texto(it, "QtdSuites")),
                vagas=inteiro(texto(it, "QtdVagas")),
                area_util=decimal_str(numero(texto(it, "AreaUtil"))),
                area_total=decimal_str(numero(texto(it, "AreaTotal"))),
                preco_venda=decimal_str(numero(texto(it, "PrecoVenda"))),
                preco_locacao=decimal_str(numero(texto(it, "PrecoLocacao"))),
                preco_temporada=decimal_str(numero(texto(it, "PrecoLocacaoTemporada"))),
                dentro_condominio=filho(it, "PrecoCondominio") is not None and numero(texto(it, "PrecoCondominio")) is not None,
                infra_imovel=[nome for tag, nome in FLAGS_VISTA if texto(it, tag) == "Sim"],
                descricao=limpar_texto(texto(it, "Descricao")),
                fotos=_fotos(fotos),
                taxas=_taxas([taxa("IPTU", texto(it, "ValorIptu")), taxa("Condomínio", texto(it, "PrecoCondominio"))]),
            )
        )
    return saida
