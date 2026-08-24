import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


def test_meta_grava(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("meta", "Localizar vertiportos na RMSP") == 0
    con = banco.conecta()
    assert con.execute("SELECT titulo FROM meta").fetchone() == (
        "Localizar vertiportos na RMSP",)


def test_ia_sem_critica_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("ia", "--proposito", "formulacao", "--aceito", "parcial")
    con = banco.conecta()
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (0,)


def test_ia_com_critica_curta_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("ia", "--proposito", "formulacao", "--aceito", "integral",
                "--critica", "ok") == 2
    con = banco.conecta()
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (0,)


def test_ia_valida_grava(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("ia", "--proposito", "formulacao", "--aceito", "parcial",
                "--critica", "A sugestao ignorou a restricao de capacidade "
                             "do vertiporto e assumiu frota infinita.") == 0
    con = banco.conecta()
    assert con.execute("SELECT aceito FROM ia").fetchone() == ("parcial",)


def test_decisao_sem_justificativa_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("decisao", "Valor do tempo = R$ 50/h")


def test_fonte_sem_limitacoes_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("fonte", "Pesquisa OD Metro", "--origem", "https://x")


def test_tarefa_sem_responsavel_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("tarefa", "Estimar demanda capturavel")


def test_experimento_guarda_parametros(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("experimento", "--variante", "cobertura", "--p", "p=8",
                "--p", "raio=5", "--obj", "12345") == 0
    con = banco.conecta()
    variante, parametros, obj = con.execute(
        "SELECT variante, parametros, obj FROM experimento").fetchone()
    assert variante == "cobertura"
    assert obj == 12345.0
    assert '"p":"8"' in parametros.replace(" ", "")


def test_experimento_obj_invalido_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("experimento", "--variante", "cobertura",
                "--obj", "12,345") == 2
    con = banco.conecta()
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (0,)


def test_experimento_sem_numeros_grava(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("experimento", "--variante", "cobertura") == 0
    con = banco.conecta()
    obj = con.execute("SELECT obj FROM experimento").fetchone()[0]
    assert obj is None


def test_pares_chave_vazia_e_recusada():
    with pytest.raises(SystemExit):
        gov._pares(["=5"])


def test_pares_chave_duplicada_e_recusada():
    with pytest.raises(SystemExit):
        gov._pares(["p=1", "p=2"])


def test_pares_valor_com_igual_e_preservado():
    assert gov._pares(["formula=a=b"]) == {"formula": "a=b"}


def test_decisao_com_alternativas_multiplas(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("decisao", "Formulacao p-mediana", "--just", "porque X",
                "--alt", "cobertura maxima", "--alt", "custo fixo") == 0
    con = banco.conecta()
    alt = con.execute("SELECT alternativas FROM decisao").fetchone()[0]
    assert "cobertura maxima" in alt and "custo fixo" in alt
