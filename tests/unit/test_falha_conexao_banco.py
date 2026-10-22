# -*- coding: utf-8 -*-
"""
Banco inacessível no boot vira uma frase, não um traceback.

Sem o banco o app não tem como subir. Antes, a falha estourava na importação
com 15 linhas de traceback do psycopg2 e a janela fechava — o "abre e fecha na
hora" do troubleshooting. Agora o boot diz o que provavelmente aconteceu e onde
mexer, e encerra.
"""

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "erro,trecho",
    [
        ('FATAL:  password authentication failed for user "postgres"', "senha"),
        ('could not translate host name "db.x.supabase.co" to address', "Session pooler"),
        ("connection to server at x, port 5432 failed: timeout expired", "internet"),
        ("Connection refused", "internet"),
    ],
)
def test_causa_conhecida_ganha_orientacao(app_module, erro, trecho):
    assert trecho in app_module._mensagem_falha_banco(Exception(erro))


def test_causa_desconhecida_aponta_para_o_env(app_module):
    assert "DATABASE_URL" in app_module._mensagem_falha_banco(Exception("algo novo"))


def test_mensagem_nunca_repete_a_url(app_module):
    """A URL tem a senha; a mensagem não pode reproduzi-la."""
    erro = Exception("invalid dsn: postgresql://postgres:segredo@host/db")
    assert "segredo" not in app_module._mensagem_falha_banco(erro)
