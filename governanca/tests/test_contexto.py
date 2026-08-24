import json

import banco
import contexto
import gov


def _semeia(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("meta", "met-000001",
                   {"titulo": "meta um", "status": "aberta"})
    banco.registra("tarefa", "tar-000001",
                   {"titulo": "tarefa um", "resp": "Ana", "status": "aberta"})
    banco.registra("decisao", "dec-000001",
                   {"titulo": "decisao um", "just": "porque sim", "alt": [],
                    "status": "vigente"})
    banco.registra("fonte", "fon-000001",
                   {"titulo": "fonte um", "origem": "https://x",
                    "limitacoes": "poucas"})
    banco.registra("arquivo", "arq-000001",
                   {"titulo": "app/01-carrega.R", "desc": None})
    banco.registra("aresta", "met-000001",
                   {"relacao": "tem", "destino": "tar-000001"})
    banco.registra("aresta", "dec-000001",
                   {"relacao": "atende", "destino": "met-000001"})
    banco.registra("aresta", "dec-000001",
                   {"relacao": "usa", "destino": "fon-000001"})
    banco.registra("aresta", "arq-000001",
                   {"relacao": "deriva", "destino": "dec-000001"})


def test_raio_1_traz_so_vizinhos_diretos(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    nos, arestas = contexto.vizinhanca(banco.conecta(), "met-000001", 1)
    assert nos == {"met-000001", "tar-000001", "dec-000001"}
    assert ("met-000001", "tem", "tar-000001") in arestas
    assert ("dec-000001", "usa", "fon-000001") not in arestas


def test_raio_2_alcanca_fonte_e_arquivo(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    nos, arestas = contexto.vizinhanca(banco.conecta(), "met-000001", 2)
    assert {"fon-000001", "arq-000001"} <= nos
    assert ("dec-000001", "usa", "fon-000001") in arestas


def test_no_isolado_tem_vizinhanca_vazia(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("pendencia", "pen-000001",
                   {"titulo": "solta", "status": "aberta"})
    nos, arestas = contexto.vizinhanca(banco.conecta(), "pen-000001", 3)
    assert nos == {"pen-000001"}
    assert arestas == []


def test_cli_markdown_lista_registros_e_arquivos(tmp_repo, monkeypatch, capsys):
    _semeia(monkeypatch)
    assert gov.main(["contexto", "met-000001", "--raio", "2"]) == 0
    saida = capsys.readouterr().out
    assert "met-000001" in saida
    assert "porque sim" in saida
    assert "app/01-carrega.R" in saida
    assert "—tem→" in saida


def test_cli_json_estruturado(tmp_repo, monkeypatch, capsys):
    _semeia(monkeypatch)
    assert gov.main(["contexto", "dec-000001", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["centro"] == "dec-000001"
    ids = {r["id"] for r in doc["registros"]}
    assert "met-000001" in ids
    assert {"origem", "relacao", "destino"} <= set(doc["arestas"][0])


def test_cli_aceita_prefixo_e_rejeita_desconhecido(tmp_repo, monkeypatch, capsys):
    _semeia(monkeypatch)
    assert gov.main(["contexto", "met-0"]) == 0
    assert gov.main(["contexto", "zzz-999999"]) == 2
