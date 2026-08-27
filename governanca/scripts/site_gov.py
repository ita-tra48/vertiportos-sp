import json
import os
import shutil
import subprocess
from html import escape
from pathlib import Path

import re

import auditoria
import banco
import grafo

ICONE = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
         "viewBox='0 0 16 16'%3E%3Crect width='16' height='16' fill='%23fbfbf9'"
         "/%3E%3Crect x='1.5' y='3.5' width='13' height='9' fill='none' "
         "stroke='%235a3a92' stroke-width='1'/%3E%3Crect x='3.5' y='5.5' "
         "width='9' height='5' fill='none' stroke='%235a3a92' "
         "stroke-width='1'/%3E%3C/svg%3E")

DESTINO = banco.RAIZ / "governanca" / "site"
FONTES = banco.RAIZ / "governanca" / "assets" / "fontes"

PAGINAS = (("index.html", "Grafo executivo"),
           ("estado.html", "Estado"),
           ("trilha.html", "Trilha"),
           ("tarefas.html", "Tarefas e pendências"),
           ("integrantes.html", "Integrantes"),
           ("ia.html", "Interações com IA"),
           ("experimentos.html", "Experimentos"),
           ("resultados.html", "Resultados"),
           ("reprodutibilidade.html", "Reprodutibilidade"))

INTEGRANTES = banco.RAIZ / "governanca" / "integrantes.json"

_ID = re.compile(r"(?:met|tar|pen|dec|fon|arq|ref|exp|ia|evt)-[0-9a-z]{6}")
_QUANDO = re.compile(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?")

CAMPOS = {"titulo": "título", "desc": "descrição", "just": "justificativa",
          "alt": "alternativas descartadas", "resp": "responsável",
          "prazo": "prazo", "status": "status", "resolucao": "resolução",
          "origem": "origem", "formato": "formato", "cobertura": "cobertura",
          "limitacoes": "limitações", "url": "url", "doi": "doi",
          "variante": "variante", "p": "parâmetros", "commit": "commit",
          "obj": "função objetivo", "gap": "gap", "tempo": "tempo (s)",
          "hipotese": "hipótese", "conclusao": "conclusão",
          "proposito": "propósito", "modelo": "modelo", "pedido": "pedido",
          "retorno": "retorno", "aceito": "aceite",
          "critica": "crítica humana", "relacao": "relação",
          "destino": "destino", "branch": "branch"}

_ACEITE = {"integral": "integral", "parcial": "em parte",
           "descarte": "descartada"}

SIGLAS = {"meta": "MET", "tarefa": "TAR", "pendencia": "PEN",
          "decisao": "DEC", "fonte": "FON", "arquivo": "ARQ",
          "referencia": "REF", "experimento": "EXP", "ia": "IA",
          "aresta": "ARE"}

CONTRATO = """<!--
THESIS: este site e um documento controlado sob revisao, nao um painel; recusa a
fileira de tiles de metrica e a grade de cartoes iguais que a categoria entrega.
OWN-WORLD: folha branco-frio com moldura de fio, bloco de titulo em mono,
clausulas numeradas como handle de citacao, carimbo de auditoria de borda dupla;
anil carrega estrutura, violeta carimba aprovacao, lapis vermelho e reservado a
falha, grafite encerra. Tipografia B612 (Airbus, telas de cockpit), mono para
identificador e numero, sans para prosa.
STORY: o professor pergunta por que este valor, quem decidiu, qual script gerou
esta figura; a folha responde em um clique e delata as proprias fraquezas.
FIRST VIEWPORT: identidade do documento a esquerda, bloco de titulo com revisao
a direita, e o carimbo de auditoria dominando a primeira dobra com os motivos
impressos abaixo como clausulas numeradas.
FORM: Documento Controlado, candidato 6 da lista ordenada, seed b1f01bde.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
-->"""

ESTILO = """@font-face{font-family:B612;src:url(fontes/B612-Regular.woff2)
format("woff2");font-weight:400;font-style:normal;font-display:swap}
@font-face{font-family:B612;src:url(fontes/B612-Bold.woff2)
format("woff2");font-weight:700;font-style:normal;font-display:swap}
@font-face{font-family:B612M;src:url(fontes/B612Mono-Regular.woff2)
format("woff2");font-weight:400;font-style:normal;font-display:swap}
@font-face{font-family:B612M;src:url(fontes/B612Mono-Bold.woff2)
format("woff2");font-weight:700;font-style:normal;font-display:swap}
:root{color-scheme:light;
--papel:#fbfbf9;--mesa:#e7e8ea;--nanquim:#14181c;--nanquim2:#48535e;
--anil:#14457f;--anil-fraco:#dde5f1;--carimbo:#5a3a92;--carimbo-fraco:#e9e2f5;
--lapis:#ab2118;--lapis-fraco:#f7e3e1;--grafite:#5c646d;
--fio:#c3c9d1;--fio-forte:#98a1ab;--sans:B612,ui-sans-serif,system-ui,sans-serif;
--mono:B612M,ui-monospace,SFMono-Regular,Menlo,monospace;
--u:8px}
*{box-sizing:border-box}
html{font-size:clamp(14.5px,.36vw + 10.4px,19px)}
body{margin:0;background:var(--mesa);color:var(--nanquim);
font:1rem/1.55 var(--sans);-webkit-font-smoothing:antialiased}
::selection{background:var(--anil-fraco);color:var(--nanquim)}
:focus-visible{outline:2px solid var(--anil);outline-offset:2px}
*{scrollbar-color:var(--fio-forte) transparent;scrollbar-width:thin}
::-webkit-scrollbar{height:10px;width:10px}
::-webkit-scrollbar-thumb{background:var(--fio-forte)}
::-webkit-scrollbar-track{background:transparent}
.folha{max-width:1240px;margin:calc(var(--u)*3) auto;background:var(--papel);
border:1px solid var(--fio-forte);
box-shadow:0 1px 2px rgba(20,24,28,.07),0 6px 20px rgba(20,24,28,.06)}
.cabeca{display:grid;grid-template-columns:1fr auto;gap:calc(var(--u)*3);
align-items:start;padding:calc(var(--u)*3);border-bottom:2px solid var(--nanquim)}
.orgao{font:700 .76rem/1.45 var(--mono);letter-spacing:.11em;
text-transform:uppercase;color:var(--anil);margin:0 0 calc(var(--u)*1.5)}
.orgao span{display:block;color:var(--grafite);font-weight:400;
letter-spacing:.09em}
.cabeca h1{margin:0;font:700 1.5rem/1.15 var(--sans);letter-spacing:-.018em;
max-width:30ch}
.bloco{border:1px solid var(--nanquim);display:grid;
grid-template-columns:auto auto;font:.72rem/1.35 var(--mono);
font-variant-numeric:tabular-nums;min-width:16rem}
.bloco dt{padding:5px 9px;border-right:1px solid var(--fio);
border-bottom:1px solid var(--fio);letter-spacing:.09em;
text-transform:uppercase;color:var(--nanquim2);background:#f3f4f6}
.bloco dd{margin:0;padding:5px 9px;border-bottom:1px solid var(--fio);
font-weight:700;text-align:right}
.bloco dt:last-of-type,.bloco dd:last-of-type{border-bottom:0}
.corpo{display:grid;grid-template-columns:15.5rem 1fr}
nav{border-right:1px solid var(--fio);padding:calc(var(--u)*3) 0}
nav ol{margin:0;padding:0;list-style:none}
nav a{display:grid;grid-template-columns:2.2rem 1fr;gap:2px;
padding:7px calc(var(--u)*3);color:var(--nanquim2);text-decoration:none;
font-size:.86rem;border-left:3px solid transparent}
nav a span{font:700 .78rem/1.55 var(--mono);color:var(--anil)}
nav a:hover{background:var(--anil-fraco);color:var(--nanquim)}
nav a[aria-current]{border-left-color:var(--anil);color:var(--nanquim);
font-weight:700;background:var(--anil-fraco)}
main{padding:calc(var(--u)*3);min-width:0}
.clausula{font:700 .8rem/1.3 var(--mono);letter-spacing:.12em;
text-transform:uppercase;color:var(--anil);margin:0 0 calc(var(--u)*1.5);
padding-bottom:6px;border-bottom:1px solid var(--fio)}
main h2{font:700 .82rem/1.3 var(--mono);letter-spacing:.1em;
text-transform:uppercase;color:var(--nanquim2);
margin:calc(var(--u)*4) 0 calc(var(--u)*1.5)}
main h2:first-of-type{margin-top:calc(var(--u)*3)}
p{max-width:68ch;margin:0 0 calc(var(--u)*1.5)}
.nota{color:var(--nanquim2);font-size:.9rem}
.carimbo{display:grid;grid-template-columns:minmax(21rem,26rem) 1fr;
gap:calc(var(--u)*5);align-items:start;
padding:calc(var(--u)*2) 0 calc(var(--u)*5)}
.marca{border:3px double currentColor;padding:calc(var(--u)*3) calc(var(--u)*2);
text-align:center;font:700 2.55rem/1 var(--mono);letter-spacing:.12em;
text-indent:.12em;animation:bate .5s cubic-bezier(.16,1,.3,1) 1}
.marca small{display:block;margin-top:10px;font-size:.55rem;letter-spacing:.1em;
font-weight:400}
.marca.aprovado{color:var(--carimbo);background:var(--carimbo-fraco)}
.marca.reprovado{color:var(--lapis);background:var(--lapis-fraco)}
.marca.pendente{color:var(--grafite);background:#eff0f2;font-size:1.85rem}
@keyframes bate{from{transform:scale(1.035);filter:blur(1.5px)}
to{transform:scale(1);filter:blur(0)}}
@media(prefers-reduced-motion:reduce){.marca{animation:none}}
.motivos{margin:0;padding:0;list-style:none;font-size:1rem;
border-top:1px solid var(--nanquim)}
.motivos li{display:grid;grid-template-columns:2.6rem 1fr;gap:4px;
padding:9px 0;border-bottom:1px solid var(--fio)}
.motivos li:last-child{border-bottom:0}
.motivos b{font:700 .82rem/1.6 var(--mono);color:var(--lapis)}
.limpo{font-size:.95rem;color:var(--nanquim2);max-width:56ch}
.indices{margin:0 0 calc(var(--u)*4);border-top:1px solid var(--nanquim);
display:grid;grid-template-columns:1fr auto;font-size:.92rem}
.indices dt{padding:7px 0;border-bottom:1px solid var(--fio)}
.indices dd{margin:0;padding:7px 0 7px calc(var(--u)*3);text-align:right;
border-bottom:1px solid var(--fio);font:700 1.05rem/1.55 var(--sans);
font-variant-numeric:tabular-nums;white-space:nowrap}
.indices dd.alerta{color:var(--lapis)}
.rolagem{overflow-x:auto;border:1px solid var(--fio);
margin-bottom:calc(var(--u)*1.5)}
table{border-collapse:collapse;width:100%;font-size:.86rem}
th,td{padding:6px 10px;text-align:left;vertical-align:top;
border-bottom:1px solid var(--fio)}
th{font:700 .72rem/1.4 var(--mono);letter-spacing:.08em;text-transform:uppercase;
color:var(--nanquim2);background:#f3f4f6;border-bottom:1px solid var(--fio-forte);
white-space:nowrap}
tr:last-child td{border-bottom:0}
tbody tr:hover td{background:var(--anil-fraco)}
td{font-variant-numeric:tabular-nums}
.sigla{display:inline-block;min-width:2.8rem;padding:1px 5px;
border:1px solid currentColor;font:700 .68rem/1.5 var(--mono);
letter-spacing:.06em;text-align:center;color:var(--anil)}
.id{font:.76rem/1.5 var(--mono);color:var(--grafite)}
.ident{font:.8rem/1.5 var(--mono);white-space:nowrap}
.reg{border-bottom:1px solid var(--fio);padding:calc(var(--u)*2) 0}
.reg:target{background:var(--anil-fraco);box-shadow:-6px 0 0 var(--anil)}
.reg h3{margin:0 0 var(--u);font:400 .82rem/1.4 var(--mono);
display:flex;flex-wrap:wrap;gap:calc(var(--u)*1.5);align-items:baseline}
.reg h3 time{font:700 .88rem/1.4 var(--sans);font-variant-numeric:tabular-nums}
.reg.aresta{padding:6px 0;background:#f7f8f9}
.reg.aresta h3{margin:0;font-size:.78rem;color:var(--nanquim2)}
.reg .rel{font:700 .72rem/1.5 var(--mono);letter-spacing:.06em;
text-transform:uppercase;color:var(--anil)}
.lista{margin:0;padding-left:1.2em}
.lista li{margin-bottom:2px}
.reg h3 .quem{color:var(--nanquim2)}
.reg dl{margin:0;display:grid;grid-template-columns:9.5rem 1fr;
gap:1px calc(var(--u)*2);font-size:.88rem}
.reg dt{font:700 .72rem/1.7 var(--mono);letter-spacing:.06em;
text-transform:uppercase;color:var(--nanquim2)}
.reg dd{margin:0;overflow-wrap:anywhere}
pre{background:#f3f4f6;border:1px solid var(--fio);padding:calc(var(--u)*2);
overflow-x:auto;font:.82rem/1.7 var(--mono);margin:0 0 calc(var(--u)*1.5)}
code{font:.86em var(--mono);background:#f3f4f6;padding:1px 4px;
border:1px solid var(--fio)}
a{color:var(--anil);text-underline-offset:3px}
.integrante h3{font:700 .72rem/1.5 var(--mono);letter-spacing:.06em;
text-transform:uppercase;color:var(--nanquim2);
margin:calc(var(--u)*1.5) 0 4px}
.trilha-filtros{display:flex;flex-wrap:wrap;gap:calc(var(--u)*1.5);
margin-bottom:calc(var(--u)*2)}
.trilha-dia{font:700 .78rem/1.4 var(--mono);letter-spacing:.08em;
text-transform:uppercase;color:var(--anil);
margin:calc(var(--u)*3) 0 var(--u);padding-bottom:4px;
border-bottom:1px solid var(--nanquim)}
.reg.commit{background:#f3f4f6;border-left:3px solid var(--grafite)}
.reg.commit p{margin:4px 0 0;font-size:.88rem}
.grafo-moldura{border:1px solid var(--fio);overflow:auto;background:#fdfdfc}
.rodape{padding:calc(var(--u)*2) calc(var(--u)*3);border-top:1px solid var(--fio);
font:.74rem/1.6 var(--mono);color:var(--grafite);
display:flex;flex-wrap:wrap;gap:calc(var(--u)*2);justify-content:space-between}
@media(max-width:900px){
.corpo{grid-template-columns:1fr}
nav{border-right:0;border-bottom:1px solid var(--fio);padding:var(--u) 0}
nav ol{display:flex;flex-wrap:wrap}
nav a{border-left:0;border-bottom:3px solid transparent;padding:6px 12px}
nav a[aria-current]{border-left:0;border-bottom-color:var(--anil)}
.cabeca{grid-template-columns:1fr}
.carimbo{grid-template-columns:1fr}
.reg dl{grid-template-columns:1fr}
.folha{margin:0;border-left:0;border-right:0}}
""" + grafo.ESTILO_HOME

GRAFO_REDIRECT = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                  '<meta http-equiv="refresh" content="0; url=index.html">'
                  '<title>Grafo executivo — TRA-48 Grupo 1</title></head>'
                  '<body><p>Esta página se mudou para '
                  '<a href="index.html">index.html</a>.</p></body></html>')



def _esc(v):
    return escape("" if v is None else str(v))


def _alerta(condicao):
    return ' class="alerta"' if condicao else ""


def _pc(valor):
    return "—" if valor is None else f"{valor}%"


def _valor(v):
    if isinstance(v, list):
        return "".join(f"<li>{_esc(x)}</li>" for x in v)
    if isinstance(v, dict):
        return "".join(f"<li>{_esc(k)} = {_esc(x)}</li>"
                       for k, x in sorted(v.items()))
    return _esc(v)


def _campo(chave, valor):
    rotulo = _esc(CAMPOS.get(chave, chave))
    if isinstance(valor, (list, dict)):
        return f'<dt>{rotulo}</dt><dd><ul class="lista">{_valor(valor)}</ul></dd>'
    return f"<dt>{rotulo}</dt><dd>{_valor(valor)}</dd>"


def _celula(v):
    texto = _esc(v)
    if isinstance(v, str) and (_ID.fullmatch(v) or _QUANDO.fullmatch(v)):
        return f'<td><span class="ident">{texto}</span></td>'
    return f"<td>{texto}</td>"


def _tabela(colunas, linhas, vazio="sem registros"):
    if not linhas:
        return f'<p class="limpo">{_esc(vazio)}</p>'
    cab = "".join(f"<th>{_esc(c)}</th>" for c in colunas)
    corpo = "".join(
        "<tr>" + "".join(_celula(v) for v in linha) + "</tr>"
        for linha in linhas)
    return (f'<div class="rolagem"><table><thead><tr>{cab}</tr></thead>'
            f'<tbody>{corpo}</tbody></table></div>')


def _bloco_titulo(m):
    revisao = m["revisao"]
    return (f'<dl class="bloco">'
            f'<dt>Projeto</dt><dd>B1 · PO</dd>'
            f'<dt>Revisão</dt><dd>{_esc(revisao)}</dd>'
            f'<dt>Registros</dt><dd>{m["registros"]}</dd>'
            f'</dl>')


def _pagina(arquivo, titulo, corpo, m, extra=""):
    itens = []
    for i, (a, t) in enumerate(PAGINAS, start=1):
        atual = ' aria-current="page"' if a == arquivo else ""
        itens.append(f'<li><a href="{a}"{atual}><span>{i}</span>{_esc(t)}</a>'
                     f'</li>')
    numero = next(i for i, (a, _) in enumerate(PAGINAS, start=1) if a == arquivo)
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{numero} {_esc(titulo)} — TRA-48 Grupo 1</title>'
            f'<link rel="icon" href="{ICONE}">'
            f'<link rel="stylesheet" href="estilo.css"></head><body>'
            f'{CONTRATO}'
            f'<article class="folha">'
            f'<header class="cabeca"><div>'
            f'<p class="orgao">Instituto Tecnológico de Aeronáutica'
            f'<span>TRA-48 · Inteligência Analítica · Grupo 1</span></p>'
            f'<h1>Localização de vertiportos na cidade de São Paulo</h1>'
            f'</div>{_bloco_titulo(m)}</header>'
            f'<div class="corpo">'
            f'<nav aria-label="Cláusulas"><ol>{"".join(itens)}</ol></nav>'
            f'<main><h2 class="clausula">{numero} · {_esc(titulo)}</h2>'
            f'{corpo}</main></div>'
            f'<footer class="rodape"><span>O que não estiver no banco, não '
            f'aconteceu.</span><span>Folha gerada de governanca/dump.sql pelo '
            f'./gov update</span></footer>'
            f'</article>{extra}</body></html>')


def _selo(m):
    cor, motivos = m["selo"]
    classe = {"verde": "aprovado", "cinza": "pendente"}.get(cor, "reprovado")
    rotulo = {"verde": "APROVADO", "cinza": "NÃO AUDITADO"}.get(cor, "REPROVADO")
    if motivos:
        itens = "".join(
            f'<li><b>{n}.</b><span>{_esc(x)}</span></li>'
            for n, x in enumerate(motivos, start=1))
        lado = (f'<h2>Apontamentos da auditoria</h2>'
                f'<ol class="motivos">{itens}</ol>')
    else:
        lado = ('<p class="limpo">Nenhum apontamento: nenhum nó órfão, toda '
                'decisão vinculada a uma meta, nenhuma pendência envelhecida e '
                'aceite de IA abaixo de 100%.</p>')
    return (f'<section class="carimbo"><div class="marca {classe}">{rotulo}'
            f'<small>Selo de auditoria</small></div><div>{lado}</div></section>')


def _estado(con, m):
    r, p, h = m["rastreabilidade"], m["postura"], m["higiene"]
    orfaos = len(r["orfaos"])
    incompletas = len(h["tarefas_incompletas"])
    velhas = len(h["pendencias_velhas"])
    indices = (
        f'<dl class="indices">'
        f'<dt>Decisões registradas</dt><dd>{r["decisoes_total"]}</dd>'
        f'<dt>Decisões vinculadas a uma meta</dt>'
        f'<dd{_alerta(r["decisoes_com_meta"] is not None and r["decisoes_com_meta"] < 90)}>'
        f'{_pc(r["decisoes_com_meta"])}</dd>'
        f'<dt>Arquivos vinculados a uma decisão</dt>'
        f'<dd>{_pc(r["arquivos_com_decisao"])}</dd>'
        f'<dt>Nós órfãos</dt>'
        f'<dd{_alerta(orfaos)}>{orfaos}</dd>'
        f'<dt>Interações com IA aceitas integralmente</dt>'
        f'<dd{_alerta(p["total"] and p["taxa_integral"] == 100)}>'
        f'{_pc(p["taxa_integral"])}</dd>'
        f'<dt>Interações com IA registradas</dt><dd>{p["total"]}</dd>'
        f'<dt>Tarefas sem responsável ou sem prazo</dt>'
        f'<dd{_alerta(incompletas)}>{incompletas}</dd>'
        f'<dt>Pendências abertas além do prazo</dt>'
        f'<dd{_alerta(velhas)}>{velhas}</dd></dl>')
    metas = _tabela(["id", "meta", "status", "registrada por"], con.execute(
        "SELECT id, titulo, status, criado_por FROM meta ORDER BY criado_em, id"
    ).fetchall(), "Nenhuma meta registrada. O projeto começa por ./gov meta.")
    acoes = _tabela(["prazo", "tarefa", "responsável"], con.execute(
        "SELECT prazo, titulo, resp FROM tarefa WHERE status = 'aberta' "
        "ORDER BY prazo NULLS LAST, id LIMIT 10").fetchall(),
        "Nenhuma tarefa aberta.")
    decisoes = _tabela(["quando", "decisão", "justificativa", "autor"],
                       con.execute(
        "SELECT strftime(criado_em, '%Y-%m-%d %H:%M'), titulo, justificativa, "
        "criado_por FROM decisao ORDER BY criado_em DESC, id DESC LIMIT 8"
        ).fetchall(), "Nenhuma decisão registrada.")
    return (f'{_selo(m)}<h2>Índices auditados</h2>{indices}'
            f'<h2>Metas</h2>{metas}'
            f'<h2>Próximas ações</h2>{acoes}'
            f'<h2>Últimas decisões</h2>{decisoes}')


def _commits():
    try:
        saida = subprocess.run(
            ["git", "log", "--format=%h\x1f%ad\x1f%an\x1f%s",
             "--date=format:%Y-%m-%d %H:%M"],
            cwd=banco.RAIZ, capture_output=True, text=True,
            check=False).stdout
    except OSError:
        return []
    commits = []
    for linha in saida.splitlines():
        partes = linha.split("\x1f")
        if len(partes) == 4:
            commits.append(tuple(partes))
    return commits


def _rotulo_tipo(tipo):
    extras = {"aresta": "arestas", "commit": "commits"}
    return grafo.ROTULOS.get(tipo, extras.get(tipo, tipo))


def _chips(valores, atributo):
    return "".join(
        f'<button type="button" class="grafo-chip ativo" '
        f'data-{atributo}="{_esc(v)}">{_esc(r)}</button>'
        for v, r in valores)


def _trilha(con):
    linhas = con.execute(
        "SELECT strftime(ts, '%Y-%m-%d %H:%M'), autor, tipo, entidade_id, "
        "evento_id, payload FROM evento ORDER BY ts DESC, evento_id DESC"
        ).fetchall()
    commits = _commits()
    if not linhas and not commits:
        return ('<p class="limpo">Nenhum evento registrado. A trilha é '
                'alimentada por cada comando ./gov.</p>')
    itens = ([(ts, "evento", (autor, tipo, eid, evid, payload))
              for ts, autor, tipo, eid, evid, payload in linhas]
             + [(quando, "commit", (autor, h, msg))
                for h, quando, autor, msg in commits])
    itens.sort(key=lambda item: item[0], reverse=True)

    tipos = sorted({d[1] if k == "evento" else "commit" for _, k, d in itens})
    autores = sorted({d[0] for _, k, d in itens})
    filtros = (
        f'<div class="trilha-filtros">'
        f'<div class="grafo-legenda">'
        f'{_chips([(t, _rotulo_tipo(t)) for t in tipos], "tipo")}</div>'
        f'<div class="grafo-legenda">'
        f'{_chips([(a, a) for a in autores], "autor")}</div></div>')

    vistos = set()
    blocos = []
    dia_atual = None
    for ts, kind, dados in itens:
        dia = ts[:10]
        if dia != dia_atual:
            dia_atual = dia
            blocos.append(f'<h2 class="trilha-dia">{_esc(dia)}</h2>')
        if kind == "commit":
            autor, h, msg = dados
            blocos.append(
                f'<section class="reg commit" data-tipo="commit" '
                f'data-autor="{_esc(autor)}">'
                f'<h3><span class="sigla">GIT</span><time>{_esc(ts)}</time>'
                f'<span class="ident">{_esc(h)}</span>'
                f'<span class="quem">{_esc(autor)}</span></h3>'
                f'<p>{_esc(msg)}</p></section>')
            continue
        autor, tipo, eid, evid, payload = dados
        primeiro = eid not in vistos
        vistos.add(eid)
        ancora = eid if primeiro else evid
        dj = json.loads(payload)
        cabeca = (f'<span class="sigla">{_esc(SIGLAS.get(tipo, tipo))}</span>'
                  f'<time>{_esc(ts)}</time>')
        if tipo == "aresta":
            blocos.append(
                f'<section class="reg aresta" data-tipo="aresta" '
                f'data-autor="{_esc(autor)}" id="{_esc(ancora)}">'
                f'<h3>{cabeca}'
                f'<span class="ident">{_esc(eid)}</span>'
                f'<span class="rel">{_esc(dj.get("relacao", ""))}</span>'
                f'<span class="ident">{_esc(dj.get("destino", ""))}</span>'
                f'<span class="quem">{_esc(autor)}</span></h3></section>')
            continue
        campos = "".join(
            _campo(k, v) for k, v in sorted(dj.items())
            if v not in (None, "", [], {}))
        blocos.append(
            f'<section class="reg" data-tipo="{_esc(tipo)}" '
            f'data-autor="{_esc(autor)}" id="{_esc(ancora)}">'
            f'<h3>{cabeca}'
            f'<span class="ident">{_esc(eid)}</span>'
            f'<span class="quem">{_esc(autor)}</span></h3>'
            f'<dl>{campos}</dl></section>')
    return filtros + "".join(blocos) + _SCRIPT_TRILHA


_SCRIPT_TRILHA = """<script>
(function(){
var ocultoTipo = {}, ocultoAutor = {};
function aplica(){
  document.querySelectorAll('.reg[data-tipo]').forEach(function(el){
    var ok = !ocultoTipo[el.dataset.tipo] && !ocultoAutor[el.dataset.autor];
    el.style.display = ok ? '' : 'none';
  });
}
document.querySelectorAll('.trilha-filtros [data-tipo]').forEach(function(chip){
  chip.addEventListener('click', function(){
    var v = chip.dataset.tipo;
    if (ocultoTipo[v]) { delete ocultoTipo[v]; chip.classList.add('ativo'); }
    else { ocultoTipo[v] = true; chip.classList.remove('ativo'); }
    aplica();
  });
});
document.querySelectorAll('.trilha-filtros [data-autor]').forEach(function(chip){
  chip.addEventListener('click', function(){
    var v = chip.dataset.autor;
    if (ocultoAutor[v]) { delete ocultoAutor[v]; chip.classList.add('ativo'); }
    else { ocultoAutor[v] = true; chip.classList.remove('ativo'); }
    aplica();
  });
});
})();
</script>"""


def _tarefas(con):
    tarefas = _tabela(
        ["id", "tarefa", "responsável", "prazo", "status", "branch"],
        con.execute(
        "SELECT id, titulo, resp, prazo, status, branch FROM tarefa "
        "ORDER BY status, prazo NULLS LAST, id").fetchall(),
        "Nenhuma tarefa registrada.")
    pendencias = _tabela(
        ["id", "pendência", "aberta em", "status", "resolução"], con.execute(
        "SELECT id, titulo, strftime(criado_em, '%Y-%m-%d %H:%M'), status, "
        "resolucao FROM pendencia ORDER BY status, criado_em, id").fetchall(),
        "Nenhuma pendência registrada.")
    return (f'{tarefas}<h2>Pendências</h2>'
            f'<p class="nota">Pendência é o que trava o projeto e depende de '
            f'terceiro ou de definição. Uma pendência aberta há muito tempo '
            f'reprova o selo de auditoria.</p>'
            f'{pendencias}')


def _lista_links(con, sql, params, vazio="sem registros ainda"):
    linhas = con.execute(sql, params).fetchall()
    if not linhas:
        return f'<p class="limpo">{_esc(vazio)}</p>'
    itens = "".join(
        f'<li><a href="index.html#{_esc(eid)}">{_esc(titulo)}</a></li>'
        for eid, titulo in linhas)
    return f'<ul class="lista">{itens}</ul>'


def _integrante(con, nome):
    abertas = _lista_links(con,
        "SELECT id, titulo FROM tarefa WHERE resp = ? AND status = 'aberta' "
        "ORDER BY prazo NULLS LAST, id", [nome])
    concluidas = _lista_links(con,
        "SELECT id, titulo FROM tarefa WHERE resp = ? AND status <> 'aberta' "
        "ORDER BY id", [nome])
    pendencias = _lista_links(con,
        "SELECT id, titulo FROM pendencia WHERE criado_por = ? "
        "ORDER BY criado_em, id", [nome])
    registros = _lista_links(con,
        "SELECT n.entidade_id, coalesce(n.payload->>'titulo', "
        "n.payload->>'variante', n.payload->>'proposito', n.entidade_id) "
        "FROM no n JOIN criacao c USING (entidade_id) WHERE c.criado_por = ? "
        "ORDER BY c.criado_em DESC, n.entidade_id DESC LIMIT 5", [nome])
    return (f'<section class="integrante">'
            f'<h2>{_esc(nome)}</h2>'
            f'<h3>Tarefas abertas</h3>{abertas}'
            f'<h3>Tarefas concluídas</h3>{concluidas}'
            f'<h3>Pendências criadas</h3>{pendencias}'
            f'<h3>Últimos registros</h3>{registros}'
            f'</section>')


def _integrantes(con):
    nomes = list(dict.fromkeys(json.loads(INTEGRANTES.read_text()).values()))
    return "".join(_integrante(con, nome) for nome in nomes)


def _ia(con, m):
    p = m["postura"]
    indices = (f'<dl class="indices">'
               f'<dt>Taxa de aceite integral</dt>'
               f'<dd{_alerta(p["total"] and p["taxa_integral"] == 100)}>'
               f'{_pc(p["taxa_integral"])}</dd>'
               f'<dt>Aceitas integralmente</dt><dd>{p["integral"]}</dd>'
               f'<dt>Aceitas em parte</dt><dd>{p["parcial"]}</dd>'
               f'<dt>Descartadas</dt><dd>{p["descarte"]}</dd></dl>')
    tabela = _tabela(
        ["quando", "quem", "propósito", "modelo", "aceito", "crítica humana"],
        [(q, quem, prop, mod, _ACEITE.get(ac, ac), cr) for
         q, quem, prop, mod, ac, cr in con.execute(
            "SELECT strftime(criado_em, '%Y-%m-%d %H:%M'), criado_por, "
            "proposito, modelo, aceito, critica FROM ia "
            "ORDER BY criado_em DESC, id DESC").fetchall()],
        "Nenhuma interação com IA registrada.")
    return (f'{indices}<p class="nota">Taxa próxima de 100% não é sinal de '
            f'eficiência: é sinal de ausência de revisão, e será examinada na '
            f'arguição. Não se registra interação sem crítica humana.</p>'
            f'<h2>Registros</h2>{tabela}')


def _experimentos(con):
    return _tabela(
        ["id", "variante", "parametros", "obj", "gap", "tempo (s)", "commit",
         "hipótese", "conclusão"],
        con.execute("SELECT id, variante, parametros, obj, gap, tempo_s, "
                    "commit_sha, hipotese, conclusao FROM experimento "
                    "ORDER BY criado_em, id").fetchall(),
        "Nenhum experimento registrado. Cada rodada do modelo entra por "
        "./gov experimento, com parâmetros, valor da função objetivo, gap e "
        "tempo de solução.")


def _resultados(con):
    arquivos = _tabela(["id", "arquivo", "descrição"], con.execute(
        "SELECT id, caminho, descricao FROM arquivo ORDER BY caminho, id"
    ).fetchall(), "Nenhum artefato registrado.")
    fontes = _tabela(["fonte", "origem", "formato", "cobertura", "limitações"],
                     con.execute(
        "SELECT nome, origem, formato, cobertura, limitacoes FROM fonte "
        "ORDER BY nome, id").fetchall(), "Nenhuma fonte registrada.")
    refs = _tabela(["citação", "url", "doi"], con.execute(
        "SELECT citacao, url, doi FROM referencia ORDER BY citacao, id"
    ).fetchall(), "Nenhuma referencia registrada.")
    return (f'<p>Esta folha não mostra número que não esteja no banco. Mapas, '
            f'fronteira de implantação e análise de sensibilidade aparecem aqui '
            f'quando a camada de Pesquisa Operacional produzir os artefatos e '
            f'eles forem registrados por <code>./gov arquivo</code>.</p>'
            f'<h2>Artefatos</h2>{arquivos}'
            f'<h2>Fontes de dados</h2>{fontes}'
            f'<h2>Referências</h2>{refs}')


def _reprodutibilidade():
    return ('<p>Qualquer pessoa deve conseguir rodar o projeto do zero. O banco '
            'binário não é versionado: ele é reconstruído do arquivo '
            '<code>governanca/dump.sql</code>, que é append-only e a fonte de '
            'verdade em git.</p><pre>'
            'git clone https://github.com/Projeto-TRA-48-Grupo-1/'
            'TRA-48_Projeto.git\ncd TRA-48_Projeto\n'
            'python3 -m venv governanca/.venv\n'
            'governanca/.venv/bin/pip install -r governanca/requirements.txt\n'
            './gov rebuild\n./gov status\n./gov auditoria\n./gov update\n'
            'Rscript app/01-carrega.R</pre>'
            '<h2>Regra do projeto</h2>'
            '<p>O que não estiver no banco, não aconteceu. A escrita passa '
            'sempre pelo <code>./gov</code>, que recusa decisão sem '
            'justificativa, fonte sem limitações, tarefa sem responsável e '
            'interação com IA sem crítica humana. A leitura sai do '
            '<code>./gov consulta</code>.</p>'
            '<h2>Tipografia</h2>'
            '<p>B612, desenhada pela Airbus para telas de cockpit, sob licença '
            'SIL Open Font License 1.1. O texto da licença acompanha os '
            'arquivos em <code>fontes/</code>. Esta folha não busca nada na '
            'rede.</p>')


def gera(destino=None):
    destino = Path(destino) if destino else DESTINO
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = banco.conecta()
    m = auditoria.calcula(con)
    m["registros"] = con.execute("SELECT count(*) FROM evento").fetchone()[0]
    m["revisao"] = con.execute(
        "SELECT coalesce(strftime(max(ts), '%Y-%m-%d'), 'sem registro') "
        "FROM evento").fetchone()[0]
    corpos = {
        "index.html": grafo.pagina_home(con),
        "estado.html": _estado(con, m),
        "trilha.html": _trilha(con),
        "tarefas.html": _tarefas(con),
        "integrantes.html": _integrantes(con),
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
            (tmp / arquivo).write_text(
                _pagina(arquivo, titulo, corpos[arquivo], m),
                encoding="utf-8")
        (tmp / "grafo.html").write_text(GRAFO_REDIRECT, encoding="utf-8")
        (tmp / "estilo.css").write_text(ESTILO, encoding="utf-8")
        (tmp / ".nojekyll").write_text("", encoding="utf-8")
        if FONTES.is_dir():
            shutil.copytree(FONTES, tmp / "fontes")
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
