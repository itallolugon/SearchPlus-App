# -*- coding: utf-8 -*-
"""
Exceção do Python não chega à tela.

O cadastro e os seletores nativos devolviam `str(exc)` ao usuário. Isso mostra
jargão que não ajuda ninguém ("could not translate host name...") e pode
expor host do banco ou caminho interno. A regra é a do RNF-046: mensagem que
diz o que fazer para quem usa, detalhe técnico só no log do servidor.
"""

from unittest import mock

import pytest

pytestmark = pytest.mark.unit

DETALHE = "host=db.segredo.supabase.co senha=xyz"


def _mensagem(resposta):
    corpo = resposta.get_json() or {}
    return corpo.get("mensagem") or corpo.get("error") or ""


class TestCadastro:
    def test_banco_fora_do_ar(self, client, app_module):
        with mock.patch.object(app_module, "get_db", side_effect=RuntimeError(DETALHE)):
            r = client.post("/api/register", json={"username": "u", "password": "p"})
        assert r.status_code == 500
        assert DETALHE not in _mensagem(r)
        assert _mensagem(r)

    def test_erro_inesperado_no_insert(self, client, db_falso):
        _, conexao = db_falso
        conexao.execute.side_effect = RuntimeError(DETALHE)
        r = client.post("/api/register", json={"username": "u", "password": "p"})
        assert r.status_code == 500
        assert DETALHE not in _mensagem(r)
        assert _mensagem(r)


class TestSeletores:
    @pytest.mark.parametrize("rota", ["/api/choose_folder", "/api/choose_image"])
    def test_falha_do_seletor(self, client_logado, app_module, rota):
        with (
            mock.patch.object(app_module, "_tk_pick", side_effect=RuntimeError(DETALHE)),
            mock.patch.object(app_module, "_ultima_pasta_exportacao", return_value=""),
        ):
            r = client_logado.get(rota)
        corpo = r.get_json()
        assert corpo["status"] == "erro"
        assert DETALHE not in corpo["mensagem"]
        assert corpo["mensagem"]
