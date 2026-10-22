# -*- coding: utf-8 -*-
"""
Decisão de carregar os modelos só do cache ou permitir download.

O padrão antigo era sempre offline, o que exigia lembrar de rodar a primeira
vez com `SEARCHPLUS_OFFLINE=0` — esquecido, o app subia com a busca desligada e
sem explicação óbvia. Agora o padrão é automático: offline se os três modelos já
estão no cache do HuggingFace, download liberado se algum falta. A variável
continua valendo para forçar um lado ou o outro.
"""

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("em_cache", [True, False])
def test_valor_1_forca_offline(app_module, em_cache):
    assert app_module._modo_offline("1", em_cache) is True


@pytest.mark.parametrize("em_cache", [True, False])
def test_valor_0_libera_download(app_module, em_cache):
    assert app_module._modo_offline("0", em_cache) is False


@pytest.mark.parametrize("valor", [None, "", "  "])
def test_sem_valor_decide_pelo_cache(app_module, valor):
    assert app_module._modo_offline(valor, True) is True
    assert app_module._modo_offline(valor, False) is False


def _criar_modelo(raiz, nome):
    (raiz / f"models--sentence-transformers--{nome}" / "snapshots").mkdir(parents=True)


def test_cache_vazio(app_module, tmp_path):
    assert app_module._modelos_no_cache(tmp_path) is False


def test_cache_completo(app_module, tmp_path):
    for nome in app_module._MODELOS_HF:
        _criar_modelo(tmp_path, nome)
    assert app_module._modelos_no_cache(tmp_path) is True


def test_cache_incompleto_libera_download(app_module, tmp_path):
    """Faltando um só modelo, a busca visual ou a textual ficaria desligada."""
    _criar_modelo(tmp_path, app_module._MODELOS_HF[0])
    assert app_module._modelos_no_cache(tmp_path) is False


def test_pasta_inexistente(app_module, tmp_path):
    assert app_module._modelos_no_cache(tmp_path / "nao_existe") is False
