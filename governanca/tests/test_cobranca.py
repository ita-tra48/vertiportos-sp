import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import cobranca
import gov


def roda(*argv):
    return gov.main(list(argv))


def dia(delta):
    return (date.today() + timedelta(days=delta)).isoformat()


def test_faixa_separa_atrasada_hoje_semana_e_depois():
    hoje = date(2026, 9, 4)
    assert cobranca.faixa(date(2026, 9, 3), hoje) == "atrasada"
    assert cobranca.faixa(date(2026, 9, 4), hoje) == "hoje"
    assert cobranca.faixa(date(2026, 9, 10), hoje) == "semana"
    assert cobranca.faixa(date(2026, 9, 30), hoje) == "depois"
    assert cobranca.faixa(None, hoje) == "sem prazo"


def test_coleta_agrupa_por_responsavel_e_ignora_fechada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Montar candidatos", "--resp", "Italo", "--prazo", dia(-2))
    roda("tarefa", "Escrever formulacao", "--resp", "Carlos", "--prazo", dia(3))
    roda("tarefa", "Ja feita", "--resp", "Italo", "--prazo", dia(1))
    con = banco.conecta()
    feita = con.execute(
        "SELECT id FROM tarefa WHERE titulo = 'Ja feita'").fetchone()[0]
    roda("fecha", feita, "--resolucao", "pronto")
    por_resp = cobranca.coleta(banco.conecta(), date.today())
    assert sorted(por_resp) == ["Carlos", "Italo"]
    assert len(por_resp["Italo"]) == 1
    assert por_resp["Italo"][0]["faixa"] == "atrasada"
    assert por_resp["Carlos"][0]["faixa"] == "semana"


def test_coleta_marca_tarefa_travada_por_pendencia(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Montar candidatos", "--resp", "Italo", "--prazo", dia(1))
    roda("pendencia", "Falta a norma de vertiporto")
    con = banco.conecta()
    tid = con.execute("SELECT id FROM tarefa").fetchone()[0]
    pid = con.execute("SELECT id FROM pendencia").fetchone()[0]
    roda("liga", pid, "bloqueia", tid)
    por_resp = cobranca.coleta(banco.conecta(), date.today())
    assert por_resp["Italo"][0]["travas"] == ["Falta a norma de vertiporto"]


def test_atrasada_vem_antes_e_aparece_no_assunto(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Depois", "--resp", "Italo", "--prazo", dia(4))
    roda("tarefa", "Vencida", "--resp", "Italo", "--prazo", dia(-1))
    tarefas = cobranca.coleta(banco.conecta(), date.today())["Italo"]
    assert [t["titulo"] for t in tarefas] == ["Vencida", "Depois"]
    assert "atrasada" in cobranca.assunto(tarefas)
    assert cobranca.TITULOS["atrasada"] in cobranca.corpo("Italo", tarefas)


def test_quem_nao_tem_tarefa_nao_recebe(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Montar candidatos", "--resp", "Italo", "--prazo", dia(1))
    por_resp = cobranca.coleta(banco.conecta(), date.today())
    msgs, sem_email = cobranca.mensagens(
        por_resp, {"Italo": "italo@exemplo.com", "Carlos": "carlos@exemplo.com"})
    assert [m["para"] for m in msgs] == ["italo@exemplo.com"]
    assert sem_email == []


def test_responsavel_sem_email_vira_aviso(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Montar candidatos", "--resp", "Italo", "--prazo", dia(1))
    por_resp = cobranca.coleta(banco.conecta(), date.today())
    msgs, sem_email = cobranca.mensagens(por_resp, {})
    assert msgs == []
    assert sem_email == ["Italo"]


def test_sem_tarefa_aberta_nao_envia_nada(tmp_repo, monkeypatch, capsys):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    monkeypatch.setenv("EMAILS_JSON", json.dumps({"Italo": "i@exemplo.com"}))
    monkeypatch.setattr(cobranca, "envia", _explode)
    assert cobranca.main([]) == 0
    assert "nada a enviar" in capsys.readouterr().out


def test_modo_seco_imprime_e_nao_envia(tmp_repo, monkeypatch, capsys):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Montar candidatos", "--resp", "Italo", "--prazo", dia(-1))
    monkeypatch.setenv("EMAILS_JSON", json.dumps({"Italo": "i@exemplo.com"}))
    monkeypatch.setattr(cobranca, "envia", _explode)
    assert cobranca.main(["--seco"]) == 0
    saida = capsys.readouterr().out
    assert "i@exemplo.com" in saida
    assert "Montar candidatos" in saida


def test_sem_credencial_falha_sem_tentar_conectar(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Montar candidatos", "--resp", "Italo", "--prazo", dia(-1))
    monkeypatch.setenv("EMAILS_JSON", json.dumps({"Italo": "i@exemplo.com"}))
    monkeypatch.delenv("SMTP_USUARIO", raising=False)
    monkeypatch.delenv("SMTP_SENHA", raising=False)
    monkeypatch.setattr(cobranca, "envia", _explode)
    assert cobranca.main([]) == 2


def _explode(*_a, **_k):
    raise AssertionError("nao devia enviar email")


def test_email_casa_com_responsavel_de_grafia_diferente():
    emails = {"gustavo vidal": "g@exemplo.com"}
    assert cobranca.destinos("Gustavo  Vidal", emails) == ["g@exemplo.com"]
    assert cobranca.destinos("Carlos", emails) == []


def test_responsavel_coletivo_aceita_varios_enderecos():
    emails = {"grupo": "a@exemplo.com, b@exemplo.com",
              "Italo": ["i@exemplo.com"]}
    assert cobranca.destinos("grupo", emails) == ["a@exemplo.com",
                                                  "b@exemplo.com"]
    assert cobranca.destinos("Italo", emails) == ["i@exemplo.com"]


def test_assunto_concorda_no_singular_e_no_plural():
    uma = [{"faixa": "atrasada"}]
    duas = [{"faixa": "atrasada"}, {"faixa": "atrasada"}]
    assert cobranca.assunto(uma).endswith("1 tarefa sua em aberto, 1 atrasada")
    assert cobranca.assunto(duas).endswith("2 tarefas suas em aberto, "
                                           "2 atrasadas")
