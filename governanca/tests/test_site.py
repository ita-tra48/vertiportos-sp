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


def test_gera_as_nove_paginas(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    nomes = {p.name for p in destino.glob("*.html")}
    assert nomes == {a for a, _ in site_gov.PAGINAS} | {"grafo.html"}
    assert len(site_gov.PAGINAS) == 9


def test_index_e_o_grafo(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "index.html").read_text()
    assert "DADOS_GRAFO" in html
    assert "grafo-legenda" in html


def test_grafo_html_redireciona_para_index(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "grafo.html").read_text()
    assert 'url=index.html' in html


def test_estado_comeca_nos_indices_sem_carimbo(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "estado.html").read_text()
    assert "Localizar vertiportos na cidade de Sao Paulo" in html
    assert '<h2 class="clausula">2 · Estado</h2><h2>Índices auditados</h2>' in html
    assert 'class="carimbo"' not in html
    assert 'class="marca' not in html


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
    html = (destino / "estado.html").read_text()
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_grafo_home_escapa_fechamento_de_script(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Meta </script> maliciosa")
    destino = site_gov.gera(tmp_repo / "governanca" / "site")
    html = (destino / "index.html").read_text()
    assert "</script> maliciosa" not in html


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


def test_cabecalho_sem_auditoria(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "estado.html").read_text()
    cabeca = html[html.index('class="cabeca"'):html.index("</header>")]
    assert "Auditoria" not in cabeca


def test_no_interno_fora_do_index_mas_na_trilha(cenario):
    con = banco.conecta()
    did = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("patch", did, "interno=true")
    destino = site_gov.gera(cenario / "governanca" / "site")
    index = (destino / "index.html").read_text()
    trilha = (destino / "trilha.html").read_text()
    assert did not in index
    assert f'id="{did}"' in trilha


def test_integrantes_lista_os_quatro_nomes_com_links(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "integrantes.html").read_text()
    for nome in ("Gustavo", "Matheus", "Italo", "Carlos"):
        assert nome in html
    assert 'href="index.html#' in html


def test_integrante_sem_registros_mostra_mensagem(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "integrantes.html").read_text()
    assert "sem registros ainda" in html


def test_trilha_agrupa_por_dia(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "trilha.html").read_text()
    assert 'class="trilha-dia"' in html


def test_trilha_tem_filtros_de_tipo_e_autor(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "trilha.html").read_text()
    assert 'data-tipo=' in html
    assert 'data-autor=' in html
    assert "trilha-filtros" in html
