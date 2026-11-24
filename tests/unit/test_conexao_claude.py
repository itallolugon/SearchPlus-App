# -*- coding: utf-8 -*-
"""
Conexão com o Claude: credencial, modos de chamada e tela de configuração.

O que está em jogo aqui é uma credencial que dá acesso à conta de alguém —
seja a assinatura (token de `claude setup-token`) ou créditos da API. Os testes
fixam três garantias: a credencial nunca sai do servidor (nem na resposta, nem
no log), cada modo usa a credencial certa, e toda falha vira uma mensagem que
diz o que fazer.
"""

import json
import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest

pytestmark = pytest.mark.unit

TOKEN = "sk-ant-oat01-" + "T" * 40
CHAVE = "sk-ant-api03-" + "K" * 40

_VARS = (
    "ANTHROPIC_API_KEY",
    "SEARCHPLUS_CLAUDE_TOKEN",
    "CLAUDE_PROVEDOR",
    "CLAUDE_MODEL",
    "CLAUDE_EFFORT",
)


@pytest.fixture()
def ambiente_claude(app_module, tmp_path, monkeypatch):
    """Isola o .env, as variáveis e o estado global da conexão."""
    # A carga dos modelos, em segundo plano desde o import, chama
    # _iniciar_claude() ao terminar — e desfaria o cenário montado abaixo.
    assert app_module._MODELOS_RESOLVIDOS.wait(timeout=60)
    for nome in _VARS:
        monkeypatch.delenv(nome, raising=False)
    env = tmp_path / ".env"
    env.write_text("# comentário\nDATABASE_URL=postgresql://x:y@h/db\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "ARQUIVO_ENV", env)
    monkeypatch.setattr(app_module, "_restringir_ao_dono", lambda caminho: None)
    monkeypatch.setattr(app_module, "CLAUDE_PROVEDOR", "assinatura")
    monkeypatch.setattr(app_module, "CLAUDE_MODEL", "claude-haiku-5-5")
    monkeypatch.setattr(app_module, "CLAUDE_EFFORT", "high")
    monkeypatch.setattr(app_module, "_CLAUDE", None)
    monkeypatch.setattr(app_module, "CLAUDE_OK", False)
    monkeypatch.setitem(app_module._estado_claude, "estado", "iniciando")
    monkeypatch.setitem(app_module._estado_claude, "uso", None)
    return env


# ── .env ───────────────────────────────────────────────────────────────────


class TestGravarNoEnv:
    def test_preserva_o_resto_do_arquivo(self, app_module, ambiente_claude):
        app_module._gravar_no_env({"SEARCHPLUS_CLAUDE_TOKEN": TOKEN})
        texto = ambiente_claude.read_text(encoding="utf-8")
        assert "DATABASE_URL=postgresql://x:y@h/db" in texto
        assert "# comentário" in texto
        assert f"SEARCHPLUS_CLAUDE_TOKEN={TOKEN}" in texto

    def test_substitui_sem_duplicar(self, app_module, ambiente_claude):
        app_module._gravar_no_env({"CLAUDE_EFFORT": "low"})
        app_module._gravar_no_env({"CLAUDE_EFFORT": "high"})
        texto = ambiente_claude.read_text(encoding="utf-8")
        assert texto.count("CLAUDE_EFFORT=") == 1
        assert "CLAUDE_EFFORT=high" in texto

    def test_none_remove_a_variavel(self, app_module, ambiente_claude):
        app_module._gravar_no_env({"ANTHROPIC_API_KEY": CHAVE})
        app_module._gravar_no_env({"ANTHROPIC_API_KEY": None})
        assert "ANTHROPIC_API_KEY" not in ambiente_claude.read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" not in app_module.os.environ

    @pytest.mark.parametrize("valor", ["a\nDATABASE_URL=outra", 'com"aspas'])
    def test_recusa_valor_que_quebraria_o_arquivo(self, app_module, ambiente_claude, valor):
        with pytest.raises(ValueError):
            app_module._gravar_no_env({"CLAUDE_MODEL": valor})
        assert "DATABASE_URL=postgresql://x:y@h/db" in ambiente_claude.read_text(encoding="utf-8")


# ── Validação da credencial ────────────────────────────────────────────────


class TestValidacao:
    def test_token_serve_para_a_assinatura(self, app_module):
        assert app_module._validar_credencial("assinatura", TOKEN) == ""

    def test_chave_serve_para_a_api(self, app_module):
        assert app_module._validar_credencial("api", CHAVE) == ""

    def test_chave_de_api_no_modo_assinatura(self, app_module):
        assert "Chave de API" in app_module._validar_credencial("assinatura", CHAVE)

    def test_token_no_modo_api(self, app_module):
        """O token da assinatura não pode virar credencial do SDK."""
        assert "Assinatura" in app_module._validar_credencial("api", TOKEN)

    @pytest.mark.parametrize("provedor", ["assinatura", "api"])
    @pytest.mark.parametrize(
        "valor", ["", "sk-ant-admin01-" + "A" * 40, "sk-ant-api03 com espaço", "qualquer-coisa"]
    )
    def test_formatos_invalidos(self, app_module, provedor, valor):
        assert app_module._validar_credencial(provedor, valor) != ""


# ── Modo assinatura: Claude Code ───────────────────────────────────────────


def _saida_claude_code(*eventos):
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout="\n".join(json.dumps(e) for e in eventos), stderr=""
    )


class TestModoAssinatura:
    @pytest.fixture()
    def claude_code(self, app_module, ambiente_claude, monkeypatch):
        monkeypatch.setenv("SEARCHPLUS_CLAUDE_TOKEN", TOKEN)
        monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE)  # tem que ficar de fora
        monkeypatch.setattr(app_module, "_binario_claude_code", lambda: "claude.exe")
        chamadas = []

        def _run(cmd, **kwargs):
            chamadas.append((cmd, kwargs))
            return _run.saida

        _run.saida = _saida_claude_code(
            {
                "type": "rate_limit_event",
                "rate_limit_info": {
                    "status": "allowed",
                    "unifiedWindows": {
                        "five_hour": {"utilization": 0.36},
                        "seven_day": {"utilization": 0.17},
                    },
                },
            },
            {
                "type": "result",
                "is_error": False,
                "result": "um cachorro",
                "stop_reason": "end_turn",
            },
        )
        monkeypatch.setattr(app_module.subprocess, "run", _run)
        return chamadas, _run

    def test_comando_isolado_com_modelo_e_effort(self, app_module, claude_code):
        chamadas, _ = claude_code
        r = app_module._chamar_claude([{"type": "text", "text": "oi"}])
        assert r["texto"] == "um cachorro"
        cmd, kwargs = chamadas[0]
        assert cmd[cmd.index("--model") + 1] == "claude-haiku-5-5"
        assert cmd[cmd.index("--effort") + 1] == "high"
        assert cmd[cmd.index("--tools") + 1] == ""  # nenhuma ferramenta
        assert cmd[cmd.index("--setting-sources") + 1] == ""
        for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
            assert flag in cmd

    def test_token_so_no_subprocesso_e_sem_chave_de_api(self, app_module, claude_code):
        """ANTHROPIC_API_KEY venceria o token na precedência do Claude Code."""
        chamadas, _ = claude_code
        app_module._chamar_claude("oi")
        ambiente = chamadas[0][1]["env"]
        assert ambiente["CLAUDE_CODE_OAUTH_TOKEN"] == TOKEN
        assert "ANTHROPIC_API_KEY" not in ambiente
        assert "SEARCHPLUS_CLAUDE_TOKEN" not in ambiente
        assert TOKEN not in " ".join(chamadas[0][0])  # nunca na linha de comando

    def test_imagem_vai_pela_entrada_padrao(self, app_module, claude_code):
        chamadas, _ = claude_code
        app_module._chamar_claude(
            [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": "QUJD"},
                }
            ]
        )
        entrada = json.loads(chamadas[0][1]["input"])
        assert entrada["message"]["content"][0]["type"] == "image"

    def test_registra_o_uso_da_cota(self, app_module, claude_code):
        app_module._chamar_claude("oi")
        assert app_module._estado_claude["uso"] == {
            "status": "allowed",
            "janela_5h": 36,
            "janela_semanal": 17,
        }
        assert app_module._estado_claude["estado"] == "conectado"

    def test_saida_estruturada(self, app_module, claude_code):
        _, run = claude_code
        run.saida = _saida_claude_code(
            {"type": "result", "is_error": False, "structured_output": {"veredictos": []}}
        )
        r = app_module._chamar_claude("oi", schema={"type": "object"})
        assert json.loads(r["texto"]) == {"veredictos": []}

    @pytest.mark.parametrize(
        "status,estado", [(401, "credencial_invalida"), (429, "limite"), (529, "indisponivel")]
    )
    def test_erros_viram_estado(self, app_module, claude_code, status, estado):
        _, run = claude_code
        run.saida = _saida_claude_code(
            {"type": "result", "is_error": True, "api_error_status": status, "result": "erro"}
        )
        with pytest.raises(app_module.FalhaClaude) as falha:
            app_module._chamar_claude("oi")
        assert falha.value.estado == estado
        assert app_module._estado_claude["estado"] == estado
        assert app_module._estado_claude["mensagem"]

    def test_demora_vira_sem_conexao(self, app_module, claude_code, monkeypatch):
        def _estoura(*a, **k):
            raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

        monkeypatch.setattr(app_module.subprocess, "run", _estoura)
        with pytest.raises(app_module.FalhaClaude) as falha:
            app_module._chamar_claude("oi")
        assert falha.value.estado == "sem_conexao"

    def test_sem_claude_code_instalado(self, app_module, claude_code, monkeypatch):
        monkeypatch.setattr(app_module, "_binario_claude_code", lambda: None)
        with pytest.raises(app_module.FalhaClaude) as falha:
            app_module._chamar_claude("oi")
        assert falha.value.estado == "nao_instalado"


# ── Modo API: SDK ──────────────────────────────────────────────────────────


def _resposta_api(texto, stop="end_turn"):
    # O Haiku 5.5 pensa por padrão: o bloco de raciocínio vem antes do texto.
    return SimpleNamespace(
        stop_reason=stop,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=texto),
        ],
    )


class TestModoApi:
    @pytest.fixture()
    def sdk(self, app_module, ambiente_claude, monkeypatch):
        cliente = mock.MagicMock()
        cliente.messages.create.return_value = _resposta_api("um gato")
        monkeypatch.setattr(app_module, "CLAUDE_PROVEDOR", "api")
        monkeypatch.setattr(app_module, "_CLAUDE", cliente)
        monkeypatch.setattr(app_module, "CLAUDE_OK", True)
        return cliente

    def test_usa_modelo_effort_e_teto_com_folga(self, app_module, sdk):
        r = app_module._chamar_claude("oi", schema={"type": "object"})
        assert r["texto"] == "um gato"
        kwargs = sdk.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-5-5"
        assert kwargs["output_config"]["effort"] == "high"
        assert kwargs["output_config"]["format"]["type"] == "json_schema"
        assert kwargs["max_tokens"] >= 8000  # cabe o raciocínio do effort alto
        for proibido in ("temperature", "top_p", "top_k"):
            assert proibido not in kwargs  # o Haiku 5.5 recusa com 400

    def test_resposta_cortada_e_recusa(self, app_module, sdk):
        sdk.messages.create.return_value = _resposta_api("", stop="max_tokens")
        assert app_module._chamar_claude("oi")["cortado"] is True
        sdk.messages.create.return_value = _resposta_api("", stop="refusal")
        assert app_module._chamar_claude("oi")["recusado"] is True

    def test_erro_do_sdk_vira_estado(self, app_module, sdk):
        anthropic = pytest.importorskip("anthropic")
        erro = anthropic.BadRequestError.__new__(anthropic.BadRequestError)
        erro.message = "Your credit balance is too low to access the Anthropic API."
        sdk.messages.create.side_effect = erro
        with pytest.raises(app_module.FalhaClaude) as falha:
            app_module._chamar_claude("oi")
        assert falha.value.estado == "sem_credito"

    @pytest.mark.parametrize(
        "classe,estado",
        [
            ("AuthenticationError", "credencial_invalida"),
            ("NotFoundError", "modelo_indisponivel"),
            ("RateLimitError", "limite"),
            ("APIConnectionError", "sem_conexao"),
        ],
    )
    def test_classificacao(self, app_module, classe, estado):
        anthropic = pytest.importorskip("anthropic")
        cls = getattr(anthropic, classe)
        erro = cls.__new__(cls)
        assert app_module._classificar_erro_api(erro)[0] == estado


# ── Descrição e re-rank usam a configuração ────────────────────────────────


class TestUsoNasChamadasReais:
    @pytest.fixture()
    def chamada(self, app_module, ambiente_claude, monkeypatch):
        capturado = {}

        def _falso(conteudo, **kwargs):
            capturado["conteudo"], capturado["kwargs"] = conteudo, kwargs
            return capturado["resposta"]

        monkeypatch.setattr(app_module, "CLAUDE_OK", True)
        monkeypatch.setattr(app_module, "_chamar_claude", _falso)
        monkeypatch.setattr(app_module, "_preparar_imagem", lambda caminho: b"jpeg")
        return capturado

    def test_descricao_manda_a_imagem(self, app_module, chamada):
        chamada["resposta"] = {"texto": "- Estilo: foto", "recusado": False, "cortado": False}
        assert app_module._analyze_image_claude("x.jpg", "descreva") == "- Estilo: foto"
        assert chamada["conteudo"][0]["type"] == "image"

    def test_descricao_cortada_nao_vira_cache(self, app_module, chamada):
        """Texto pela metade gravado como descrição ficaria para sempre."""
        chamada["resposta"] = {"texto": "- Estilo: fo", "recusado": False, "cortado": True}
        assert app_module._analyze_image_claude("x.jpg", "descreva") is None

    def test_rerank_com_raciocinio_antes_do_json(self, app_module, chamada):
        chamada["resposta"] = {
            "texto": json.dumps(
                {"veredictos": [{"n": 1, "corresponde": True}, {"n": 2, "corresponde": False}]}
            ),
            "recusado": False,
            "cortado": False,
        }
        candidatos = [
            {
                "nome": "cao.jpg",
                "tipo": "jpg",
                "descricao_ia": "cachorro",
                "score": 0.9,
                "_sbert": 0.5,
            },
            {
                "nome": "gato.jpg",
                "tipo": "jpg",
                "descricao_ia": "gato",
                "score": 0.8,
                "_sbert": 0.5,
            },
        ]
        saida = app_module._rerank_com_claude("cachorro", candidatos)
        assert [c["nome"] for c in saida] == ["cao.jpg", "gato.jpg"]
        assert saida[1]["score"] == 0.10
        assert chamada["kwargs"]["schema"]["required"] == ["veredictos"]

    def test_rerank_mantem_ordem_se_o_claude_falhar(self, app_module, ambiente_claude, monkeypatch):
        def _falha(*a, **k):
            raise app_module.FalhaClaude("limite", "acabou")

        monkeypatch.setattr(app_module, "CLAUDE_OK", True)
        monkeypatch.setattr(app_module, "_chamar_claude", _falha)
        candidatos = [{"nome": "a.jpg", "tipo": "jpg", "descricao_ia": "x", "score": 0.5}]
        assert app_module._rerank_com_claude("q", candidatos) == candidatos


# ── Rotas da tela ──────────────────────────────────────────────────────────


class TestRotas:
    @pytest.fixture()
    def sem_rede(self, app_module, ambiente_claude, monkeypatch):
        """Nenhuma rota de teste fala com a Anthropic nem com o Claude Code."""

        def _testar(com_chamada):
            app_module._definir_estado_claude("conectado")
            return dict(app_module._estado_claude)

        monkeypatch.setattr(app_module, "_testar_claude", _testar)
        monkeypatch.setattr(app_module, "_binario_claude_code", lambda: "claude.exe")
        return ambiente_claude

    @pytest.mark.parametrize(
        "metodo,rota",
        [
            ("get", "/api/claude"),
            ("post", "/api/claude"),
            ("post", "/api/claude/testar"),
            ("delete", "/api/claude/credencial"),
        ],
    )
    def test_exige_login(self, client, metodo, rota):
        assert getattr(client, metodo)(rota, json={}).status_code == 401

    def test_so_aceita_a_propria_maquina(self, client_logado, sem_rede):
        r = client_logado.get("/api/claude", environ_base={"REMOTE_ADDR": "10.0.0.7"})
        assert r.status_code == 403

    def test_recusa_escrita_de_outro_site(self, client_logado, sem_rede):
        r = client_logado.post(
            "/api/claude",
            json={"effort": "low"},
            headers={"Origin": "https://site-malicioso.example"},
        )
        assert r.status_code == 403

    def test_recusa_corpo_que_nao_e_json(self, client_logado, sem_rede):
        r = client_logado.post("/api/claude", data="credencial=x")
        assert r.status_code == 415

    def test_salva_e_nunca_devolve_a_credencial(self, app_module, client_logado, sem_rede, capsys):
        r = client_logado.post(
            "/api/claude",
            json={
                "provedor": "assinatura",
                "credencial": TOKEN,
                "modelo": "claude-haiku-5-5",
                "effort": "high",
            },
        )
        assert r.status_code == 200
        corpo = r.get_data(as_text=True)
        assert TOKEN not in corpo
        assert r.get_json()["final_credencial"] == TOKEN[-4:]
        assert r.get_json()["configurada"] is True
        assert TOKEN not in capsys.readouterr().out  # nem no log
        assert f"SEARCHPLUS_CLAUDE_TOKEN={TOKEN}" in sem_rede.read_text(encoding="utf-8")
        assert app_module.CLAUDE_OK is True

    def test_get_nao_tem_a_credencial(self, client_logado, sem_rede, monkeypatch):
        monkeypatch.setenv("SEARCHPLUS_CLAUDE_TOKEN", TOKEN)
        assert TOKEN not in client_logado.get("/api/claude").get_data(as_text=True)

    @pytest.mark.parametrize(
        "corpo",
        [
            {"provedor": "outro"},
            {"modelo": "claude-inventado-9"},
            {"effort": "turbo"},
            {"provedor": "assinatura", "credencial": CHAVE},
            {"provedor": "api", "credencial": TOKEN},
        ],
    )
    def test_valida_antes_de_gravar(self, client_logado, sem_rede, corpo):
        antes = sem_rede.read_text(encoding="utf-8")
        r = client_logado.post("/api/claude", json=corpo)
        assert r.status_code == 400
        assert r.get_json()["error"]
        assert sem_rede.read_text(encoding="utf-8") == antes

    def test_remover_credencial(self, app_module, client_logado, sem_rede):
        client_logado.post("/api/claude", json={"provedor": "assinatura", "credencial": TOKEN})
        r = client_logado.delete("/api/claude/credencial")
        assert r.get_json()["configurada"] is False
        assert r.get_json()["estado"] == "sem_credencial"
        assert "SEARCHPLUS_CLAUDE_TOKEN" not in sem_rede.read_text(encoding="utf-8")
        assert app_module.CLAUDE_OK is False
