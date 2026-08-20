import json
import os
import shutil
from html import escape
from pathlib import Path

import auditoria
import banco
import grafo

DESTINO = banco.RAIZ / "governanca" / "site"

PAGINAS = (("index.html", "Estado"),
           ("grafo.html", "Grafo executivo"),
           ("trilha.html", "Trilha"),
           ("tarefas.html", "Tarefas e pendencias"),
           ("ia.html", "Interacoes com IA"),
           ("experimentos.html", "Experimentos"),
           ("resultados.html", "Resultados"),
           ("reprodutibilidade.html", "Reprodutibilidade"))

ESTILO = """:root{--tinta:#0f172a;--fundo:#ffffff;--suave:#f1f5f9;
--borda:#e2e8f0;--fraco:#64748b;--verde:#047857;--vermelho:#be123c}
*{box-sizing:border-box}
body{margin:0;font:15px/1.6 ui-sans-serif,system-ui,sans-serif;
color:var(--tinta);background:var(--fundo)}
header{border-bottom:1px solid var(--borda);padding:18px 24px}
header h1{margin:0 0 10px;font-size:17px;letter-spacing:-.01em}
nav a{margin-right:14px;color:var(--fraco);text-decoration:none;font-size:13px}
nav a.ativo{color:var(--tinta);font-weight:600}
main{padding:24px;max-width:1100px}
h2{font-size:15px;margin:28px 0 10px;text-transform:uppercase;
letter-spacing:.06em;color:var(--fraco)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-bottom:8px}
th,td{border-bottom:1px solid var(--borda);padding:7px 9px;
text-align:left;vertical-align:top}
th{background:var(--suave);font-weight:600}
.rolagem{overflow-x:auto}
.selo{display:inline-block;padding:4px 11px;border-radius:99px;
color:#fff;font-size:12px;font-weight:700}
.selo.verde{background:var(--verde)}.selo.vermelho{background:var(--vermelho)}
.grade{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.cartao{border:1px solid var(--borda);border-radius:9px;padding:13px}
.cartao b{display:block;font-size:23px;line-height:1.1}
.cartao span{font-size:12px;color:var(--fraco)}
code,pre{font-family:ui-monospace,monospace;font-size:12px}
pre{background:var(--suave);padding:13px;border-radius:8px;overflow-x:auto}
.id{font-family:ui-monospace,monospace;font-size:11px;color:var(--fraco)}
@media(prefers-color-scheme:dark){:root{--tinta:#e6edf6;--fundo:#0b1120;
--suave:#151f33;--borda:#24314b;--fraco:#94a3b8}}
"""

PAN = """<script>
(function(){var s=document.getElementById('grafo');if(!s)return;
var g=document.getElementById('camada'),k=1,x=0,y=0,a=false,px=0,py=0;
function t(){g.setAttribute('transform','translate('+x+' '+y+') scale('+k+')')}
s.addEventListener('wheel',function(e){e.preventDefault();
k=Math.min(4,Math.max(.3,k*(e.deltaY<0?1.1:.9)));t()},{passive:false});
s.addEventListener('mousedown',function(e){a=true;px=e.clientX;py=e.clientY});
window.addEventListener('mouseup',function(){a=false});
window.addEventListener('mousemove',function(e){if(!a)return;
x+=e.clientX-px;y+=e.clientY-py;px=e.clientX;py=e.clientY;t()});})();
</script>"""


def _esc(v):
    return escape("" if v is None else str(v))


def _tabela(colunas, linhas):
    if not linhas:
        return '<p class="id">sem registros</p>'
    cab = "".join(f"<th>{_esc(c)}</th>" for c in colunas)
    corpo = "".join(
        "<tr>" + "".join(f"<td>{_esc(v)}</td>" for v in linha) + "</tr>"
        for linha in linhas)
    return f'<div class="rolagem"><table><tr>{cab}</tr>{corpo}</table></div>'


def _pagina(arquivo, titulo, corpo, extra=""):
    itens = []
    for a, t in PAGINAS:
        classe = ' class="ativo"' if a == arquivo else ""
        itens.append(f'<a href="{a}"{classe}>{t}</a>')
    nav = "".join(itens)
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_esc(titulo)} — TRA-48 Grupo 1</title>'
            f'<link rel="stylesheet" href="estilo.css"></head><body>'
            f'<header><h1>TRA-48 · Projeto B1 · Localizacao de vertiportos '
            f'em Sao Paulo</h1><nav>{nav}</nav></header>'
            f'<main><h2>{_esc(titulo)}</h2>{corpo}</main>{extra}</body></html>')


def _index(con, m):
    r, p, h = m["rastreabilidade"], m["postura"], m["higiene"]
    cor, motivos = m["selo"]
    lista = "".join(f"<li>{_esc(x)}</li>" for x in motivos) or "<li>sem apontamentos</li>"
    cartoes = (
        f'<div class="grade">'
        f'<div class="cartao"><b>{r["decisoes_total"]}</b>'
        f'<span>decisoes registradas</span></div>'
        f'<div class="cartao"><b>{r["decisoes_com_meta"]}%</b>'
        f'<span>decisoes com meta</span></div>'
        f'<div class="cartao"><b>{len(r["orfaos"])}</b>'
        f'<span>nos orfaos</span></div>'
        f'<div class="cartao"><b>{p["taxa_integral"]}%</b>'
        f'<span>aceite integral de IA ({p["total"]} interacoes)</span></div>'
        f'<div class="cartao"><b>{len(h["tarefas_incompletas"])}</b>'
        f'<span>tarefas incompletas</span></div></div>')
    metas = _tabela(["id", "meta", "status", "criada por"], con.execute(
        "SELECT id, titulo, status, criado_por FROM meta ORDER BY criado_em, id"
    ).fetchall())
    acoes = _tabela(["prazo", "tarefa", "resp"], con.execute(
        "SELECT prazo, titulo, resp FROM tarefa WHERE status = 'aberta' "
        "ORDER BY prazo NULLS LAST, id LIMIT 10").fetchall())
    decisoes = _tabela(["quando", "decisao", "justificativa", "autor"],
                       con.execute(
        "SELECT criado_em, titulo, justificativa, criado_por FROM decisao "
        "ORDER BY criado_em DESC, id DESC LIMIT 8").fetchall())
    return (f'<p>Selo de auditoria: <span class="selo {cor}">{cor.upper()}'
            f'</span></p><ul>{lista}</ul>{cartoes}'
            f'<h2>Metas</h2>{metas}<h2>Proximas acoes</h2>{acoes}'
            f'<h2>Ultimas decisoes</h2>{decisoes}')


def _trilha(con):
    linhas = con.execute(
        "SELECT ts, autor, tipo, entidade_id, payload FROM evento "
        "ORDER BY ts DESC, evento_id DESC").fetchall()
    blocos = []
    for ts, autor, tipo, eid, payload in linhas:
        dados = json.loads(payload)
        campos = "".join(
            f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
            for k, v in sorted(dados.items()) if v not in (None, "", [], {}))
        blocos.append(
            f'<h2 id="{_esc(eid)}">{_esc(ts)} · {_esc(tipo)} · '
            f'<span class="id">{_esc(eid)}</span> · {_esc(autor)}</h2>'
            f'<div class="rolagem"><table>{campos}</table></div>')
    return "".join(blocos) or '<p class="id">sem eventos</p>'


def _tarefas(con):
    tarefas = _tabela(["id", "tarefa", "resp", "prazo", "status"],
                      con.execute(
        "SELECT id, titulo, resp, prazo, status FROM tarefa "
        "ORDER BY status, prazo NULLS LAST, id").fetchall())
    pendencias = _tabela(["id", "pendencia", "aberta em", "status", "resolucao"],
                         con.execute(
        "SELECT id, titulo, criado_em, status, resolucao FROM pendencia "
        "ORDER BY status, criado_em, id").fetchall())
    return f"{tarefas}<h2>Pendencias</h2>{pendencias}"


def _ia(con, m):
    p = m["postura"]
    cartoes = (f'<div class="grade">'
               f'<div class="cartao"><b>{p["taxa_integral"]}%</b>'
               f'<span>aceite integral</span></div>'
               f'<div class="cartao"><b>{p["integral"]}</b>'
               f'<span>integral</span></div>'
               f'<div class="cartao"><b>{p["parcial"]}</b>'
               f'<span>parcial</span></div>'
               f'<div class="cartao"><b>{p["descarte"]}</b>'
               f'<span>descarte</span></div></div>')
    tabela = _tabela(
        ["quando", "quem", "proposito", "modelo", "aceito", "critica humana"],
        con.execute("SELECT criado_em, criado_por, proposito, modelo, aceito, "
                    "critica FROM ia ORDER BY criado_em DESC, id DESC").fetchall())
    return (f'{cartoes}<p>Taxa proxima de 100% nao e eficiencia: e ausencia de '
            f'revisao (enunciado 5.6.3).</p><h2>Registros</h2>{tabela}')


def _experimentos(con):
    return _tabela(
        ["id", "variante", "parametros", "obj", "gap", "tempo (s)", "commit",
         "hipotese", "conclusao"],
        con.execute("SELECT id, variante, parametros, obj, gap, tempo_s, "
                    "commit_sha, hipotese, conclusao FROM experimento "
                    "ORDER BY criado_em, id").fetchall())


def _resultados(con):
    arquivos = _tabela(["id", "arquivo", "descricao"], con.execute(
        "SELECT id, caminho, descricao FROM arquivo ORDER BY caminho, id"
    ).fetchall())
    fontes = _tabela(["fonte", "origem", "formato", "cobertura", "limitacoes"],
                     con.execute(
        "SELECT nome, origem, formato, cobertura, limitacoes FROM fonte "
        "ORDER BY nome, id").fetchall())
    refs = _tabela(["citacao", "url", "doi"], con.execute(
        "SELECT citacao, url, doi FROM referencia ORDER BY citacao, id").fetchall())
    return (f'<p>Mapas, fronteira de implantacao e sensibilidade entram aqui '
            f'quando a camada A produzir os artefatos, registrados via '
            f'<code>./gov arquivo</code>.</p><h2>Artefatos</h2>{arquivos}'
            f'<h2>Fontes de dados</h2>{fontes}<h2>Referencias</h2>{refs}')


def _reprodutibilidade():
    return ('<p>Qualquer pessoa deve conseguir rodar o projeto do zero. '
            'O banco binario nao e versionado: ele e reconstruido do '
            '<code>governanca/dump.sql</code>.</p><pre>'
            'git clone https://github.com/Projeto-TRA-48-Grupo-1/'
            'TRA-48_Projeto.git\ncd TRA-48_Projeto\n'
            'python3 -m venv governanca/.venv\n'
            'governanca/.venv/bin/pip install -r governanca/requirements.txt\n'
            './gov rebuild\n./gov status\n./gov auditoria\n./gov update\n'
            'Rscript app/01-carrega.R</pre>'
            '<h2>Regra do projeto</h2><p>O que nao estiver no banco, nao '
            'aconteceu. Escrita sempre pelo <code>./gov</code>; leitura pelo '
            'MCP ou por <code>./gov consulta</code>.</p>')


def gera(destino=None):
    destino = Path(destino) if destino else DESTINO
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = banco.conecta()
    m = auditoria.calcula(con)
    corpos = {
        "index.html": _index(con, m),
        "grafo.html": f'<div class="rolagem">{grafo.svg(con)}</div>'
                      f'<p class="id">roda do mouse: zoom · arrastar: pan · '
                      f'clique no no: abre o registro na trilha</p>',
        "trilha.html": _trilha(con),
        "tarefas.html": _tarefas(con),
        "ia.html": _ia(con, m),
        "experimentos.html": _experimentos(con),
        "resultados.html": _resultados(con),
        "reprodutibilidade.html": _reprodutibilidade(),
    }
    tmp = destino.parent / f".{destino.name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        for arquivo, titulo in PAGINAS:
            extra = PAN if arquivo == "grafo.html" else ""
            (tmp / arquivo).write_text(
                _pagina(arquivo, titulo, corpos[arquivo], extra), encoding="utf-8")
        (tmp / "estilo.css").write_text(ESTILO, encoding="utf-8")
        (tmp / ".nojekyll").write_text("", encoding="utf-8")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    velho = destino.parent / f".{destino.name}.velho"
    if velho.exists():
        shutil.rmtree(velho)
    if destino.exists():
        os.replace(destino, velho)
    try:
        os.replace(tmp, destino)
    except Exception:
        if velho.exists():
            os.replace(velho, destino)
        raise
    if velho.exists():
        shutil.rmtree(velho, ignore_errors=True)
    return destino
