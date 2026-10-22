# -*- coding: utf-8 -*-
"""
Nome de arquivo não entra cru em HTML montado por template string.

Os nomes vêm do disco do usuário. Inseridos sem escape via `innerHTML`, um `&`
ou aspas quebram o card, e um nome preparado vira marcação. Os cards de
"recentes" já tinham sido corrigidos (montagem pelo DOM); o card de resultado
e o de favoritos ainda interpolavam `${r.nome}` direto entre tags.
"""

import io
import os
import re

import pytest

pytestmark = pytest.mark.unit

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def script():
    with io.open(os.path.join(RAIZ, "script.js"), encoding="utf-8") as f:
        return f.read()


def test_nome_nunca_entre_tags_sem_escape(script):
    codigo = "\n".join(
        linha for linha in script.splitlines() if not linha.lstrip().startswith("//")
    )
    crus = re.findall(r">\s*\$\{r\.nome\}\s*<", codigo)
    assert crus == [], f"nome inserido sem _attr(): {crus}"


def test_cards_usam_o_escape(script):
    assert "<h3>${_attr(r.nome)}</h3>" in script
    assert "<strong>${_attr(r.nome)}</strong>" in script
