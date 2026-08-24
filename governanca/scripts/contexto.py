import json


def vizinhanca(con, entidade_id, raio=1):
    nos = {entidade_id}
    arestas = []
    vistas = set()
    fronteira = {entidade_id}
    for _ in range(raio):
        if not fronteira:
            break
        marcas = ", ".join("?" for _ in fronteira)
        linhas = con.execute(
            f"SELECT origem, relacao, destino FROM aresta "
            f"WHERE origem IN ({marcas}) OR destino IN ({marcas}) "
            f"ORDER BY origem, relacao, destino",
            sorted(fronteira) * 2).fetchall()
        proxima = set()
        for origem, relacao, destino in linhas:
            tripla = (origem, relacao, destino)
            if tripla in vistas:
                continue
            vistas.add(tripla)
            arestas.append(tripla)
            for lado in (origem, destino):
                if lado not in nos:
                    nos.add(lado)
                    proxima.add(lado)
        fronteira = proxima
    return nos, arestas


def registros(con, ids):
    marcas = ", ".join("?" for _ in ids)
    linhas = con.execute(
        f"SELECT entidade_id, tipo, autor, ts, payload FROM no "
        f"WHERE entidade_id IN ({marcas}) ORDER BY entidade_id",
        sorted(ids)).fetchall()
    saida = []
    for eid, tipo, autor, ts, payload in linhas:
        reg = {"id": eid, "tipo": tipo, "autor": autor, "ts": str(ts)}
        reg.update(json.loads(payload))
        saida.append(reg)
    return saida


def markdown(centro, raio, regs, arestas):
    linhas = [f"# contexto de {centro} (raio {raio})", ""]
    for reg in regs:
        linhas.append(f"## {reg['id']} — {reg['tipo']}")
        for chave, valor in reg.items():
            if chave in ("id", "tipo") or valor in (None, "", []):
                continue
            linhas.append(f"- {chave}: {valor}")
        linhas.append("")
    linhas.append("## arestas")
    for origem, relacao, destino in arestas:
        linhas.append(f"- {origem} —{relacao}→ {destino}")
    caminhos = [r["titulo"] for r in regs
                if r["tipo"] == "arquivo" and r.get("titulo")]
    if caminhos:
        linhas += ["", "## arquivos ligados"]
        linhas += [f"- {c}" for c in caminhos]
    return "\n".join(linhas)
