# -*- coding: utf-8 -*-
"""
Leitura da descrição gerada pela IA.

O formato de campos ("- Estilo:", "- Pessoas:", ...) é contrato interno: a
busca, o embedding e a galeria dependem dele. Estes testes fixam o parsing para
que uma mudança no prompt não quebre os consumidores em silêncio.
"""

import pytest

pytestmark = pytest.mark.unit

DESCRICAO_FOTO = """- Estilo: foto
- O que é: um cachorro correndo na grama
- Pessoas: nenhuma
- Animais: cachorro (beagle)
- Objetos: bola vermelha, grama
- Ambiente: campo gramado ao ar livre
- Ações: correndo, mordendo a bola
- Texto: nenhum
- Tags: foto, cachorro, beagle, bola"""

DESCRICAO_DESENHO = """- Estilo: ilustração, anime, mangá
- O que é: retrato de uma personagem
- Pessoas: mulher jovem
- Animais: nenhum
- Objetos: cabelo azul, jaqueta
- Ambiente: fundo neutro
- Ações: olhando para frente
- Texto: nenhum
- Tags: anime, ilustração, personagem"""


class TestExtrairCamposDescricao:
    def test_junta_os_campos_relevantes(self, app_module):
        resultado = app_module._extrair_campos_descricao(DESCRICAO_FOTO)
        assert "Animais: cachorro (beagle)" in resultado
        assert "O que é: um cachorro correndo na grama" in resultado

    def test_descarta_ambiente(self, app_module):
        """
        `Ambiente` é ruído para a busca: quase toda foto tem "ao ar livre" ou
        "fundo neutro", o que aproxima imagens sem relação nenhuma.
        """
        resultado = app_module._extrair_campos_descricao(DESCRICAO_FOTO)
        assert "campo gramado" not in resultado
        assert "Ambiente" not in resultado

    def test_descricao_vazia_nao_estoura(self, app_module):
        assert app_module._extrair_campos_descricao("") == ""

    def test_texto_livre_sem_campos(self, app_module):
        """Descrições antigas, sem o formato de campos, não podem quebrar."""
        resultado = app_module._extrair_campos_descricao("apenas um texto solto")
        assert isinstance(resultado, str)


class TestCampoDescricao:
    def test_le_campo_preenchido(self, app_module):
        norm = app_module._normalizar(DESCRICAO_FOTO)
        assert "cachorro" in app_module._campo_descricao(norm, "animais")

    def test_campo_negado_volta_vazio(self, app_module):
        """
        "Pessoas: nenhuma" precisa virar string vazia — é isso que permite à
        regra de rejeição saber que não há pessoa na imagem.
        """
        norm = app_module._normalizar(DESCRICAO_FOTO)
        assert app_module._campo_descricao(norm, "pessoas") == ""

    def test_campo_inexistente_volta_vazio(self, app_module):
        norm = app_module._normalizar(DESCRICAO_FOTO)
        assert app_module._campo_descricao(norm, "campo_que_nao_existe") == ""

    def test_desenho_preenche_pessoas(self, app_module):
        """Personagem desenhada conta como pessoa — regra central do produto."""
        norm = app_module._normalizar(DESCRICAO_DESENHO)
        assert app_module._campo_descricao(norm, "pessoas") != ""


class TestCategoriasDoArquivo:
    def test_foto_de_cachorro_cai_em_animais(self, app_module):
        assert "animais" in app_module._categorias_do_arquivo(DESCRICAO_FOTO)

    def test_desenho_de_pessoa_cai_em_pessoas(self, app_module):
        assert "pessoas" in app_module._categorias_do_arquivo(DESCRICAO_DESENHO)

    def test_retorna_lista(self, app_module):
        assert isinstance(app_module._categorias_do_arquivo(DESCRICAO_FOTO), list)

    def test_descricao_vazia_nao_inventa_categoria(self, app_module):
        assert app_module._categorias_do_arquivo("") == []

    def test_negacao_nao_conta_como_presenca(self, app_module):
        """
        "Animais: nenhum" não pode classificar em `animais` — a palavra-chave
        aparece no rótulo do campo mesmo quando o campo está vazio.
        """
        assert "animais" not in app_module._categorias_do_arquivo(DESCRICAO_DESENHO)


class TestTextoParaEmbedding:
    def test_produz_texto_nao_vazio(self, app_module):
        assert app_module._texto_para_embedding(DESCRICAO_FOTO).strip() != ""

    def test_expande_sinonimos(self, app_module):
        """'cachorro' precisa arrastar 'cao'/'dog' para o vetor casar com sinônimos."""
        resultado = app_module._texto_para_embedding(DESCRICAO_FOTO)
        assert "cao" in resultado or "dog" in resultado

    def test_entrada_vazia_nao_estoura(self, app_module):
        assert isinstance(app_module._texto_para_embedding(""), str)


# Resposta real do Claude Haiku 5.5 (24/11/2026): os campos vieram em negrito
# Markdown. Lidos ao pé da letra, "Animais" saía vazio — e a regra de
# rejeição descartava a foto do cachorro numa busca por "cachorro".
DESCRICAO_MARKDOWN = """- **Estilo:** foto
- **O que é:** Um cachorro correndo na grama com uma bola amarela.
- **Pessoas:** nenhuma
- **Animais:** cachorro (Jack Russell terrier)
- **Objetos:** bola amarela
- **Ambiente:** gramado ao ar livre
- **Ações:** correndo
- **Texto:** nenhum
- **Tags:** foto, cachorro, bola"""


class TestDescricaoEmMarkdown:
    def test_campo_e_lido_apesar_do_negrito(self, app_module):
        norm = app_module._normalizar(DESCRICAO_MARKDOWN)
        assert app_module._campo_descricao(norm, "animais").startswith("cachorro")
        assert app_module._campo_descricao(norm, "pessoas") == ""

    def test_categorias_apesar_do_negrito(self, app_module):
        assert "animais" in app_module._categorias_do_arquivo(DESCRICAO_MARKDOWN)

    def test_embedding_usa_os_campos(self, app_module):
        texto = app_module._extrair_campos_descricao(DESCRICAO_MARKDOWN)
        assert "Animais: cachorro" in texto
        assert "gramado" not in texto  # Ambiente continua de fora
        assert "**" not in texto

    def test_descricao_nova_e_gravada_sem_markdown(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, "CLAUDE_OK", True)
        monkeypatch.setattr(app_module, "_preparar_imagem", lambda caminho: b"jpeg")
        monkeypatch.setattr(
            app_module,
            "_chamar_claude",
            lambda *a, **k: {"texto": DESCRICAO_MARKDOWN, "recusado": False, "cortado": False},
        )
        desc = app_module._analyze_image_claude("x.jpg", "descreva")
        assert "**" not in desc
        assert "- Animais: cachorro (Jack Russell terrier)" in desc

    def test_prompt_pede_texto_simples(self, app_module):
        assert "sem Markdown" in app_module._build_prompt_visao(["tudo"])
