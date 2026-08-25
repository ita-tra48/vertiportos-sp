import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov
import site_gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def cenario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos na cidade de Sao Paulo")
    roda("decisao", "Recorte metropolitano", "--just", "porque X",
         "--alt", "municipio isolado")
    roda("tarefa", "Baixar Pesquisa OD", "--resp", "Ana",
         "--prazo", "2026-08-26")
    roda("fonte", "Pesquisa OD Metro SP", "--origem", "https://metro.sp.gov.br",
         "--limitacoes", "ultima onda 2017, sem eVTOL")
    roda("experimento", "--variante", "cobertura", "--p", "p=8",
         "--obj", "12345")
    roda("ia", "--proposito", "formulacao", "--aceito", "parcial",
         "--critica", "ignorou capacidade do vertiporto, corrigi a restricao")
    return tmp_repo


def test_gera_as_oito_paginas(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    nomes = {p.name for p in destino.glob("*.html")}
    assert nomes == {a for a, _ in site_gov.PAGINAS}
    assert len(site_gov.PAGINAS) == 8


def test_index_mostra_selo_e_metas(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "index.html").read_text()
    assert "Localizar vertiportos na cidade de Sao Paulo" in html
    assert "selo" in html.lower()


def test_pagina_ia_mostra_taxa_e_critica(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "ia.html").read_text()
    assert "ignorou capacidade do vertiporto" in html
    assert "%" in html


def test_site_nao_tem_dependencia_de_rede(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    for pagina in destino.glob("*.html"):
        texto = pagina.read_text()
        assert "http://" not in texto.replace(
            "http://www.w3.org/2000/svg", "")
        assert "cdn" not in texto.lower()


def test_geracao_e_determinista(cenario):
    destino = cenario / "governanca" / "site"
    site_gov.gera(destino)
    primeiro = {p.name: p.read_text() for p in sorted(destino.glob("*"))
                if p.is_file()}
    site_gov.gera(destino)
    segundo = {p.name: p.read_text() for p in sorted(destino.glob("*"))
               if p.is_file()}
    assert primeiro == segundo


def test_trilha_tem_ancora_por_no(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "trilha.html").read_text()
    con = banco.conecta()
    for (eid,) in con.execute("SELECT entidade_id FROM no").fetchall():
        assert f'id="{eid}"' in html


def test_escapa_html_do_usuario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "<img src=x onerror=alert(1)>")
    destino = site_gov.gera(tmp_repo / "governanca" / "site")
    html = (destino / "index.html").read_text()
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_tarefas_mostra_branch(cenario):
    banco.registra("tarefa", banco.novo_id("tar"),
                   {"titulo": "usar worktree", "resp": "Ana",
                    "status": "aberta", "branch": "tarefa/tar-xyz-demanda"})
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "tarefas.html").read_text()
    assert "tarefa/tar-xyz-demanda" in html


def test_update_gera_site(cenario, monkeypatch):
    monkeypatch.setattr(site_gov, "DESTINO",
                        cenario / "governanca" / "site")
    assert roda("update") == 0
    assert (cenario / "governanca" / "site" / "index.html").exists()


def _quebra_na_quarta_pagina(monkeypatch):
    original = Path.write_text
    alvo = site_gov.PAGINAS[3][0]

    def falha(self, *args, **kwargs):
        if self.name == alvo:
            raise OSError("disco cheio (simulado)")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", falha)


def test_gera_e_atomica_sem_site_anterior(cenario, monkeypatch):
    destino = cenario / "governanca" / "site"
    _quebra_na_quarta_pagina(monkeypatch)
    with pytest.raises(OSError):
        site_gov.gera(destino)
    assert not destino.exists()
    irmaos = {p.name for p in destino.parent.iterdir()}
    assert not any(n.startswith(".site") for n in irmaos)


def test_gera_e_atomica_com_site_anterior(cenario, monkeypatch):
    destino = cenario / "governanca" / "site"
    site_gov.gera(destino)
    anterior = {p.name: p.read_text() for p in sorted(destino.glob("*"))
                if p.is_file()}

    _quebra_na_quarta_pagina(monkeypatch)
    with pytest.raises(OSError):
        site_gov.gera(destino)

    atual = {p.name: p.read_text() for p in sorted(destino.glob("*"))
             if p.is_file()}
    assert atual == anterior
    irmaos = {p.name for p in destino.parent.iterdir()}
    assert not any(n.startswith(".site") for n in irmaos)


def test_gera_normal_produz_css_e_nojekyll(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    nomes = {p.name for p in destino.iterdir()}
    assert {a for a, _ in site_gov.PAGINAS} | {"estilo.css", ".nojekyll"} <= nomes
