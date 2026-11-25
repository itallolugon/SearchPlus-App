# -*- coding: utf-8 -*-
"""
Modo público e envio de arquivos pelo navegador.

O modo público existe para o Search+ ficar acessível por um link na internet
(um túnel até a máquina onde ele roda). Nessa situação, quem tem uma conta não
pode mexer no disco do servidor: cadastrar 'C:\\' como pasta deixaria ler
qualquer arquivo de lá — inclusive o backend/.env, com a senha do banco.

Por isso as rotas que tocam no disco ou no Windows da máquina ficam bloqueadas,
e os arquivos chegam pelo navegador, em /api/upload, numa pasta só do usuário.
"""

import io
import os
import queue

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture()
def modo_publico(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "MODO_PUBLICO", True)


@pytest.fixture()
def envios(app_module, monkeypatch, tmp_path):
    """Pasta de envios temporária e uma fila limpa para conferir o que entrou."""
    monkeypatch.setattr(app_module, "PASTA_ENVIOS", tmp_path / "envios")
    fila = queue.Queue()
    monkeypatch.setattr(app_module, "_queue", fila)
    return tmp_path / "envios", fila


# ── Bloqueios ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "metodo, rota",
    [
        ("POST", "/api/register"),
        ("POST", "/api/cadastro"),
        ("POST", "/api/folders"),
        ("GET", "/api/choose_folder"),
        ("GET", "/api/choose_image"),
        ("GET", "/api/estimate_time?pasta=C:\\"),
        ("GET", "/api/open_location?path=C:\\"),
        ("GET", "/api/open_folder?path=C:\\"),
        ("POST", "/api/collections/1/export"),
        ("POST", "/api/collections/1/sync"),
        ("DELETE", "/api/collections/1/sync"),
        ("PATCH", "/api/collections/1/folders"),
        ("DELETE", "/api/collections/1/folders"),
        ("POST", "/api/exportacoes/1/repetir"),
        ("POST", "/api/exportacoes/1/limpar_sumidos"),
        ("GET", "/api/debug/files"),
        ("GET", "/api/debug/scores"),
        ("POST", "/api/claude"),
        ("POST", "/api/claude/testar"),
        ("DELETE", "/api/claude/credencial"),
        ("POST", "/api/clear_cache"),
    ],
)
def test_rota_que_mexe_na_maquina_fica_bloqueada(client_logado, modo_publico, metodo, rota):
    r = client_logado.open(rota, method=metodo, json={})
    assert r.status_code == 403
    assert "versão on-line" in r.get_json()["error"]


def test_bloqueio_vale_mesmo_sem_login(client, modo_publico):
    """O cadastro é justamente o que um visitante sem conta tentaria."""
    r = client.post("/api/register", json={"username": "x", "password": "y"})
    assert r.status_code == 403


@pytest.mark.parametrize(
    "metodo, rota",
    [
        ("GET", "/api/folders"),
        ("GET", "/api/collections/1/folders"),
    ],
)
def test_leitura_continua_liberada(client_logado, modo_publico, db_roteado, metodo, rota):
    db_roteado({})
    r = client_logado.open(rota, method=metodo)
    assert r.status_code != 403


def test_fora_do_modo_publico_nada_e_bloqueado(client_logado, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "MODO_PUBLICO", False)
    r = client_logado.post("/api/folders", json={"pasta": ""})
    assert r.status_code == 400  # chegou no handler, que recusou o caminho vazio


# ── check_session avisa o front ──────────────────────────────────────────────


def test_check_session_sem_login_informa_modo_publico(client, modo_publico):
    r = client.get("/api/check_session")
    assert r.status_code == 401
    assert r.get_json()["modo_publico"] is True


def test_check_session_logado_informa_modo_publico(client_logado, modo_publico, db_roteado):
    db_roteado({"SELECT username FROM users": {"fetchone": {"username": "banca"}}})
    r = client_logado.get("/api/check_session")
    assert r.status_code == 200
    assert r.get_json() == {"username": "banca", "modo_publico": True}


def test_check_session_fora_do_modo_publico(client_logado, app_module, monkeypatch, db_roteado):
    monkeypatch.setattr(app_module, "MODO_PUBLICO", False)
    db_roteado({"SELECT username FROM users": {"fetchone": {"username": "banca"}}})
    assert client_logado.get("/api/check_session").get_json()["modo_publico"] is False


# ── Envio de arquivos ────────────────────────────────────────────────────────


def _arquivo(nome, conteudo=b"\xff\xd8\xff conteudo"):
    return (io.BytesIO(conteudo), nome)


def _enviar(cliente, *arquivos):
    return cliente.post(
        "/api/upload",
        data={"arquivos": list(arquivos)},
        content_type="multipart/form-data",
    )


def test_upload_exige_login(client, envios):
    assert _enviar(client, _arquivo("a.jpg")).status_code == 401


def test_upload_sem_arquivo_da_400(client_logado, envios, db_roteado):
    db_roteado({})
    r = client_logado.post("/api/upload", data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_upload_grava_na_pasta_do_usuario_e_entra_na_fila(client_logado, envios, db_roteado):
    pasta_base, fila = envios
    db_roteado({"SELECT id FROM folders": {"fetchone": {"id": 7}}})

    r = _enviar(client_logado, _arquivo("cachorro.jpg"), _arquivo("relatório.pdf"))

    assert r.status_code == 200
    corpo = r.get_json()
    assert corpo["enviados"] == 2
    assert corpo["ignorados"] == []

    pasta = pasta_base / "4242"
    assert (pasta / "cachorro.jpg").read_bytes() == b"\xff\xd8\xff conteudo"
    assert (pasta / "relatório.pdf").exists()  # acento preservado

    itens = [fila.get_nowait() for _ in range(fila.qsize())]
    assert {i["nome"] for i in itens} == {"cachorro.jpg", "relatório.pdf"}
    assert all(i["uid"] == 4242 and i["folder_id"] == 7 for i in itens)
    assert {i["ext"] for i in itens} == {"jpg", "pdf"}


def test_upload_cria_o_registro_da_pasta(client_logado, envios, db_roteado):
    conexao = db_roteado({"RETURNING id": {"fetchone": {"id": 9}}})
    _enviar(client_logado, _arquivo("a.jpg"))
    sqls = [str(c.args[0]) for c in conexao.execute.call_args_list]
    assert any("INSERT INTO folders" in s for s in sqls)


def test_upload_ignora_tipo_nao_suportado(client_logado, envios, db_roteado):
    pasta_base, fila = envios
    db_roteado({"SELECT id FROM folders": {"fetchone": {"id": 7}}})

    r = _enviar(client_logado, _arquivo("virus.exe"), _arquivo("foto.png"))

    corpo = r.get_json()
    assert corpo["enviados"] == 1
    assert [i["nome"] for i in corpo["ignorados"]] == ["virus.exe"]
    assert not (pasta_base / "4242" / "virus.exe").exists()
    assert fila.qsize() == 1


@pytest.mark.parametrize(
    "nome",
    [
        "../../fora.jpg",
        "..\\..\\fora.jpg",
        "C:\\Windows\\fora.jpg",
        "/etc/fora.jpg",
    ],
)
def test_upload_nao_escapa_da_pasta(client_logado, envios, db_roteado, nome):
    pasta_base, _ = envios
    db_roteado({"SELECT id FROM folders": {"fetchone": {"id": 7}}})

    _enviar(client_logado, _arquivo(nome))

    gravados = [os.path.join(r, f) for r, _, fs in os.walk(pasta_base.parent) for f in fs]
    assert gravados == [str(pasta_base / "4242" / "fora.jpg")]


def test_upload_nao_sobrescreve_arquivo_com_mesmo_nome(client_logado, envios, db_roteado):
    pasta_base, _ = envios
    db_roteado({"SELECT id FROM folders": {"fetchone": {"id": 7}}})

    _enviar(client_logado, _arquivo("a.jpg", b"primeiro"))
    r = _enviar(client_logado, _arquivo("a.jpg", b"segundo"))

    pasta = pasta_base / "4242"
    assert (pasta / "a.jpg").read_bytes() == b"primeiro"
    assert (pasta / "a (2).jpg").read_bytes() == b"segundo"
    assert r.get_json()["arquivos"] == ["a (2).jpg"]


def test_upload_funciona_no_modo_publico(client_logado, envios, db_roteado, modo_publico):
    db_roteado({"SELECT id FROM folders": {"fetchone": {"id": 7}}})
    assert _enviar(client_logado, _arquivo("a.jpg")).status_code == 200


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("foto.jpg", "foto.jpg"),
        ("  .oculto.jpg", "oculto.jpg"),
        ("a<b>c:d|e?f*.jpg", "abcdef.jpg"),
        ("CON.jpg", "_CON.jpg"),
        ("nome.", "nome"),
        ("", ""),
        ("..", ""),
    ],
)
def test_nome_seguro(app_module, nome, esperado):
    assert app_module._nome_seguro(nome) == esperado


def test_corpo_grande_demais_responde_json(client_logado, flask_app, envios):
    antes = flask_app.config.get("MAX_CONTENT_LENGTH")
    flask_app.config["MAX_CONTENT_LENGTH"] = 10
    try:
        r = _enviar(client_logado, _arquivo("a.jpg", b"x" * 1000))
    finally:
        flask_app.config["MAX_CONTENT_LENGTH"] = antes
    assert r.status_code == 413
    assert "error" in r.get_json()


def test_lista_de_pastas_marca_a_pasta_de_envios(app_module, envios):
    pasta_base, _ = envios
    linhas = [
        {
            "id": 1,
            "path": str(pasta_base / "4242"),
            "prioridades": '["tudo"]',
            "perfil_analise": "fast",
            "janela_processamento": "always",
        },
        {
            "id": 2,
            "path": r"C:\Users\Demo\Fotos",
            "prioridades": '["tudo"]',
            "perfil_analise": "fast",
            "janela_processamento": "always",
        },
    ]
    assert [p["enviados"] for p in app_module._folders_to_json(linhas)] == [True, False]
