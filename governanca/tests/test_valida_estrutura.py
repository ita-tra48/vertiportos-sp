import subprocess

import pytest

import banco
import valida_estrutura


def _git(raiz, *args):
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


def test_scripts_de_app_devem_ser_numerados(tmp_repo):
    app = tmp_repo / "app"
    app.mkdir()
    (app / "01-carrega.R").write_text("x <- 1\n")
    (app / "modelo.R").write_text("x <- 1\n")
    (app / "R").mkdir()
    (app / "R" / "gov.R").write_text("x <- 1\n")
    assert valida_estrutura.scripts_fora_do_padrao(tmp_repo) == ["modelo.R"]


def test_bruto_alterado_no_diff(tmp_repo):
    _git(tmp_repo, "init", "-b", "main")
    _git(tmp_repo, "config", "user.name", "T")
    _git(tmp_repo, "config", "user.email", "t@t")
    bruto = tmp_repo / "dados" / "bruto"
    bruto.mkdir(parents=True)
    (bruto / ".gitkeep").write_text("")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-m", "base")
    _git(tmp_repo, "checkout", "-b", "tarefa/x")
    (bruto / "od.csv").write_text("a,b\n")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-m", "mexe no bruto")
    assert valida_estrutura.bruto_alterado(tmp_repo, "main") == \
        ["dados/bruto/od.csv"]


def test_bruto_alterado_ref_inexistente(tmp_repo):
    _git(tmp_repo, "init", "-b", "main")
    _git(tmp_repo, "config", "user.name", "T")
    _git(tmp_repo, "config", "user.email", "t@t")
    (tmp_repo / ".gitkeep").write_text("")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-m", "base")
    with pytest.raises(SystemExit):
        valida_estrutura.bruto_alterado(tmp_repo, "ref-inexistente")


def test_figura_sem_produz_e_apontada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    figuras = tmp_repo / "relatorio" / "figuras"
    figuras.mkdir(parents=True)
    (figuras / "mapa.png").write_bytes(b"png")
    (figuras / "curva.png").write_bytes(b"png")
    banco.registra("arquivo", "arq-000001",
                   {"titulo": "app/04-mapa.R", "desc": None})
    banco.registra("arquivo", "arq-000002",
                   {"titulo": "relatorio/figuras/mapa.png", "desc": None})
    banco.registra("aresta", "arq-000001",
                   {"relacao": "produz", "destino": "arq-000002"})
    assert valida_estrutura.figuras_sem_gerador(tmp_repo) == \
        ["relatorio/figuras/curva.png"]


def test_main_devolve_1_com_problema(tmp_repo, capsys):
    app = tmp_repo / "app"
    app.mkdir()
    (app / "solto.R").write_text("x <- 1\n")
    assert valida_estrutura.main([]) == 1
    assert "solto.R" in capsys.readouterr().err


def test_main_devolve_0_limpo(tmp_repo):
    assert valida_estrutura.main([]) == 0
