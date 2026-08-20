import re
import subprocess
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


@pytest.fixture
def bando_arquivo(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("arquivo", "a.R", "--desc", "A")
    roda("arquivo", "b.R", "--desc", "B")
    roda("arquivo", "c.R", "--desc", "C")
    con = banco.conecta()
    ids = [r[0] for r in con.execute(
        "SELECT id FROM arquivo ORDER BY id").fetchall()]
    roda("liga", ids[0], "produz", ids[2])
    return con, ids


def test_svg_curva_desvia_no_mesmo_bando(bando_arquivo):
    con, ids = bando_arquivo
    primeiro = grafo.svg(con)
    pos = grafo.posiciona(grafo.coleta(con)[0])
    x0, y = pos[ids[0]]
    x1, y1 = pos[ids[2]]
    assert y1 == y
    casamento = re.search(
        rf'M {x0} {y} C {x0} (-?[\d.]+) {x1} (-?[\d.]+) {x1} {y}', primeiro)
    assert casamento is not None
    assert float(casamento.group(1)) != y
    assert float(casamento.group(2)) != y
    assert grafo.svg(con) == primeiro


def test_svg_determinista_entre_processos(cenario, tmp_repo):
    con, _, _ = cenario
    primeiro = grafo.svg(con)
    con.close()
    banco._CON = None
    banco._CON_SOMENTE_LEITURA = None
    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    codigo = f"""
import sys
sys.path.insert(0, {scripts!r})
from pathlib import Path
import banco, grafo
banco.RAIZ = Path({str(tmp_repo)!r})
banco.DB = banco.RAIZ / "governanca" / "projeto.duckdb"
banco.DUMP = banco.RAIZ / "governanca" / "dump.sql"
banco.SCHEMA = banco.RAIZ / "governanca" / "schemas" / "schema.sql"
print(grafo.svg(banco.conecta()), end="")
"""
    resultado = subprocess.run([sys.executable, "-c", codigo],
                               capture_output=True, text=True, check=True)
    assert resultado.stdout == primeiro
