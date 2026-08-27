import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def nos(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("tarefa", "Estimar demanda", "--resp", "Ana")
    roda("pendencia", "Confirmar cobertura")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    roda("decisao", "Valor do tempo", "--just", "porque Y")
    roda("fonte", "ANAC VRA", "--origem", "ANAC", "--limitacoes", "amostral")
    roda("arquivo", "app/01-carrega.R")
    roda("arquivo", "app/02-od.R")
    roda("referencia", "Ortuzar & Willumsen", "--doi", "10.0/x")
    roda("experimento", "--variante", "base")
    roda("ia", "--proposito", "codigo", "--aceito", "parcial",
         "--critica", "revisei e ajustei os parametros do modelo antes")
    con = banco.conecta()

    def id_de(tabela, titulo=None, coluna="titulo"):
        if titulo is None:
            return con.execute(f"SELECT id FROM {tabela} LIMIT 1").fetchone()[0]
        return con.execute(f"SELECT id FROM {tabela} WHERE {coluna} = ?",
                           [titulo]).fetchone()[0]

    return {
        "meta": id_de("meta"),
        "tarefa": id_de("tarefa"),
        "pendencia": id_de("pendencia"),
        "decisao1": id_de("decisao", "Recorte metropolitano"),
        "decisao2": id_de("decisao", "Valor do tempo"),
        "fonte": id_de("fonte", "ANAC VRA", "nome"),
        "arquivo1": id_de("arquivo", "app/01-carrega.R", "caminho"),
        "arquivo2": id_de("arquivo", "app/02-od.R", "caminho"),
        "referencia": id_de("referencia"),
        "experimento": id_de("experimento"),
        "ia": id_de("ia"),
    }


PARES_VALIDOS = [
    ("tem", "meta", "tarefa"),
    ("atende", "decisao1", "meta"),
    ("usa", "decisao1", "fonte"),
    ("usa", "decisao1", "referencia"),
    ("produz", "arquivo1", "arquivo2"),
    ("justifica", "experimento", "decisao1"),
    ("apoia", "experimento", "arquivo1"),
    ("deriva", "arquivo1", "decisao1"),
    ("bloqueia", "pendencia", "tarefa"),
    ("bloqueia", "pendencia", "meta"),
    ("informa", "ia", "decisao1"),
    ("informa", "ia", "arquivo1"),
    ("informa", "ia", "tarefa"),
    ("refina", "decisao1", "decisao2"),
    ("afeta", "pendencia", "decisao1"),
]


@pytest.mark.parametrize("relacao,chave_origem,chave_destino", PARES_VALIDOS)
def test_liga_aceita_par_valido(nos, relacao, chave_origem, chave_destino):
    origem = nos[chave_origem]
    destino = nos[chave_destino]
    assert roda("liga", origem, relacao, destino) == 0
    con = banco.conecta()
    assert con.execute(
        "SELECT count(*) FROM aresta WHERE origem = ? AND relacao = ? "
        "AND destino = ?", [origem, relacao, destino]).fetchone()[0] == 1


def test_liga_recusa_destino_de_tipo_errado(nos):
    dec1, dec2 = nos["decisao1"], nos["decisao2"]
    assert roda("liga", dec1, "atende", dec2) == 2
    con = banco.conecta()
    assert con.execute(
        "SELECT count(*) FROM aresta").fetchone()[0] == 0


def test_liga_recusa_origem_de_tipo_errado(nos):
    arquivo, meta = nos["arquivo1"], nos["meta"]
    assert roda("liga", arquivo, "atende", meta) == 2
    con = banco.conecta()
    assert con.execute(
        "SELECT count(*) FROM aresta").fetchone()[0] == 0


def test_liga_recusa_refina_com_destino_de_tipo_errado(nos):
    decisao, arquivo = nos["decisao1"], nos["arquivo1"]
    assert roda("liga", decisao, "refina", arquivo) == 2
    con = banco.conecta()
    assert con.execute(
        "SELECT count(*) FROM aresta").fetchone()[0] == 0


def test_liga_recusa_afeta_com_origem_de_tipo_errado(nos):
    tarefa, decisao = nos["tarefa"], nos["decisao1"]
    assert roda("liga", tarefa, "afeta", decisao) == 2
    con = banco.conecta()
    assert con.execute(
        "SELECT count(*) FROM aresta").fetchone()[0] == 0
