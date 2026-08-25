import json
from html import escape

import banco

FAIXAS = ["meta", "decisao", "experimento", "fonte", "referencia",
          "arquivo", "tarefa", "pendencia", "ia"]
CORES = {"meta": "#14457f", "decisao": "#5a3a92", "experimento": "#1f5c3d",
         "fonte": "#7a4a12", "referencia": "#0f5b6b", "arquivo": "#4a5560",
         "tarefa": "#8a6a10", "pendencia": "#ab2118", "ia": "#8c2f6d"}
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
               "payload->>'proposito') FROM no ORDER BY tipo, entidade_id"
           ).fetchall()]
    arestas = [{"origem": r[0], "relacao": r[1], "destino": r[2]}
               for r in con.execute(
                   "SELECT origem, relacao, destino FROM aresta "
                   "ORDER BY origem, relacao, destino").fetchall()]
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
        "strftime(c.criado_em, '%Y-%m-%d %H:%M'), n.payload "
        "FROM no n JOIN criacao c USING (entidade_id) "
        "ORDER BY n.entidade_id").fetchall()
    arestas = con.execute(
        "SELECT origem, relacao, destino FROM aresta "
        "ORDER BY origem, relacao, destino").fetchall()
    status_por_id = {}
    nos = []
    for eid, tipo, autor, criado_em, payload_bruto in linhas:
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
    bloqueados = {destino for origem, relacao, destino in arestas
                 if relacao == "bloqueia" and status_por_id.get(origem) == "aberta"}
    for no in nos:
        no["concluido"] = no["status"] in CONCLUIDOS and no["id"] not in bloqueados
    arestas_saida = [{"origem": o, "relacao": r, "destino": d}
                     for o, r, d in arestas]
    return nos, arestas_saida


def json_dados(con):
    nos, arestas = dados_nos(con)
    bruto = json.dumps(
        {"nos": nos, "arestas": arestas, "cores": CORES, "rotulos": ROTULOS},
        ensure_ascii=False, sort_keys=True)
    return bruto.replace("</", "<\\/")


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
    return f'<div class="grafo-filtros" id="grafo-filtros">{itens}</div>'


ESTILO_HOME = """
.grafo-legenda{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:calc(var(--u)*1.5)}
.grafo-chip{display:inline-flex;align-items:center;gap:6px;
border:1px solid var(--fio-forte);background:var(--papel);padding:4px 10px;
font:700 .72rem/1.4 var(--mono);letter-spacing:.04em;text-transform:uppercase;
color:var(--nanquim2);cursor:pointer}
.grafo-chip.ativo{background:var(--anil-fraco);color:var(--nanquim);
border-color:var(--anil)}
.grafo-chip .ponto{width:10px;height:10px;border-radius:50%;display:inline-block}
.grafo-filtros{display:flex;gap:6px;margin-bottom:calc(var(--u)*2)}
.grafo-status{border:1px solid var(--fio-forte);background:var(--papel);
padding:4px 10px;font:700 .72rem/1.4 var(--mono);text-transform:uppercase;
letter-spacing:.04em;color:var(--nanquim2);cursor:pointer}
.grafo-status.ativo{background:var(--carimbo-fraco);color:var(--nanquim);
border-color:var(--carimbo)}
.grafo-palco{border:1px solid var(--fio);background:#fdfdfc;overflow:hidden;
height:min(78vh,760px)}
.grafo-palco svg{width:100%;height:100%;touch-action:none}
.grafo-tooltip{position:fixed;pointer-events:none;background:var(--nanquim);
color:var(--papel);font:.78rem/1.4 var(--mono);padding:6px 9px;
border:1px solid var(--nanquim);max-width:26rem;z-index:20}
.grafo-tooltip dl{margin:4px 0 0;display:grid;grid-template-columns:auto 1fr;
gap:2px 8px}
.grafo-tooltip dt{opacity:.7}
.grafo-tooltip dd{margin:0;overflow-wrap:anywhere}
.grafo-no{cursor:pointer}
.grafo-no.grafo-brilho{animation:grafobrilho 2.4s ease-in-out infinite}
@keyframes grafobrilho{0%,100%{filter:drop-shadow(0 0 0 currentColor)}
50%{filter:drop-shadow(0 0 6px currentColor)}}
@media(prefers-reduced-motion:reduce){.grafo-no.grafo-brilho{animation:none}}
"""

_SCRIPT_HOME = """<script>
(function(){
var DADOS = DADOS_GRAFO;
var svg = document.getElementById('grafo-svg');
var camadaArestas = document.getElementById('grafo-arestas');
var camadaNos = document.getElementById('grafo-nos');
var tooltip = document.getElementById('grafo-tooltip');
var LARGURA = 960, ALTURA = 640;
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
var arestas = DADOS.arestas.filter(function(a){
  return nos[a.origem] && nos[a.destino];
});
var vizinhos = {};
Object.keys(nos).forEach(function(id){ vizinhos[id] = new Set(); });
arestas.forEach(function(a){
  vizinhos[a.origem].add(a.destino);
  vizinhos[a.destino].add(a.origem);
});
var NS = 'http://www.w3.org/2000/svg';
var elLinha = [], elGrupo = {};
arestas.forEach(function(a){
  var linha = document.createElementNS(NS, 'line');
  linha.setAttribute('stroke', '#98a1ab');
  linha.setAttribute('stroke-width', '1.2');
  camadaArestas.appendChild(linha);
  elLinha.push(linha);
});
function pontoSvg(cx, cy){
  var pt = svg.createSVGPoint();
  pt.x = cx; pt.y = cy;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}
function escondeTooltip(){ tooltip.hidden = true; }
function posicionaTooltip(e){
  tooltip.style.left = (e.clientX + 14) + 'px';
  tooltip.style.top = (e.clientY + 14) + 'px';
}
function mostraTooltip(id, e){
  var no = nos[id];
  tooltip.textContent = '';
  var titulo = document.createElement('div');
  titulo.style.fontWeight = '700';
  titulo.textContent = no.titulo;
  tooltip.appendChild(titulo);
  var dl = document.createElement('dl');
  function linha(rotulo, valor){
    if (valor === undefined || valor === null || valor === '') return;
    var dt = document.createElement('dt'); dt.textContent = rotulo;
    var dd = document.createElement('dd'); dd.textContent = valor;
    dl.appendChild(dt); dl.appendChild(dd);
  }
  linha('tipo', DADOS.rotulos[no.tipo] || no.tipo);
  linha('autor', no.autor);
  linha('data', no.criado_em);
  linha('status', no.status);
  Object.keys(no.campos || {}).sort().forEach(function(chave){
    var valor = no.campos[chave];
    if (valor && typeof valor === 'object') { valor = JSON.stringify(valor); }
    linha(chave, valor);
  });
  tooltip.appendChild(dl);
  tooltip.hidden = false;
  posicionaTooltip(e);
}
var selecionado = null;
function aplicaSelecao(){
  Object.keys(nos).forEach(function(id){
    var destaque = !selecionado || id === selecionado
      || vizinhos[selecionado].has(id);
    elGrupo[id].style.opacity = destaque ? '1' : '0.15';
  });
  arestas.forEach(function(a, i){
    var destaque = !selecionado || a.origem === selecionado
      || a.destino === selecionado;
    elLinha[i].style.opacity = destaque ? '0.8' : '0.15';
  });
}
function alternaSelecao(id){
  if (selecionado === id) { window.location.href = 'trilha.html#' + id; return; }
  selecionado = id;
  aplicaSelecao();
}
Object.keys(nos).forEach(function(id){
  var no = nos[id];
  var g = document.createElementNS(NS, 'g');
  g.setAttribute('class', 'grafo-no' + (no.concluido ? ' grafo-brilho' : ''));
  g.style.color = DADOS.cores[no.tipo] || '#4a5560';
  var circulo = document.createElementNS(NS, 'circle');
  circulo.setAttribute('r', '9');
  circulo.setAttribute('fill', DADOS.cores[no.tipo] || '#4a5560');
  circulo.setAttribute('stroke', '#fbfbf9');
  circulo.setAttribute('stroke-width', '2');
  var texto = document.createElementNS(NS, 'text');
  texto.setAttribute('font-size', '11');
  texto.setAttribute('fill', '#14181c');
  texto.setAttribute('x', '13');
  texto.setAttribute('y', '4');
  texto.textContent = no.titulo;
  g.appendChild(circulo);
  g.appendChild(texto);
  camadaNos.appendChild(g);
  elGrupo[id] = g;
  var arrastando = false, moveu = false, px = 0, py = 0;
  g.addEventListener('pointerdown', function(e){
    arrastando = true; moveu = false; px = e.clientX; py = e.clientY;
    no.fixo = true;
    g.setPointerCapture(e.pointerId);
    quadro = 0;
  });
  g.addEventListener('pointermove', function(e){
    if (!arrastando) { mostraTooltip(id, e); return; }
    if (Math.abs(e.clientX - px) > 3 || Math.abs(e.clientY - py) > 3) { moveu = true; }
    var p = pontoSvg(e.clientX, e.clientY);
    no.x = p.x; no.y = p.y; no.vx = 0; no.vy = 0;
  });
  g.addEventListener('pointerup', function(){
    arrastando = false; no.fixo = false; quadro = 0;
    if (!moveu) { alternaSelecao(id); }
  });
  g.addEventListener('pointerenter', function(e){ mostraTooltip(id, e); });
  g.addEventListener('pointerleave', function(){ escondeTooltip(); });
});
svg.addEventListener('pointerdown', function(e){
  if (e.target.id === 'grafo-fundo') { selecionado = null; aplicaSelecao(); }
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
  Object.keys(nos).forEach(function(id){
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
var ids = Object.keys(nos);
var quadro = 0, MAX_QUADROS = 300, EPS = 0.05;
function passo(){
  var maxDelta = 0;
  for (var i = 0; i < ids.length; i++) {
    for (var j = i + 1; j < ids.length; j++) {
      var a = nos[ids[i]], b = nos[ids[j]];
      var dx = b.x - a.x, dy = b.y - a.y;
      var distSq = dx * dx + dy * dy + 0.01;
      var dist = Math.sqrt(distSq);
      var forca = 2600 / distSq;
      var fx = forca * dx / dist, fy = forca * dy / dist;
      if (!a.fixo) { a.vx -= fx; a.vy -= fy; }
      if (!b.fixo) { b.vx += fx; b.vy += fy; }
    }
  }
  arestas.forEach(function(ar){
    var a = nos[ar.origem], b = nos[ar.destino];
    var dx = b.x - a.x, dy = b.y - a.y;
    var dist = Math.sqrt(dx * dx + dy * dy) || 1;
    var forca = (dist - 130) * 0.02;
    var fx = forca * dx / dist, fy = forca * dy / dist;
    if (!a.fixo) { a.vx += fx; a.vy += fy; }
    if (!b.fixo) { b.vx -= fx; b.vy -= fy; }
  });
  ids.forEach(function(id){
    var no = nos[id];
    if (no.fixo) { return; }
    no.vx += (LARGURA / 2 - no.x) * 0.002;
    no.vy += (ALTURA / 2 - no.y) * 0.002;
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
    elLinha[i].setAttribute('x1', a.x); elLinha[i].setAttribute('y1', a.y);
    elLinha[i].setAttribute('x2', b.x); elLinha[i].setAttribute('y2', b.y);
  });
  quadro++;
  var arrastando = ids.some(function(id){ return nos[id].fixo; });
  if (quadro < MAX_QUADROS || maxDelta > EPS || arrastando) {
    requestAnimationFrame(passo);
  }
}
requestAnimationFrame(passo);
aplicaSelecao();
aplicaFiltros();
})();
</script>"""


def pagina_home(con):
    nota = ('<p class="nota">Arraste os nós para reorganizar; a física se '
           'reacomoda sozinha. Passe o mouse para ver os detalhes e clique '
           'para acender vizinhos — clique de novo para abrir a trilha.</p>')
    palco = (f'<div class="grafo-palco"><svg id="grafo-svg" '
            f'viewBox="0 0 {LARGURA_HOME} {ALTURA_HOME}">'
            f'<rect id="grafo-fundo" width="{LARGURA_HOME}" '
            f'height="{ALTURA_HOME}" fill="transparent"/>'
            f'<g id="grafo-arestas"></g><g id="grafo-nos"></g></svg></div>')
    return (f'{nota}{_legenda()}{_filtros()}{palco}'
           f'<div id="grafo-tooltip" class="grafo-tooltip" hidden></div>'
           f'<script>const DADOS_GRAFO = {json_dados(con)};</script>'
           f'{_SCRIPT_HOME}')
