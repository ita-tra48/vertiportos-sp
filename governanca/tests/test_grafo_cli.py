import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def semeado(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    dec = con.execute("SELECT id FROM decisao").fetchone()[0]
    return met, dec


def test_liga_cria_aresta(semeado):
    met, dec = semeado
    assert roda("liga", dec, "atende", met) == 0
    con = banco.conecta()
    assert con.execute(
        "SELECT origem, relacao, destino FROM aresta").fetchone() == (
        dec, "atende", met)


def test_liga_recusa_relacao_fora_do_vocabulario(semeado):
    met, dec = semeado
    with pytest.raises(SystemExit):
        roda("liga", dec, "inventada", met)


def test_liga_aceita_prefixo(semeado):
    met, dec = semeado
    assert roda("liga", dec[:6], "atende", met[:6]) == 0
    con = banco.conecta()
    assert con.execute("SELECT destino FROM aresta").fetchone() == (met,)


def test_fecha_muda_status_sem_apagar_historia(semeado, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    con = banco.conecta()
    roda("tarefa", "Baixar OD", "--resp", "Ana")
    tar = con.execute("SELECT id FROM tarefa").fetchone()[0]
    assert roda("fecha", tar) == 0
    assert con.execute("SELECT status FROM tarefa WHERE id = ?",
                       [tar]).fetchone() == ("feita",)
    assert con.execute("SELECT count(*) FROM evento WHERE entidade_id = ?",
                       [tar]).fetchone() == (2,)


def test_patch_mescla_campos(semeado, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    met, dec = semeado
    assert roda("patch", dec, "just=porque Y") == 0
    con = banco.conecta()
    titulo, just = con.execute(
        "SELECT titulo, justificativa FROM decisao WHERE id = ?",
        [dec]).fetchone()
    assert titulo == "Recorte metropolitano"
    assert just == "porque Y"


def test_consulta_recusa_escrita(semeado):
    with pytest.raises(SystemExit):
        roda("consulta", "DELETE FROM evento")


def test_consulta_select_funciona(semeado, capsys):
    assert roda("consulta", "SELECT count(*) FROM decisao") == 0
    assert "1" in capsys.readouterr().out


def test_consulta_recusa_leitura_de_arquivo(semeado, tmp_repo, capsys):
    alvo = tmp_repo / "governanca" / "schemas" / "schema.sql"
    with pytest.raises(duckdb.Error):
        roda("consulta", f"SELECT * FROM read_text('{alvo}')")
    assert "CREATE TABLE" not in capsys.readouterr().out


def test_consulta_recusa_glob(semeado):
    with pytest.raises(duckdb.Error):
        roda("consulta", "SELECT * FROM glob('*')")


def test_registra_e_rebuild_funcionam_apos_consulta(semeado, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("consulta", "SELECT count(*) FROM decisao")
    assert roda("pendencia", "Confirmar cobertura de dados") == 0
    con = banco.conecta()
    assert con.execute("SELECT count(*) FROM pendencia").fetchone() == (1,)
    assert roda("rebuild") == 0


def test_status_lista_orfaos(semeado, capsys):
    met, dec = semeado
    roda("liga", dec, "atende", met)
    roda("pendencia", "Confirmar cobertura de dados")
    con = banco.conecta()
    pen = con.execute("SELECT id FROM pendencia").fetchone()[0]
    roda("status")
    saida = capsys.readouterr().out
    assert "orfaos" in saida.lower()
    assert met not in saida
    assert dec not in saida
    assert pen in saida


def test_orfaos_ignora_null_de_aresta_malformada(semeado):
    met, dec = semeado
    banco.registra("aresta", dec, {"relacao": "atende", "destino": None})
    con = banco.conecta()
    orfaos = gov._orfaos(con)
    assert met in orfaos
    assert dec not in orfaos
