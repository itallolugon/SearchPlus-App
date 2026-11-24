# -*- coding: utf-8 -*-
"""
Painel "Conexão com o Claude": a credencial não fica no navegador.

O servidor nunca devolve a credencial; estes testes fixam o lado do front: o
campo é de senha, não é preenchido pelo navegador, é limpo ao salvar e ao
fechar, e nada do painel passa pelo localStorage nem pelo console.
"""

import io
import os
import re

import pytest

pytestmark = pytest.mark.unit

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ler(nome):
    with io.open(os.path.join(RAIZ, nome), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def secao_js():
    js = _ler("script.js")
    inicio = js.index("// CONEXÃO COM O CLAUDE")
    fim = js.index("function selecionarTabCg(", inicio)
    # Só código: os comentários explicam justamente por que não usar o localStorage.
    linhas = js[inicio:fim].splitlines()
    return "\n".join(linha for linha in linhas if not linha.lstrip().startswith("//"))


@pytest.fixture(scope="module")
def html():
    return _ler("index.html")


def test_campo_e_de_senha_sem_autopreenchimento(html):
    campo = re.search(r'<input[^>]*id="claudeCredencial"[^>]*>', html, re.S).group(0)
    assert 'type="password"' in campo
    assert 'autocomplete="off"' in campo


def test_nada_vai_para_o_armazenamento_do_navegador(secao_js):
    for proibido in ("localStorage", "sessionStorage", "document.cookie", "console.log"):
        assert proibido not in secao_js, proibido


def test_campo_e_limpo_ao_fechar_e_ao_salvar(secao_js):
    fechar = secao_js[secao_js.index("function fecharClaudeModal") :]
    assert "claudeCredencial').value = ''" in fechar.split("}", 1)[0]
    salvar = secao_js[secao_js.index("async function salvarClaude") :]
    assert "campo.value = ''" in salvar


def test_texto_do_servidor_entra_por_textcontent(secao_js):
    assert "innerHTML" not in secao_js


def test_indicador_comeca_escondido(html):
    botao = re.search(r'<button[^>]*id="claudeIndicador"[^>]*>', html, re.S).group(0)
    assert 'type="button"' in botao
    assert "display: none" in botao
