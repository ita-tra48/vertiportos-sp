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


def test_dados_nos_traz_campos_do_payload(cenario):
    con, met, dec = cenario
    nos, arestas = grafo.dados_nos(con)
    achado = next(n for n in nos if n["id"] == dec)
    assert achado["tipo"] == "decisao"
    assert achado["titulo"] == "Recorte metropolitano"
    assert achado["autor"] == "Gustavo"
    assert achado["status"] == "vigente"
    assert achado["campos"]["just"] == "porque X"
    assert arestas == [{"origem": dec, "relacao": "atende", "destino": met}]


def test_dados_nos_marca_concluido_sem_pendencia(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Baixar OD", "--resp", "Ana")
    con = banco.conecta()
    tid = con.execute("SELECT id FROM tarefa").fetchone()[0]
    roda("fecha", tid, "--resolucao", "feito")
    nos, _ = grafo.dados_nos(banco.conecta())
    achado = next(n for n in nos if n["id"] == tid)
    assert achado["status"] == "feita"
    assert achado["concluido"] is True


def test_dados_nos_pendencia_aberta_apaga_concluido(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Baixar OD", "--resp", "Ana")
    con = banco.conecta()
    tid = con.execute("SELECT id FROM tarefa").fetchone()[0]
    roda("fecha", tid, "--resolucao", "feito")
    roda("pendencia", "Falta aprovacao")
    pid = banco.conecta().execute("SELECT id FROM pendencia").fetchone()[0]
    roda("liga", pid, "bloqueia", tid)
    nos, _ = grafo.dados_nos(banco.conecta())
    achado = next(n for n in nos if n["id"] == tid)
    assert achado["concluido"] is False


def test_json_dados_e_ordenado_e_escapa_fechamento_de_script(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Meta </script> maliciosa")
    texto = grafo.json_dados(banco.conecta())
    assert "</script>" not in texto
    assert "<\\/script>" in texto


def test_pagina_home_traz_dados_e_legenda(cenario):
    con, met, dec = cenario
    html = grafo.pagina_home(con)
    assert f'"id": "{met}"' in html
    assert f'"id": "{dec}"' in html
    for tipo in grafo.FAIXAS:
        assert f'data-tipo="{tipo}"' in html
    assert 'data-status="todos"' in html
    assert 'data-status="abertos"' in html
    assert 'data-status="concluidos"' in html
    assert "grafo-brilho" in html


def test_pagina_home_e_determinista(cenario):
    con, _, _ = cenario
    assert grafo.pagina_home(con) == grafo.pagina_home(con)


def test_pagina_home_no_e_acessivel_por_teclado(cenario):
    con, _, _ = cenario
    html = grafo.pagina_home(con)
    assert "createElementNS(NS, 'title')" in html
    assert "setAttribute('tabindex', '0')" in html
    assert "setAttribute('role', 'button')" in html
    assert "setAttribute('aria-label'" in html
    assert "e.key === 'Enter'" in html


def test_aplica_filtros_esconde_tooltip(cenario):
    con, _, _ = cenario
    html = grafo.pagina_home(con)
    trecho = html[html.index("function aplicaFiltros(){"):]
    assert trecho.split("\n")[1].strip() == "escondeTooltip();"


def test_rotulo_oculto_por_padrao_no_css():
    assert ".grafo-rotulo{display:none}" in grafo.ESTILO_HOME


def test_rotulo_aparece_ao_selecionar(cenario):
    con, _, _ = cenario
    html = grafo.pagina_home(con)
    assert "grafo-mostra-rotulo" in html
    assert "class', 'grafo-rotulo'" in html


def test_deep_link_seleciona_no_id_da_url(cenario):
    con, _, _ = cenario
    html = grafo.pagina_home(con)
    assert "window.location.hash" in html
    assert "selecionaSemNavegar" in html


def test_no_interno_fica_fora_do_coleta(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("decisao", "Decisao interna", "--just", "porque X")
    con = banco.conecta()
    did = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("patch", did, "interno=true")
    con = banco.conecta()
    nos, _ = grafo.coleta(con)
    assert did not in {n["id"] for n in nos}


def test_no_interno_fica_fora_do_dados_nos(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("decisao", "Decisao interna", "--just", "porque X")
    con = banco.conecta()
    did = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("patch", did, "interno=true")
    con = banco.conecta()
    nos, _ = grafo.dados_nos(con)
    assert did not in {n["id"] for n in nos}
    assert did not in grafo.json_dados(con)
