import subprocess

import banco
import gov


def _git(raiz, *args):
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


def _repo_git(raiz):
    _git(raiz, "init", "-b", "main")
    _git(raiz, "config", "user.name", "Teste")
    _git(raiz, "config", "user.email", "t@t")
    (raiz / "raiz.txt").write_text("x")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-m", "raiz")


def test_cria_branch_worktree_e_registra(tmp_repo, monkeypatch, capsys):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("tarefa", "tar-000001",
                   {"titulo": "estimar demanda", "resp": "Ana",
                    "status": "aberta"})
    _repo_git(tmp_repo)
    assert gov.main(["worktree", "tar-000001", "--slug", "demanda"]) == 0
    destino = tmp_repo.parent / f"{tmp_repo.name}.worktrees" / "tar-000001"
    assert destino.is_dir()
    assert str(destino) in capsys.readouterr().out
    ramos = subprocess.run(["git", "branch", "--list", "tarefa/*"],
                           cwd=tmp_repo, capture_output=True,
                           text=True).stdout
    assert "tarefa/tar-000001-demanda" in ramos
    branch = banco.conecta().execute(
        "SELECT payload->>'branch' FROM no WHERE entidade_id = 'tar-000001'"
    ).fetchone()[0]
    assert branch == "tarefa/tar-000001-demanda"


def test_idempotente_se_worktree_existe(tmp_repo, monkeypatch, capsys):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("tarefa", "tar-000002",
                   {"titulo": "t", "resp": "Ana", "status": "aberta"})
    _repo_git(tmp_repo)
    assert gov.main(["worktree", "tar-000002"]) == 0
    eventos_antes = banco.conecta().execute(
        "SELECT count(*) FROM evento").fetchone()[0]
    assert gov.main(["worktree", "tar-000002"]) == 0
    eventos_depois = banco.conecta().execute(
        "SELECT count(*) FROM evento").fetchone()[0]
    assert eventos_depois == eventos_antes


def test_recusa_no_que_nao_e_tarefa(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("meta", "met-000001",
                   {"titulo": "m", "status": "aberta"})
    _repo_git(tmp_repo)
    assert gov.main(["worktree", "met-000001"]) == 2
