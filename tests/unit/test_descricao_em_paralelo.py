# -*- coding: utf-8 -*-
"""
As descrições sob demanda de uma busca rodam em paralelo.

Cada descrição é uma chamada ao Claude que leva alguns segundos (3,8 s medidos
com o Haiku 5.5 em effort high, via Claude Code). Uma depois da outra, as até
5 imagens de uma busca somavam ~19 s antes do re-rank; como são independentes,
em paralelo custam o tempo de uma só.
"""

import threading
import time

import pytest

pytestmark = pytest.mark.unit


def _linhas(n):
    return [{"caminho": f"C:/f{i}.jpg", "nome": f"f{i}.jpg", "folder_id": 1} for i in range(n)]


def test_roda_ao_mesmo_tempo(app_module, monkeypatch):
    threads = set()

    def _lenta(caminho, nome, **kw):
        threads.add(threading.get_ident())
        time.sleep(0.3)
        return f"descricao de {nome}"

    monkeypatch.setattr(app_module, "_descrever_imagem_on_demand", _lenta)
    inicio = time.time()
    saida = app_module._descrever_em_paralelo(_linhas(5), [0, 1, 2, 3, 4], uid=1)
    assert time.time() - inicio < 1.0  # sequencial seriam 1,5 s
    assert len(threads) == 5
    assert saida == {i: f"descricao de f{i}.jpg" for i in range(5)}


def test_falha_numa_imagem_nao_derruba_as_outras(app_module, monkeypatch):
    def _instavel(caminho, nome, **kw):
        if nome == "f1.jpg":
            raise RuntimeError("banco caiu no meio")
        if nome == "f2.jpg":
            return None  # Claude recusou ou não respondeu
        return "ok"

    monkeypatch.setattr(app_module, "_descrever_imagem_on_demand", _instavel)
    assert app_module._descrever_em_paralelo(_linhas(3), [0, 1, 2], uid=1) == {0: "ok"}


def test_sem_candidatas_nao_abre_nada(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module, "_descrever_imagem_on_demand", lambda *a, **k: pytest.fail("não devia chamar")
    )
    assert app_module._descrever_em_paralelo(_linhas(2), [], uid=1) == {}


def test_repassa_pasta_e_usuario(app_module, monkeypatch):
    recebidos = []
    monkeypatch.setattr(
        app_module,
        "_descrever_imagem_on_demand",
        lambda caminho, nome, **kw: recebidos.append(kw) or "ok",
    )
    app_module._descrever_em_paralelo(_linhas(1), [0], uid=42)
    assert recebidos == [{"folder_id": 1, "uid": 42}]
