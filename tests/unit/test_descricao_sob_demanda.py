# -*- coding: utf-8 -*-
"""
A descrição feita na busca respeita a configuração da pasta.

Ao adicionar uma pasta, a pessoa escolhe o modo (Relâmpago ou Profundo) e o
foco da análise (pessoas, animais, paisagens...). Com a indexação lazy, a
descrição só acontece na busca — e ela estava fixa em `perfil="fast"` e foco
`["tudo"]`. As duas escolhas eram gravadas no banco e nunca usadas: quem
marcava "Profundo" recebia a mesma descrição de quem marcava "Relâmpago".
"""

from unittest import mock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture()
def claude_capturado(app_module):
    """Liga o Claude e troca a chamada real por uma que só registra o pedido."""
    chamadas = []

    def _falso(caminho, prompt, perfil="fast"):
        chamadas.append({"caminho": caminho, "prompt": prompt, "perfil": perfil})
        return "- Estilo: foto\n- O que é: teste"

    with (
        mock.patch.object(app_module, "CLAUDE_OK", True),
        mock.patch.object(app_module, "_analyze_image_claude", side_effect=_falso),
        mock.patch.object(app_module.os.path, "isfile", return_value=True),
    ):
        yield chamadas


def test_usa_perfil_e_foco_da_pasta(app_module, db_roteado, claude_capturado):
    db_roteado(
        {
            "perfil_analise, janela_processamento": {
                "fetchone": {
                    "prioridades": '["animais"]',
                    "perfil_analise": "deep",
                    "janela_processamento": "always",
                }
            }
        }
    )
    desc = app_module._descrever_imagem_on_demand("x.jpg", "x.jpg", folder_id=7, uid=1)

    assert desc
    assert claude_capturado[0]["perfil"] == "deep"
    assert claude_capturado[0]["prompt"] == app_module._build_prompt_visao(["animais"])


def test_arquivo_sem_pasta_usa_o_padrao(app_module, claude_capturado):
    """Arquivo cuja pasta foi removida (folder_id NULL) cai no modo econômico."""
    app_module._descrever_imagem_on_demand("x.jpg", "x.jpg", folder_id=None, uid=1)

    assert claude_capturado[0]["perfil"] == "fast"
    assert claude_capturado[0]["prompt"] == app_module._build_prompt_visao(["tudo"])


def test_pasta_de_outro_usuario_nao_vaza_configuracao(app_module, db_roteado, claude_capturado):
    """A consulta filtra por user_id; sem linha, vale o padrão."""
    db_roteado({})
    app_module._descrever_imagem_on_demand("x.jpg", "x.jpg", folder_id=7, uid=99)

    assert claude_capturado[0]["perfil"] == "fast"
