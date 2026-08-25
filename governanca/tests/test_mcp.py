import json

import duckdb

import banco
import mcp_gov


def _chama(nome, argumentos, mid=7):
    return mcp_gov.despacha({"jsonrpc": "2.0", "id": mid,
                             "method": "tools/call",
                             "params": {"name": nome,
                                        "arguments": argumentos}})


def _texto(resposta):
    return resposta["result"]["content"][0]["text"]


def _semeia(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("decisao", "dec-000001",
                   {"titulo": "usar p-mediana", "just": "literatura",
                    "alt": [], "status": "vigente"})
    banco.registra("meta", "met-000001",
                   {"titulo": "m", "status": "aberta"})
    banco.registra("aresta", "dec-000001",
                   {"relacao": "atende", "destino": "met-000001"})
    banco._CON.close()
    banco._CON = None
    banco._CON_SOMENTE_LEITURA = None


def test_initialize_e_tools_list(tmp_repo):
    ini = mcp_gov.despacha({"jsonrpc": "2.0", "id": 1,
                            "method": "initialize", "params": {}})
    assert ini["result"]["protocolVersion"]
    assert mcp_gov.despacha({"jsonrpc": "2.0",
                             "method": "notifications/initialized"}) is None
    lista = mcp_gov.despacha({"jsonrpc": "2.0", "id": 2,
                              "method": "tools/list"})
    nomes = {t["name"] for t in lista["result"]["tools"]}
    assert nomes == {"consultar", "no", "vizinhos", "contexto", "auditoria"}


def test_consultar_select_funciona(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    r = _chama("consultar", {"sql": "SELECT count(*) AS n FROM decisao"})
    assert r["result"]["isError"] is False
    assert "1" in _texto(r)


def test_consultar_recusa_escrita(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    r = _chama("consultar", {"sql": "DELETE FROM evento"})
    assert r["result"]["isError"] is True


def test_no_aceita_prefixo(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    r = _chama("no", {"id": "dec-0"})
    assert "usar p-mediana" in _texto(r)


def test_contexto_e_vizinhos(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    assert "met-000001" in _texto(_chama("vizinhos", {"id": "dec-000001"}))
    assert "atende" in _texto(_chama("contexto", {"id": "dec-000001",
                                                  "raio": 2}))


def test_auditoria_retorna_selo(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    doc = json.loads(_texto(_chama("auditoria", {})))
    assert "selo" in doc


def test_metodo_desconhecido_da_erro(tmp_repo):
    r = mcp_gov.despacha({"jsonrpc": "2.0", "id": 9, "method": "prompts/list"})
    assert r["error"]["code"] == -32601


def test_tools_call_sem_params(tmp_repo):
    r = mcp_gov.despacha({"jsonrpc": "2.0", "id": 10, "method": "tools/call"})
    assert r["result"]["isError"] is True
    assert "ferramenta desconhecida" in _texto(r)


def test_nao_segura_lock_rw_apos_chamada(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    _chama("consultar", {"sql": "SELECT count(*) AS n FROM decisao"})
    assert banco._CON is None
    con = duckdb.connect(str(banco.DB))
    con.execute("INSERT INTO evento VALUES "
               "('evt-lockteste', now(), 'Teste', 'meta', 'met-999999', "
               "'{}')")
    con.close()


def test_no_com_registro_fantasma_da_erro_claro(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("aresta", "dec-fantasma",
                   {"relacao": "atende", "destino": "met-000001"})
    banco._CON.close()
    banco._CON = None
    banco._CON_SOMENTE_LEITURA = None
    r = _chama("no", {"id": "dec-fantasma"})
    assert r["result"]["isError"] is True
    assert "sem registro para" in _texto(r)


def test_servidor_json_invalido_nao_mata(tmp_repo):
    import subprocess
    import sys
    script_path = (
        __import__("pathlib").Path(__file__).resolve().parents[1] / "scripts" /
        "mcp_gov.py"
    )
    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    entrada = '{"json": "invalido"\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
    stdout, stderr = proc.communicate(entrada, timeout=5)
    linhas = [l for l in stdout.strip().split("\n") if l]
    assert len(linhas) >= 1
    import json
    ultima = json.loads(linhas[-1])
    assert ultima["id"] == 2
    assert "tools" in ultima["result"]
