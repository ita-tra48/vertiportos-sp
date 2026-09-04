import json
from html import escape

import banco

FAIXAS = ["meta", "decisao", "experimento", "fonte", "referencia",
          "arquivo", "tarefa", "pendencia", "ia"]
CORES = {"meta": "#14457f", "decisao": "#5a3a92", "experimento": "#1f5c3d",
         "fonte": "#7a4a12", "referencia": "#0f5b6b", "arquivo": "#4a5560",
         "tarefa": "#8a6a10", "pendencia": "#ab2118", "ia": "#8c2f6d"}
SIGLAS = {"meta": "MT", "decisao": "DC", "experimento": "EX", "fonte": "FO",
          "referencia": "RF", "arquivo": "AQ", "tarefa": "TF",
          "pendencia": "PD", "ia": "IA"}
ROTULOS = {"meta": "metas", "decisao": "decisões",
           "experimento": "experimentos", "fonte": "fontes de dados",
           "referencia": "referências", "arquivo": "arquivos",
           "tarefa": "tarefas", "pendencia": "pendências",
           "ia": "interações com IA"}
LARGURA_COLUNA = 240
ALTURA_FAIXA = 110
RAIO = 9
MARGEM = 40


def coleta(con):
    nos = [{"id": r[0], "tipo": r[1], "rotulo": r[2] or r[0]}
           for r in con.execute(
               "SELECT entidade_id, tipo, coalesce("
               "payload->>'titulo', payload->>'variante', "
               "payload->>'proposito') FROM no "
               "WHERE payload->>'interno' IS DISTINCT FROM 'true' "
               "ORDER BY tipo, entidade_id"
           ).fetchall()]
    ids = {n["id"] for n in nos}
    arestas = [{"origem": r[0], "relacao": r[1], "destino": r[2]}
               for r in con.execute(
                   "SELECT origem, relacao, destino FROM aresta "
                   "ORDER BY origem, relacao, destino").fetchall()
               if r[0] in ids and r[2] in ids]
    return nos, arestas


def posiciona(nos):
    pos = {}
    for faixa, tipo in enumerate(FAIXAS):
        deste = [n for n in nos if n["tipo"] == tipo]
        for coluna, no in enumerate(deste):
            pos[no["id"]] = (MARGEM + 160 + coluna * LARGURA_COLUNA,
                             MARGEM + faixa * ALTURA_FAIXA)
    return pos


def _corta(texto, limite=24):
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def svg(con):
    nos, arestas = coleta(con)
    pos = posiciona(nos)
    colunas = max([1] + [1 + (pos[n["id"]][0] - MARGEM - 160) // LARGURA_COLUNA
                         for n in nos])
    largura = MARGEM * 2 + 160 + colunas * LARGURA_COLUNA
    altura = MARGEM + (len(FAIXAS) - 1) * ALTURA_FAIXA + 60
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" id="grafo" '
              f'viewBox="0 0 {largura} {altura}" width="100%" '
              f'height="{altura}" font-family="B612M, ui-monospace, monospace">']
    partes.append('<g id="camada">')
    for faixa, tipo in enumerate(FAIXAS):
        y = MARGEM + faixa * ALTURA_FAIXA
        partes.append(
            f'<text x="{MARGEM}" y="{y + 4}" font-size="13" '
            f'fill="{CORES[tipo]}" font-weight="700">'
            f'{escape(ROTULOS.get(tipo, tipo))}</text>')
        partes.append(
            f'<line x1="{MARGEM}" y1="{y + 16}" x2="{largura - MARGEM}" '
            f'y2="{y + 16}" stroke="#c3c9d1" stroke-width="1"/>')
    for aresta in arestas:
        origem, destino = pos.get(aresta["origem"]), pos.get(aresta["destino"])
        if not origem or not destino:
            continue
        if origem[1] == destino[1]:
            meio_y = origem[1] - ALTURA_FAIXA / 3
        else:
            meio_y = (origem[1] + destino[1]) / 2
        partes.append(
            f'<path d="M {origem[0]} {origem[1]} C {origem[0]} {meio_y} '
            f'{destino[0]} {meio_y} {destino[0]} {destino[1]}" fill="none" '
            f'stroke="#98a1ab" stroke-width="1.2" opacity="0.8"/>')
        partes.append(
            f'<text x="{(origem[0] + destino[0]) / 2}" y="{meio_y - 3}" '
            f'font-size="9" fill="#5c646d" text-anchor="middle" '
            f'paint-order="stroke" stroke="#fbfbf9" stroke-width="3" '
            f'stroke-linejoin="round">{escape(aresta["relacao"])}</text>')
    for no in nos:
        x, y = pos[no["id"]]
        cor = CORES.get(no["tipo"], "#4a5560")
        partes.append(
            f'<a href="trilha.html#{escape(no["id"])}">'
            f'<circle cx="{x}" cy="{y}" r="{RAIO}" fill="{cor}" '
            f'stroke="#fbfbf9" stroke-width="2"><title>'
            f'{escape(no["id"])} — {escape(no["rotulo"])}</title></circle>'
            f'<text x="{x + RAIO + 6}" y="{y + 4}" font-size="11" '
            f'fill="#14181c">{escape(_corta(no["rotulo"]))}</text></a>')
    partes.append("</g></svg>")
    return "\n".join(partes)


CONCLUIDOS = {"concluida", "feita", "resolvida", "encerrada"}
LARGURA_HOME = 960
ALTURA_HOME = 640


def dados_nos(con):
    linhas = con.execute(
        "SELECT n.entidade_id, n.tipo, c.criado_por, "
        "strftime(c.criado_em, '%Y-%m-%d %H:%M'), n.payload, c.criado_em "
        "FROM no n JOIN criacao c USING (entidade_id) "
        "WHERE n.payload->>'interno' IS DISTINCT FROM 'true' "
        "ORDER BY n.entidade_id").fetchall()
    arestas = con.execute(
        "SELECT origem, relacao, destino FROM aresta "
        "ORDER BY origem, relacao, destino").fetchall()
    status_por_id = {}
    nos = []
    nascimento = {}
    for eid, tipo, autor, criado_em, payload_bruto, ts in linhas:
        nascimento[eid] = ts
        payload = json.loads(payload_bruto)
        status = payload.get("status")
        status_por_id[eid] = status
        titulo = (payload.get("titulo") or payload.get("variante")
                 or payload.get("proposito") or eid)
        campos = {k: v for k, v in payload.items()
                 if k not in ("titulo", "status")}
        nos.append({"id": eid, "tipo": tipo, "titulo": titulo,
                    "autor": autor, "criado_em": criado_em,
                    "status": status, "campos": campos})
    ids = {n["id"] for n in nos}
    bloqueados = {destino for origem, relacao, destino in arestas
                 if relacao == "bloqueia" and status_por_id.get(origem) == "aberta"}
    for no in nos:
        no["concluido"] = no["status"] in CONCLUIDOS and no["id"] not in bloqueados
    arestas_saida = [{"origem": o, "relacao": r, "destino": d}
                     for o, r, d in arestas if o in ids and d in ids]
    numera(nos, nascimento)
    grau = {n["id"]: 0 for n in nos}
    for a in arestas_saida:
        grau[a["origem"]] += 1
        grau[a["destino"]] += 1
    for no in nos:
        no["grau"] = grau[no["id"]]
    return nos, arestas_saida


def numera(nos, nascimento):
    contagem = {}
    for no in sorted(nos, key=lambda n: (nascimento[n["id"]], n["id"])):
        ordem = contagem[no["tipo"]] = contagem.get(no["tipo"], 0) + 1
        no["sigla"] = f'{SIGLAS.get(no["tipo"], no["tipo"][:2].upper())}{ordem}'


def json_dados(con):
    nos, arestas = dados_nos(con)
    bruto = json.dumps(
        {"nos": nos, "arestas": arestas, "cores": CORES, "rotulos": ROTULOS,
         "siglas": SIGLAS},
        ensure_ascii=False, sort_keys=True)
    return bruto.replace("</", "<\\/")


def _controles():
    campos = "".join(
        f'<label><span>{rotulo}</span>'
        f'<input type="range" id="{alvo}" min="{minimo}" max="{maximo}" '
        f'step="{passo}" value="{valor}"></label>'
        for alvo, rotulo, minimo, maximo, passo, valor in (
            ("grafo-repulsao", "repulsão", 800, 14000, 200, 4200),
            ("grafo-distancia", "distância da ligação", 50, 320, 10, 110),
            ("grafo-centro", "força ao centro", 0, 10, 1, 2)))
    return (f'<details class="grafo-controles"><summary>Forças</summary>'
            f'<div>{campos}</div></details>')



def _legenda():
    chips = "".join(
        f'<button type="button" class="grafo-chip ativo" data-tipo="{tipo}">'
        f'<span class="ponto" style="background:{CORES[tipo]}"></span>'
        f'{escape(ROTULOS[tipo])}</button>'
        for tipo in FAIXAS)
    return f'<div class="grafo-legenda" id="grafo-legenda">{chips}</div>'


def _filtros():
    itens = "".join(
        f'<button type="button" class="grafo-status'
        f'{" ativo" if valor == "todos" else ""}" data-status="{valor}">'
        f'{rotulo}</button>'
        for valor, rotulo in (("todos", "Todos"), ("abertos", "Abertos"),
                              ("concluidos", "Concluídos")))
    return (f'<div class="grafo-filtros" id="grafo-filtros">{itens}'
            f'{_controles()}</div>')




ESTILO_HOME = """
.grafo-legenda{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:calc(var(--u)*1.5)}
.grafo-chip{display:inline-flex;align-items:center;gap:6px;
border:1px solid var(--fio-forte);background:var(--papel);padding:4px 10px;
font:700 .72rem/1.4 var(--mono);letter-spacing:.04em;text-transform:uppercase;
color:var(--nanquim2);cursor:pointer}
.grafo-chip.ativo{background:var(--anil-fraco);color:var(--nanquim);
border-color:var(--anil)}
.grafo-chip .ponto{width:10px;height:10px;border-radius:50%;display:inline-block}
.grafo-filtros{display:flex;flex-wrap:wrap;gap:6px;align-items:center;
margin-bottom:calc(var(--u)*2)}
.grafo-status{border:1px solid var(--fio-forte);background:var(--papel);
padding:4px 10px;font:700 .72rem/1.4 var(--mono);text-transform:uppercase;
letter-spacing:.04em;color:var(--nanquim2);cursor:pointer}
.grafo-status.ativo{background:var(--carimbo-fraco);color:var(--nanquim);
border-color:var(--carimbo)}
.grafo-controles{margin-left:auto;position:relative;
font:.72rem/1.4 var(--mono)}
.grafo-controles summary{border:1px solid var(--fio-forte);padding:4px 10px;
text-transform:uppercase;letter-spacing:.04em;color:var(--nanquim2);
cursor:pointer;list-style:none}
.grafo-controles summary::-webkit-details-marker{display:none}
.grafo-controles[open] summary{background:var(--anil-fraco);
border-color:var(--anil);color:var(--nanquim)}
.grafo-controles>div{position:absolute;right:0;top:100%;z-index:5;
min-width:23rem;border:1px solid var(--anil);background:var(--papel);
padding:10px 12px;display:grid;gap:8px;
box-shadow:0 6px 20px rgba(20,24,28,.12)}
.grafo-controles label{display:grid;grid-template-columns:11rem 1fr;
gap:8px;align-items:center;color:var(--nanquim2)}
.grafo-quadro{display:grid;grid-template-columns:1fr 21rem;
border:1px solid var(--fio);height:min(78vh,760px)}
.grafo-palco{background:#fdfdfc;overflow:hidden;min-width:0}
.grafo-palco svg{width:100%;height:100%;touch-action:none;
cursor:grab;display:block}
.grafo-palco svg.arrastando{cursor:grabbing}
.grafo-tooltip{position:fixed;pointer-events:none;background:var(--nanquim);
color:var(--papel);font:.78rem/1.4 var(--mono);padding:6px 9px;
border:1px solid var(--nanquim);max-width:26rem;z-index:20}
.grafo-tooltip b{display:block;font:700 .82rem/1.4 var(--sans)}
.grafo-tooltip span{opacity:.75}
.grafo-ficha{border-left:1px solid var(--fio);background:var(--papel);
overflow-y:auto;padding:calc(var(--u)*2);font-size:.84rem;min-width:0}
.grafo-ficha .vazia{color:var(--grafite);font-size:.8rem;margin:0}
.grafo-ficha h3{margin:8px 0 10px;font:700 .95rem/1.35 var(--sans)}
.grafo-ficha h4{margin:calc(var(--u)*2) 0 6px;font:700 .7rem/1.4 var(--mono);
letter-spacing:.1em;text-transform:uppercase;color:var(--nanquim2);
border-bottom:1px solid var(--fio);padding-bottom:4px}
.grafo-ficha dl{margin:0;display:grid;grid-template-columns:6.5rem 1fr;
gap:3px 8px}
.grafo-ficha dt{font:700 .66rem/1.6 var(--mono);letter-spacing:.05em;
text-transform:uppercase;color:var(--nanquim2)}
.grafo-ficha dd{margin:0;overflow-wrap:anywhere}
.grafo-ficha ul{margin:2px 0 0;padding-left:1.1em}
.grafo-cabeca{display:flex;align-items:center;gap:8px}
.grafo-selo{display:inline-block;padding:2px 7px;border:1px solid currentColor;
font:700 .74rem/1.5 var(--mono);letter-spacing:.06em}
.grafo-elo{display:block;width:100%;text-align:left;background:none;
border:0;border-bottom:1px solid var(--fio);padding:5px 0;cursor:pointer;
font:inherit;color:var(--nanquim);display:grid;
grid-template-columns:3.4rem 5.5rem 1fr;gap:6px;align-items:baseline}
.grafo-elo:hover{background:var(--anil-fraco)}
.grafo-elo .rel{font:700 .66rem/1.5 var(--mono);letter-spacing:.05em;
text-transform:uppercase;color:var(--anil)}
.grafo-elo .alvo{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.grafo-trilha{display:inline-block;margin-top:calc(var(--u)*2);
font:.72rem/1.5 var(--mono)}
.grafo-no{cursor:pointer}
.grafo-rotulo{font:700 10px/1 var(--mono);fill:var(--nanquim2);
text-anchor:middle;pointer-events:none;transition:opacity .18s}
.grafo-sem-rotulo .grafo-rotulo{opacity:0}
.grafo-apagado{opacity:.12}
.grafo-no.grafo-brilho{animation:grafobrilho 2.4s ease-in-out infinite}
@keyframes grafobrilho{0%,100%{filter:drop-shadow(0 0 0 currentColor)}
50%{filter:drop-shadow(0 0 6px currentColor)}}
@media(prefers-reduced-motion:reduce){.grafo-no.grafo-brilho{animation:none}}
@media(max-width:900px){
.grafo-quadro{grid-template-columns:1fr;height:auto}
.grafo-palco{height:60vh}
.grafo-ficha{border-left:0;border-top:1px solid var(--fio);max-height:40vh}
.grafo-controles{margin-left:0}}
"""

_SCRIPT_HOME = """<script>
(function(){
var DADOS = DADOS_GRAFO;
var svg = document.getElementById('grafo-svg');
var camera = document.getElementById('grafo-camera');
var camadaArestas = document.getElementById('grafo-arestas');
var camadaNos = document.getElementById('grafo-nos');
var tooltip = document.getElementById('grafo-tooltip');
var ficha = document.getElementById('grafo-ficha');
var LARGURA = 960, ALTURA = 640, ZOOM_MIN = 0.3, ZOOM_MAX = 4;
var LIMIAR_ROTULO = 0.45;
var forcas = {repulsao: 4200, distancia: 110, centro: 0.002};
function hash(texto){
  var h = 5381;
  for (var i = 0; i < texto.length; i++) { h = ((h * 33) ^ texto.charCodeAt(i)) >>> 0; }
  return h;
}
var nos = {};
DADOS.nos.forEach(function(no){
  var angulo = (hash(no.id) % 360) * Math.PI / 180;
  var raio = 60 + (hash(no.id + '#raio') % 220);
  nos[no.id] = Object.assign({}, no, {
    x: LARGURA / 2 + raio * Math.cos(angulo),
    y: ALTURA / 2 + raio * Math.sin(angulo),
    vx: 0, vy: 0, fixo: false
  });
});
var ids = Object.keys(nos);
var arestas = DADOS.arestas.filter(function(a){
  return nos[a.origem] && nos[a.destino];
});
var vizinhos = {}, saindo = {}, entrando = {};
ids.forEach(function(id){
  vizinhos[id] = new Set(); saindo[id] = []; entrando[id] = [];
});
arestas.forEach(function(a){
  vizinhos[a.origem].add(a.destino);
  vizinhos[a.destino].add(a.origem);
  saindo[a.origem].push(a);
  entrando[a.destino].push(a);
});
function raioDe(no){ return 6 + Math.min(9, Math.sqrt(no.grau || 0) * 2.6); }
var NS = 'http://www.w3.org/2000/svg';
var elLinha = [], elGrupo = {};
arestas.forEach(function(){
  var linha = document.createElementNS(NS, 'line');
  linha.setAttribute('stroke', '#98a1ab');
  linha.setAttribute('stroke-width', '1.2');
  linha.setAttribute('marker-end', 'url(#grafo-seta)');
  camadaArestas.appendChild(linha);
  elLinha.push(linha);
});
function ajustaViewBox(){
  var r = svg.getBoundingClientRect();
  if (!r.width || !r.height) { return; }
  LARGURA = Math.round(r.width);
  ALTURA = Math.round(r.height);
  svg.setAttribute('viewBox', '0 0 ' + LARGURA + ' ' + ALTURA);
}
var cam = {x: 0, y: 0, k: 1};
function aplicaCamera(){
  camera.setAttribute('transform',
    'translate(' + cam.x + ' ' + cam.y + ') scale(' + cam.k + ')');
  camadaNos.classList.toggle('grafo-sem-rotulo', cam.k < LIMIAR_ROTULO);
}
function ponto(elemento, cx, cy){
  var pt = svg.createSVGPoint();
  pt.x = cx; pt.y = cy;
  return pt.matrixTransform(elemento.getScreenCTM().inverse());
}
function pontoMundo(cx, cy){ return ponto(camera, cx, cy); }
function zoom(fator, cx, cy){
  var antes = pontoMundo(cx, cy);
  cam.k = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, cam.k * fator));
  aplicaCamera();
  var depois = pontoMundo(cx, cy);
  cam.x += (depois.x - antes.x) * cam.k;
  cam.y += (depois.y - antes.y) * cam.k;
  aplicaCamera();
}
function enquadra(){
  ajustaViewBox();
  var caixa = camera.getBBox();
  if (!caixa.width || !caixa.height) { return; }
  var margem = 20;
  cam.k = Math.min(1.4, Math.max(ZOOM_MIN,
    Math.min((LARGURA - margem * 2) / caixa.width,
             (ALTURA - margem * 2) / caixa.height)));
  cam.x = LARGURA / 2 - cam.k * (caixa.x + caixa.width / 2);
  cam.y = ALTURA / 2 - cam.k * (caixa.y + caixa.height / 2);
  aplicaCamera();
}
svg.addEventListener('wheel', function(e){
  e.preventDefault();
  zoom(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
}, {passive: false});
var panX = 0, panY = 0, panicando = false;
svg.addEventListener('pointerdown', function(e){
  if (e.target.id !== 'grafo-fundo') { return; }
  panicando = true; panX = e.clientX; panY = e.clientY;
  svg.classList.add('arrastando');
  svg.setPointerCapture(e.pointerId);
});
svg.addEventListener('pointermove', function(e){
  if (!panicando) { return; }
  var a = ponto(svg, panX, panY), b = ponto(svg, e.clientX, e.clientY);
  cam.x += b.x - a.x; cam.y += b.y - a.y;
  panX = e.clientX; panY = e.clientY;
  aplicaCamera();
});
svg.addEventListener('pointerup', function(e){
  if (!panicando) { return; }
  panicando = false;
  svg.classList.remove('arrastando');
  if (Math.abs(e.clientX - panX) < 3 && Math.abs(e.clientY - panY) < 3) {
    abre(null);
  }
});
function escondeTooltip(){ tooltip.hidden = true; }
function mostraTooltip(id, e){
  var no = nos[id];
  tooltip.textContent = '';
  var nome = document.createElement('b');
  nome.textContent = no.titulo;
  var meta = document.createElement('span');
  meta.textContent = no.sigla + ' · ' + (DADOS.rotulos[no.tipo] || no.tipo)
    + ' · ' + no.id + (no.status ? ' · ' + no.status : '');
  tooltip.appendChild(nome);
  tooltip.appendChild(meta);
  tooltip.hidden = false;
  if (e && typeof e.clientX === 'number') {
    tooltip.style.left = (e.clientX + 14) + 'px';
    tooltip.style.top = (e.clientY + 14) + 'px';
  } else {
    var r = elGrupo[id].getBoundingClientRect();
    tooltip.style.left = (r.left + r.width + 8) + 'px';
    tooltip.style.top = (r.top + r.height + 8) + 'px';
  }
}
var selecionado = null, focado = null;
function aplicaDestaque(){
  var alvo = focado || selecionado;
  ids.forEach(function(id){
    var aceso = !alvo || id === alvo || vizinhos[alvo].has(id);
    elGrupo[id].classList.toggle('grafo-apagado', !aceso);
  });
  arestas.forEach(function(a, i){
    var aceso = !alvo || a.origem === alvo || a.destino === alvo;
    elLinha[i].classList.toggle('grafo-apagado', !aceso);
  });
}
function linhaDl(dl, rotulo, valor){
  if (valor === undefined || valor === null || valor === '') { return; }
  var dt = document.createElement('dt');
  dt.textContent = rotulo;
  var dd = document.createElement('dd');
  if (Array.isArray(valor)) {
    var ul = document.createElement('ul');
    valor.forEach(function(x){
      var li = document.createElement('li');
      li.textContent = typeof x === 'object' ? JSON.stringify(x) : x;
      ul.appendChild(li);
    });
    if (!valor.length) { return; }
    dd.appendChild(ul);
  } else if (typeof valor === 'object') {
    dd.textContent = JSON.stringify(valor);
  } else {
    dd.textContent = valor;
  }
  dl.appendChild(dt); dl.appendChild(dd);
}
function botaoElo(relacao, outro, direcao){
  var b = document.createElement('button');
  b.type = 'button';
  b.className = 'grafo-elo';
  var selo = document.createElement('span');
  selo.className = 'grafo-selo';
  selo.style.color = DADOS.cores[nos[outro].tipo] || '#4a5560';
  selo.textContent = nos[outro].sigla;
  var rel = document.createElement('span');
  rel.className = 'rel';
  rel.textContent = (direcao === 'saida' ? '→ ' : '← ') + relacao;
  var alvo = document.createElement('span');
  alvo.className = 'alvo';
  alvo.textContent = nos[outro].titulo;
  alvo.title = nos[outro].titulo;
  b.appendChild(selo); b.appendChild(rel); b.appendChild(alvo);
  b.addEventListener('click', function(){ abre(outro); });
  return b;
}
function desenhaFicha(id){
  ficha.textContent = '';
  if (!id) {
    var vazia = document.createElement('p');
    vazia.className = 'vazia';
    vazia.textContent = 'Clique num nó para abrir a ficha. Passe o mouse '
      + 'para ver o nome e acender a vizinhança.';
    ficha.appendChild(vazia);
    return;
  }
  var no = nos[id];
  var cabeca = document.createElement('div');
  cabeca.className = 'grafo-cabeca';
  var selo = document.createElement('span');
  selo.className = 'grafo-selo';
  selo.style.color = DADOS.cores[no.tipo] || '#4a5560';
  selo.textContent = no.sigla;
  var ident = document.createElement('span');
  ident.className = 'ident';
  ident.textContent = no.id;
  cabeca.appendChild(selo); cabeca.appendChild(ident);
  ficha.appendChild(cabeca);
  var titulo = document.createElement('h3');
  titulo.textContent = no.titulo;
  ficha.appendChild(titulo);
  var dl = document.createElement('dl');
  linhaDl(dl, 'tipo', DADOS.rotulos[no.tipo] || no.tipo);
  linhaDl(dl, 'autor', no.autor);
  linhaDl(dl, 'data', no.criado_em);
  linhaDl(dl, 'status', no.status);
  Object.keys(no.campos || {}).sort().forEach(function(chave){
    linhaDl(dl, chave, no.campos[chave]);
  });
  ficha.appendChild(dl);
  var elos = saindo[id].map(function(a){
    return botaoElo(a.relacao, a.destino, 'saida');
  }).concat(entrando[id].map(function(a){
    return botaoElo(a.relacao, a.origem, 'entrada');
  }));
  var h4 = document.createElement('h4');
  h4.textContent = 'Ligações (' + elos.length + ')';
  ficha.appendChild(h4);
  if (elos.length) {
    elos.forEach(function(b){ ficha.appendChild(b); });
  } else {
    var so = document.createElement('p');
    so.className = 'vazia';
    so.textContent = 'Nó órfão: nenhuma ligação registrada.';
    ficha.appendChild(so);
  }
  var link = document.createElement('a');
  link.className = 'grafo-trilha';
  link.href = 'trilha.html#' + encodeURIComponent(id);
  link.textContent = 'ver registro na trilha →';
  ficha.appendChild(link);
}
function abre(id){
  selecionado = id;
  desenhaFicha(id);
  aplicaDestaque();
  ficha.scrollTop = 0;
}
ids.forEach(function(id){
  var no = nos[id];
  var rotuloTipo = DADOS.rotulos[no.tipo] || no.tipo;
  var g = document.createElementNS(NS, 'g');
  g.setAttribute('class', 'grafo-no' + (no.concluido ? ' grafo-brilho' : ''));
  g.setAttribute('tabindex', '0');
  g.setAttribute('role', 'button');
  g.setAttribute('aria-label', no.sigla + ': ' + no.titulo + ' (' + rotuloTipo + ')');
  g.style.color = DADOS.cores[no.tipo] || '#4a5560';
  var tituloSvg = document.createElementNS(NS, 'title');
  tituloSvg.textContent = no.sigla + ' — ' + no.titulo;
  var circulo = document.createElementNS(NS, 'circle');
  circulo.setAttribute('r', raioDe(no));
  circulo.setAttribute('fill', DADOS.cores[no.tipo] || '#4a5560');
  circulo.setAttribute('stroke', '#fbfbf9');
  circulo.setAttribute('stroke-width', '2');
  var texto = document.createElementNS(NS, 'text');
  texto.setAttribute('class', 'grafo-rotulo');
  texto.setAttribute('y', raioDe(no) + 10);
  texto.textContent = no.sigla;
  g.appendChild(tituloSvg);
  g.appendChild(circulo);
  g.appendChild(texto);
  camadaNos.appendChild(g);
  elGrupo[id] = g;
  var arrastando = false, moveu = false, px = 0, py = 0;
  g.addEventListener('pointerdown', function(e){
    e.stopPropagation();
    arrastando = true; moveu = false; px = e.clientX; py = e.clientY;
    no.fixo = true;
    g.setPointerCapture(e.pointerId);
    acorda();
  });
  g.addEventListener('pointermove', function(e){
    if (!arrastando) { mostraTooltip(id, e); return; }
    if (Math.abs(e.clientX - px) > 3 || Math.abs(e.clientY - py) > 3) { moveu = true; }
    var p = pontoMundo(e.clientX, e.clientY);
    no.x = p.x; no.y = p.y; no.vx = 0; no.vy = 0;
  });
  g.addEventListener('pointerup', function(){
    arrastando = false; no.fixo = false; acorda();
    if (!moveu) { abre(id); }
  });
  g.addEventListener('pointerenter', function(e){
    focado = id; aplicaDestaque(); mostraTooltip(id, e);
  });
  g.addEventListener('pointerleave', function(){
    focado = null; aplicaDestaque(); escondeTooltip();
  });
  g.addEventListener('focus', function(e){
    focado = id; aplicaDestaque(); mostraTooltip(id, e);
  });
  g.addEventListener('blur', function(){
    focado = null; aplicaDestaque(); escondeTooltip();
  });
  g.addEventListener('keydown', function(e){
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abre(id); }
  });
});
var ocultos = {};
var filtroStatus = 'todos';
function visivel(no){
  if (ocultos[no.tipo]) { return false; }
  if (filtroStatus === 'abertos' && no.concluido) { return false; }
  if (filtroStatus === 'concluidos' && !no.concluido) { return false; }
  return true;
}
function aplicaFiltros(){
  escondeTooltip();
  ids.forEach(function(id){
    elGrupo[id].style.display = visivel(nos[id]) ? '' : 'none';
  });
  arestas.forEach(function(a, i){
    var ok = visivel(nos[a.origem]) && visivel(nos[a.destino]);
    elLinha[i].style.display = ok ? '' : 'none';
  });
}
document.querySelectorAll('.grafo-chip').forEach(function(chip){
  chip.addEventListener('click', function(){
    var tipo = chip.dataset.tipo;
    if (ocultos[tipo]) { delete ocultos[tipo]; chip.classList.add('ativo'); }
    else { ocultos[tipo] = true; chip.classList.remove('ativo'); }
    aplicaFiltros();
  });
});
document.querySelectorAll('.grafo-status').forEach(function(botao){
  botao.addEventListener('click', function(){
    filtroStatus = botao.dataset.status;
    document.querySelectorAll('.grafo-status').forEach(function(b){
      b.classList.remove('ativo');
    });
    botao.classList.add('ativo');
    aplicaFiltros();
  });
});
function liga(id, chave, escala){
  var campo = document.getElementById(id);
  if (!campo) { return; }
  campo.addEventListener('input', function(){
    forcas[chave] = Number(campo.value) * escala;
    acorda();
  });
}
liga('grafo-repulsao', 'repulsao', 1);
liga('grafo-distancia', 'distancia', 1);
liga('grafo-centro', 'centro', 0.001);
var quadro = 0, rodando = false, MAX_QUADROS = 300, EPS = 0.05;
function acorda(){
  quadro = 0;
  if (!rodando) { rodando = true; requestAnimationFrame(passo); }
}
function passo(){
  var maxDelta = 0;
  for (var i = 0; i < ids.length; i++) {
    for (var j = i + 1; j < ids.length; j++) {
      var a = nos[ids[i]], b = nos[ids[j]];
      var dx = b.x - a.x, dy = b.y - a.y;
      var distSq = dx * dx + dy * dy + 0.01;
      var dist = Math.sqrt(distSq);
      var forca = forcas.repulsao / distSq;
      var fx = forca * dx / dist, fy = forca * dy / dist;
      if (!a.fixo) { a.vx -= fx; a.vy -= fy; }
      if (!b.fixo) { b.vx += fx; b.vy += fy; }
    }
  }
  arestas.forEach(function(ar){
    var a = nos[ar.origem], b = nos[ar.destino];
    var dx = b.x - a.x, dy = b.y - a.y;
    var dist = Math.sqrt(dx * dx + dy * dy) || 1;
    var forca = (dist - forcas.distancia) * 0.02;
    var fx = forca * dx / dist, fy = forca * dy / dist;
    if (!a.fixo) { a.vx += fx; a.vy += fy; }
    if (!b.fixo) { b.vx -= fx; b.vy -= fy; }
  });
  ids.forEach(function(id){
    var no = nos[id];
    if (no.fixo) { return; }
    no.vx += (LARGURA / 2 - no.x) * forcas.centro;
    no.vy += (ALTURA / 2 - no.y) * forcas.centro;
    no.vx *= 0.85; no.vy *= 0.85;
    no.x += no.vx; no.y += no.vy;
    maxDelta = Math.max(maxDelta, Math.abs(no.vx), Math.abs(no.vy));
  });
  ids.forEach(function(id){
    elGrupo[id].setAttribute('transform',
      'translate(' + nos[id].x + ' ' + nos[id].y + ')');
  });
  arestas.forEach(function(ar, i){
    var a = nos[ar.origem], b = nos[ar.destino];
    var dx = b.x - a.x, dy = b.y - a.y;
    var dist = Math.sqrt(dx * dx + dy * dy) || 1;
    var ux = dx / dist, uy = dy / dist;
    var recuo = raioDe(b) + 7;
    elLinha[i].setAttribute('x1', a.x + ux * raioDe(a));
    elLinha[i].setAttribute('y1', a.y + uy * raioDe(a));
    elLinha[i].setAttribute('x2', b.x - ux * recuo);
    elLinha[i].setAttribute('y2', b.y - uy * recuo);
  });
  quadro++;
  if (acomodando) {
    if (quadro % 12 === 0) { enquadra(); }
    if (quadro >= MAX_QUADROS) { acomodando = false; enquadra(); }
  }
  var puxando = ids.some(function(id){ return nos[id].fixo; });
  if (quadro < MAX_QUADROS || maxDelta > EPS || puxando) {
    requestAnimationFrame(passo);
  } else {
    rodando = false;
  }
}
var acomodando = true;
window.addEventListener('resize', function(){ ajustaViewBox(); enquadra(); });
ajustaViewBox();
aplicaCamera();
acorda();
aplicaDestaque();
aplicaFiltros();
var alvoUrl = decodeURIComponent(window.location.hash.slice(1));
abre(alvoUrl && nos[alvoUrl] ? alvoUrl : null);
})();
</script>"""


def pagina_home(con):
    nota = ('<p class="nota">Cada nó é um registro do banco, e cada linha é '
            'uma ligação com direção. O rótulo do ponto é a sigla '
            '(<b>MT1</b> meta, <b>TF1</b> tarefa, <b>PD1</b> pendência, '
            '<b>DC1</b> decisão…); o nome inteiro aparece ao passar o mouse, '
            'que também acende a vizinhança e apaga o resto. Clique para abrir '
            'a ficha ao lado, arraste um nó para reorganizar, arraste o fundo '
            'para deslocar e use a roda para o zoom.</p>')
    palco = (f'<div class="grafo-quadro"><div class="grafo-palco">'
             f'<svg id="grafo-svg" viewBox="0 0 {LARGURA_HOME} {ALTURA_HOME}">'
             f'<defs><marker id="grafo-seta" viewBox="0 0 8 8" refX="7" '
             f'refY="4" markerWidth="5" markerHeight="5" '
             f'orient="auto-start-reverse">'
             f'<path d="M0 0 L8 4 L0 8 z" fill="#98a1ab"/></marker></defs>'
             f'<rect id="grafo-fundo" x="-4000" y="-4000" width="9000" '
             f'height="9000" fill="transparent"/>'
             f'<g id="grafo-camera"><g id="grafo-arestas"></g>'
             f'<g id="grafo-nos"></g></g></svg></div>'
             f'<aside class="grafo-ficha" id="grafo-ficha" aria-live="polite">'
             f'</aside></div>')
    return (f'{nota}{_legenda()}{_filtros()}{palco}'
            f'<div id="grafo-tooltip" class="grafo-tooltip" hidden></div>'
            f'<script>const DADOS_GRAFO = {json_dados(con)};</script>'
            f'{_SCRIPT_HOME}')
