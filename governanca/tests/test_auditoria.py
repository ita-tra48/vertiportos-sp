import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import auditoria
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def cenario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    roda("decisao", "Valor do tempo", "--just", "porque Y")
    roda("arquivo", "app/02-od.R")
    roda("ia", "--proposito", "formulacao", "--aceito", "integral",
         "--critica", "aceitei mas conferi a algebra do dual linha por linha")
    roda("ia", "--proposito", "codigo", "--aceito", "descarte",
         "--critica", "propos loop em R onde vetorizacao resolve, descartei")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    decs = [r[0] for r in con.execute(
        "SELECT id FROM decisao ORDER BY id").fetchall()]
    roda("liga", decs[0], "atende", met)
    return con


def test_rastreabilidade_conta_decisoes_com_meta(cenario):
    r = auditoria.rastreabilidade(cenario)
    assert r["decisoes_com_meta"] == pytest.approx(50.0)


def test_rastreabilidade_lista_orfaos(cenario):
    r = auditoria.rastreabilidade(cenario)
    assert len(r["orfaos"]) == 4


def test_arquivo_sem_decisao_conta_zero(cenario):
    r = auditoria.rastreabilidade(cenario)
    assert r["arquivos_com_decisao"] == pytest.approx(0.0)


def test_postura_critica(cenario):
    p = auditoria.postura(cenario)
    assert (p["integral"], p["parcial"], p["descarte"]) == (1, 0, 1)
    assert p["taxa_integral"] == pytest.approx(50.0)


def test_selo_vermelho_com_orfaos(cenario):
    m = auditoria.calcula(cenario)
    assert m["selo"][0] == "vermelho"
    assert any("órfão" in motivo for motivo in m["selo"][1])


def test_higiene_pega_tarefa_sem_prazo(cenario, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Estimar demanda", "--resp", "Ana")
    h = auditoria.higiene(banco.conecta())
    assert len(h["tarefas_incompletas"]) == 1


def test_cadencia_agrupa_por_semana(cenario):
    c = auditoria.cadencia(cenario)
    assert sum(n for _, n in c["registros_semana"]) == 7


def test_rastreabilidade_ignora_aresta_atende_para_decisao(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    roda("decisao", "Valor do tempo", "--just", "porque Y")
    con = banco.conecta()
    d1, d2 = [r[0] for r in con.execute(
        "SELECT id FROM decisao ORDER BY id").fetchall()]
    banco.registra("aresta", d1, {"relacao": "atende", "destino": d2})
    r = auditoria.rastreabilidade(banco.conecta())
    assert r["decisoes_com_meta"] == pytest.approx(0.0)


@pytest.fixture
def saudavel(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    dec = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("liga", dec, "atende", met)
    return con


def test_selo_verde_sem_motivos(saudavel):
    m = auditoria.calcula(saudavel)
    assert m["selo"] == ("verde", [])


def test_selo_vermelho_quando_taxa_integral_e_cem(saudavel, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    con = saudavel
    dec = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("ia", "--proposito", "codigo", "--aceito", "integral",
         "--critica", "conferi linha a linha antes de aceitar o trecho")
    ia = con.execute("SELECT id FROM ia").fetchone()[0]
    roda("liga", ia, "informa", dec)
    m = auditoria.calcula(banco.conecta())
    assert m["selo"][0] == "vermelho"
    assert any("aceite integral em 100%" in motivo for motivo in m["selo"][1])
    assert len(m["selo"][1]) >= 1


def test_higiene_indice_de_dias_aciona_o_selo(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    ts_antigo = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=20)
    met = banco.novo_id("met")
    dec = banco.novo_id("dec")
    banco.registra("meta", met, {"titulo": "M", "status": "aberta"})
    banco.registra("decisao", dec, {"titulo": "D", "just": "J"})
    banco.registra("aresta", dec, {"relacao": "atende", "destino": met})
    banco.registra("pendencia", banco.novo_id("pen"),
                   {"titulo": "Confirmar cobertura", "status": "aberta"},
                   ts=ts_antigo)
    con = banco.conecta()
    h = auditoria.higiene(con)
    assert len(h["pendencias_velhas"]) == 1
    assert h["pendencias_velhas"][0][3] > auditoria.LIMITE_SELO_DIAS
    m = auditoria.calcula(con)
    assert m["selo"][0] == "vermelho"
    assert any("pendência" in motivo for motivo in m["selo"][1])
