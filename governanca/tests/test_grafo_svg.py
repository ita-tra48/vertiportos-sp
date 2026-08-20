import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov
import grafo


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def cenario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    dec = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("liga", dec, "atende", met)
    return con, met, dec


def test_coleta_nos_e_arestas(cenario):
    con, met, dec = cenario
    nos, arestas = grafo.coleta(con)
    assert {n["id"] for n in nos} == {met, dec}
    assert arestas == [{"origem": dec, "relacao": "atende", "destino": met}]


def test_svg_e_determinista(cenario):
    con, _, _ = cenario
    assert grafo.svg(con) == grafo.svg(con)


def test_svg_tem_link_por_no(cenario):
    con, met, dec = cenario
    saida = grafo.svg(con)
    assert f'href="trilha.html#{met}"' in saida
    assert f'href="trilha.html#{dec}"' in saida


def test_svg_escapa_rotulo(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", 'Meta com <script> & "aspas"')
    saida = grafo.svg(banco.conecta())
    assert "<script>" not in saida
    assert "&lt;script&gt;" in saida


def test_svg_vazio_nao_quebra(tmp_repo):
    saida = grafo.svg(banco.conecta())
    assert saida.startswith("<svg")
