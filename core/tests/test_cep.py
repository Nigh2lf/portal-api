import io
import json

import pytest

from core.models import PostalCode
from core.services import lookup_cep, normalize_cep


def _resposta(payload):
    class _Resp(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return _Resp(json.dumps(payload).encode("utf-8"))


def test_normalize_cep():
    assert normalize_cep("01001-000") == "01001000"
    assert normalize_cep("01001 000") == "01001000"
    assert normalize_cep(None) == ""


@pytest.mark.django_db
def test_lookup_cep_consulta_viacep_e_grava_cache(mocker):
    viacep = {"cep": "01001-000", "logradouro": "Praça da Sé", "bairro": "Sé", "localidade": "São Paulo", "uf": "SP", "ibge": "3550308"}
    urlopen = mocker.patch("core.services.services_cep.urllib.request.urlopen", return_value=_resposta(viacep))

    data, error = lookup_cep("01001-000")

    assert error is None
    assert data == {"cep": "01001-000", "logradouro": "Praça da Sé", "bairro": "Sé", "cidade": "São Paulo", "uf": "SP"}
    assert PostalCode.objects.filter(cep="01001000", city="São Paulo").exists()

    data2, _ = lookup_cep("01001000")
    assert data2 == data
    assert urlopen.call_count == 1


@pytest.mark.django_db
def test_lookup_cep_inexistente(mocker):
    mocker.patch("core.services.services_cep.urllib.request.urlopen", return_value=_resposta({"erro": True}))
    data, error = lookup_cep("99999999")
    assert data is None
    assert error.status == 404
    assert PostalCode.objects.get(cep="99999999").not_found is True


def test_lookup_cep_invalido():
    data, error = lookup_cep("123")
    assert data is None
    assert error.status == 400
