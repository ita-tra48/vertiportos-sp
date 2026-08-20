import json
import os
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco


class _ConexaoComFalhaNoInsert:
    def __init__(self, real):
        self._real = real

    def execute(self, stmt, *a, **kw):
        if stmt.startswith("INSERT INTO evento"):
            raise RuntimeError("falha simulada")
        return self._real.execute(stmt, *a, **kw)


class _CaminhoComFalhaNoAppend:
    def __init__(self, real):
        self._real = real

    def exists(self):
        return self._real.exists()

    def stat(self):
        return self._real.stat()

    @property
    def parent(self):
        return self._real.parent

    def open(self, mode="r", encoding=None):
        if mode == "a":
            raise OSError("falha simulada no append")
        return self._real.open(mode, encoding=encoding)

    def read_text(self):
        return self._real.read_text()


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
    con = banco.conecta()
    for _ in range(30):
        eid = banco.novo_id("tar")
        banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                       "status": "aberta"}, autor="G")
        banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                       "status": "feita"}, autor="G")
        assert con.execute(
            "SELECT status FROM tarefa WHERE id = ?", [eid]
        ).fetchone() == ("feita",)


def test_ultimo_evento_ganha_com_ts_explicito_no_mesmo_segundo(tmp_repo):
    eid = banco.novo_id("tar")
    base = datetime(2026, 1, 1, 12, 0, 0)
    banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                   "status": "aberta"}, autor="G",
                   ts=base.replace(microsecond=1))
    banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                   "status": "feita"}, autor="G",
                   ts=base.replace(microsecond=2))
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
    with pytest.raises(ValueError):
        banco.resolve("dec-zzzzzz")


def test_autor_atual_usa_env(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Fulano")
    assert banco.autor_atual() == "Fulano"


def test_dump_sobrevive_a_falha_no_banco(tmp_repo):
    eid = banco.novo_id("dec")
    antes = banco.DUMP.read_text() if banco.DUMP.exists() else ""
    proxy = _ConexaoComFalhaNoInsert(banco.conecta())
    original_conecta = banco.conecta
    banco.conecta = lambda somente_leitura=False: proxy
    try:
        with pytest.raises(RuntimeError):
            banco.registra("decisao", eid, {"titulo": "T", "just": "J"}, autor="G")
    finally:
        banco.conecta = original_conecta
    depois = banco.DUMP.read_text() if banco.DUMP.exists() else ""
    assert depois == antes
    con = banco.conecta()
    assert con.execute(
        "SELECT titulo FROM decisao WHERE id = ?", [eid]
    ).fetchone() is None


def test_dump_continua_append_only_apos_falha(tmp_repo):
    banco.registra("meta", banco.novo_id("met"), {"titulo": "A"}, autor="G")
    antes = banco.DUMP.read_text()
    proxy = _ConexaoComFalhaNoInsert(banco.conecta())
    original_conecta = banco.conecta
    banco.conecta = lambda somente_leitura=False: proxy
    try:
        with pytest.raises(RuntimeError):
            banco.registra("meta", banco.novo_id("met"), {"titulo": "B"}, autor="G")
    finally:
        banco.conecta = original_conecta
    depois = banco.DUMP.read_text()
    assert depois == antes
    assert depois.count("INSERT INTO evento") == 1


def test_colisao_de_evento_id_nao_deixa_rastro(tmp_repo, monkeypatch):
    real_novo_id = banco.novo_id
    monkeypatch.setattr(banco, "novo_id",
                        lambda prefixo: "evt-fixado" if prefixo == "evt"
                        else real_novo_id(prefixo))
    eid1 = banco.novo_id("dec")
    banco.registra("decisao", eid1, {"titulo": "Primeiro", "just": "J"}, autor="G")
    antes = banco.DUMP.read_text()
    eid2 = banco.novo_id("dec")
    with pytest.raises(duckdb.Error):
        banco.registra("decisao", eid2, {"titulo": "Segundo", "just": "J2"}, autor="G")
    depois = banco.DUMP.read_text()
    assert depois == antes
    con = banco.conecta()
    assert con.execute(
        "SELECT titulo FROM decisao WHERE id = ?", [eid2]
    ).fetchone() is None
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (1,)


def test_falha_no_append_do_dump_desfaz_o_banco(tmp_repo, monkeypatch):
    eid = banco.novo_id("tar")
    caminho_real = banco.DUMP
    monkeypatch.setattr(banco, "DUMP", _CaminhoComFalhaNoAppend(caminho_real))
    with pytest.raises(OSError):
        banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                       "status": "aberta"}, autor="G")
    monkeypatch.setattr(banco, "DUMP", caminho_real)
    assert not banco.DUMP.exists()
    con = banco.conecta()
    assert con.execute(
        "SELECT status FROM tarefa WHERE id = ?", [eid]
    ).fetchone() is None
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (0,)


def test_conecta_somente_leitura_apos_escrita_nao_e_gravavel(tmp_repo):
    banco.registra("meta", banco.novo_id("met"), {"titulo": "A"}, autor="G")
    con_ro = banco.conecta(somente_leitura=True)
    with pytest.raises(duckdb.Error):
        con_ro.execute(
            "INSERT INTO evento VALUES "
            "('x', '2020-01-01 00:00:00', 'G', 'meta', 'met-xxxxxx', '{}')"
        )


def test_conecta_escrita_apos_somente_leitura_funciona(tmp_repo):
    banco.conecta(somente_leitura=True)
    eid = banco.novo_id("met")
    banco.registra("meta", eid, {"titulo": "B"}, autor="G")
    con = banco.conecta()
    assert con.execute(
        "SELECT titulo FROM meta WHERE id = ?", [eid]
    ).fetchone() == ("B",)
