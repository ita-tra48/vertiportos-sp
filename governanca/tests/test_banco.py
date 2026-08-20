import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco


def test_novo_id_tem_prefixo_e_seis_chars():
    i = banco.novo_id("dec")
    assert i.startswith("dec-")
    assert len(i) == len("dec-") + 6
    assert set(i.split("-")[1]) <= set("0123456789abcdefghijklmnopqrstuvwxyz")


def test_novo_id_nao_repete():
    assert len({banco.novo_id("dec") for _ in range(500)}) == 500


def test_registra_e_le_de_volta(tmp_repo):
    eid = banco.novo_id("dec")
    banco.registra("decisao", eid, {"titulo": "Motor em Python", "just": "porque"},
                   autor="Gustavo")
    con = banco.conecta()
    linha = con.execute(
        "SELECT titulo, justificativa, criado_por FROM decisao WHERE id = ?", [eid]
    ).fetchone()
    assert linha == ("Motor em Python", "porque", "Gustavo")


def test_dump_e_append_only(tmp_repo):
    banco.registra("meta", banco.novo_id("met"), {"titulo": "A"}, autor="G")
    antes = banco.DUMP.read_text()
    banco.registra("meta", banco.novo_id("met"), {"titulo": "B"}, autor="G")
    depois = banco.DUMP.read_text()
    assert depois.startswith(antes)
    assert depois.count("INSERT INTO evento") == 2


def test_rebuild_reconstroi_do_dump(tmp_repo):
    eid = banco.novo_id("fon")
    banco.registra("fonte", eid, {"titulo": "OD Metro", "limitacoes": "2017"},
                   autor="G")
    banco.DB.unlink()
    con = banco.conecta()
    assert con.execute("SELECT nome FROM fonte WHERE id = ?", [eid]).fetchone() == (
        "OD Metro",
    )


def test_ultimo_evento_ganha(tmp_repo):
    eid = banco.novo_id("tar")
    banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                   "status": "aberta"}, autor="G")
    banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                   "status": "feita"}, autor="G")
    con = banco.conecta()
    assert con.execute("SELECT status FROM tarefa WHERE id = ?", [eid]).fetchone() == (
        "feita",
    )
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (2,)


def test_resolve_por_prefixo(tmp_repo):
    eid = banco.novo_id("dec")
    banco.registra("decisao", eid, {"titulo": "T", "just": "J"}, autor="G")
    assert banco.resolve(eid[:6]) == eid


def test_resolve_recusa_inexistente(tmp_repo):
    import pytest
    with pytest.raises(ValueError):
        banco.resolve("dec-zzzzzz")


def test_autor_atual_usa_env(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Fulano")
    assert banco.autor_atual() == "Fulano"
