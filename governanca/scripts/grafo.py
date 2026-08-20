from html import escape

import banco

FAIXAS = ["meta", "decisao", "experimento", "fonte", "referencia",
          "arquivo", "tarefa", "pendencia", "ia"]
CORES = {"meta": "#1d4ed8", "decisao": "#b45309", "experimento": "#047857",
         "fonte": "#7c3aed", "referencia": "#0e7490", "arquivo": "#475569",
         "tarefa": "#ca8a04", "pendencia": "#be123c", "ia": "#db2777"}
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


def _corta(texto, limite=34):
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def svg(con):
    nos, arestas = coleta(con)
    pos = posiciona(nos)
    colunas = max([1] + [1 + (pos[n["id"]][0] - MARGEM - 160) // LARGURA_COLUNA
                         for n in nos])
    largura = MARGEM * 2 + 160 + colunas * LARGURA_COLUNA
    altura = MARGEM * 2 + len(FAIXAS) * ALTURA_FAIXA
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" id="grafo" '
              f'viewBox="0 0 {largura} {altura}" width="100%" '
              f'height="{altura}" font-family="ui-monospace, monospace">']
    partes.append('<g id="camada">')
    for faixa, tipo in enumerate(FAIXAS):
        y = MARGEM + faixa * ALTURA_FAIXA
        partes.append(
            f'<text x="{MARGEM}" y="{y + 4}" font-size="13" '
            f'fill="{CORES[tipo]}" font-weight="700">{tipo}</text>')
        partes.append(
            f'<line x1="{MARGEM}" y1="{y + 16}" x2="{largura - MARGEM}" '
            f'y2="{y + 16}" stroke="#e2e8f0" stroke-width="1"/>')
    for aresta in arestas:
        origem, destino = pos.get(aresta["origem"]), pos.get(aresta["destino"])
        if not origem or not destino:
            continue
        meio_y = (origem[1] + destino[1]) / 2
        partes.append(
            f'<path d="M {origem[0]} {origem[1]} C {origem[0]} {meio_y} '
            f'{destino[0]} {meio_y} {destino[0]} {destino[1]}" fill="none" '
            f'stroke="#94a3b8" stroke-width="1.2" opacity="0.75"/>')
        partes.append(
            f'<text x="{(origem[0] + destino[0]) / 2}" y="{meio_y - 3}" '
            f'font-size="9" fill="#64748b" text-anchor="middle">'
            f'{escape(aresta["relacao"])}</text>')
    for no in nos:
        x, y = pos[no["id"]]
        cor = CORES.get(no["tipo"], "#334155")
        partes.append(
            f'<a href="trilha.html#{escape(no["id"])}">'
            f'<circle cx="{x}" cy="{y}" r="{RAIO}" fill="{cor}" '
            f'stroke="#ffffff" stroke-width="2"><title>'
            f'{escape(no["id"])} — {escape(no["rotulo"])}</title></circle>'
            f'<text x="{x + RAIO + 6}" y="{y + 4}" font-size="11" '
            f'fill="#0f172a">{escape(_corta(no["rotulo"]))}</text></a>')
    partes.append("</g></svg>")
    return "\n".join(partes)
