import subprocess
from collections import Counter

import banco

LIMITE_PENDENCIA_DIAS = 7
LIMITE_SELO_DIAS = 14
MINIMO_RASTREABILIDADE = 90.0


def _pct(parte, total):
    return 100.0 if total == 0 else round(100.0 * parte / total, 1)


def _orfaos(con):
    return [r[0] for r in con.execute(
        "SELECT entidade_id FROM no n WHERE NOT EXISTS "
        "(SELECT 1 FROM aresta a WHERE a.origem = n.entidade_id "
        "OR a.destino = n.entidade_id) ORDER BY entidade_id").fetchall()]


def rastreabilidade(con):
    arq_total = con.execute(
        "SELECT count(*) FROM arquivo").fetchone()[0]
    arq_ok = con.execute(
        "SELECT count(DISTINCT origem) FROM aresta WHERE relacao = 'deriva' "
        "AND origem IN (SELECT id FROM arquivo) "
        "AND destino IN (SELECT id FROM decisao)").fetchone()[0]
    dec_total = con.execute("SELECT count(*) FROM decisao").fetchone()[0]
    dec_ok = con.execute(
        "SELECT count(DISTINCT origem) FROM aresta WHERE relacao = 'atende' "
        "AND origem IN (SELECT id FROM decisao) "
        "AND destino IN (SELECT id FROM meta)").fetchone()[0]
    orfaos = _orfaos(con)
    return {"arquivos_com_decisao": _pct(arq_ok, arq_total),
            "decisoes_com_meta": _pct(dec_ok, dec_total),
            "arquivos_total": arq_total, "decisoes_total": dec_total,
            "orfaos": orfaos}


def _commits_por_semana():
    try:
        saida = subprocess.run(
            ["git", "log", "--date=format:%G-W%V", "--format=%ad"],
            cwd=banco.RAIZ, capture_output=True, text=True,
            check=False).stdout
    except OSError:
        return []
    return sorted(Counter(l for l in saida.split() if l).items())


def cadencia(con):
    def semanal(filtro):
        return [(str(s), n) for s, n in con.execute(
            "SELECT strftime(ts, '%G-W%V') AS semana, count(*) FROM evento "
            f"{filtro} GROUP BY semana ORDER BY semana").fetchall()]
    return {"registros_semana": semanal(""),
            "decisoes_semana": semanal("WHERE tipo = 'decisao'"),
            "commits_semana": _commits_por_semana()}


def higiene(con):
    pendencias = con.execute(
        "SELECT id, titulo, criado_em, date_diff('day', criado_em, now()) AS d "
        "FROM pendencia WHERE status = 'aberta' AND d > ? ORDER BY d DESC",
        [LIMITE_PENDENCIA_DIAS]).fetchall()
    tarefas = con.execute(
        "SELECT id, titulo, resp, prazo FROM tarefa WHERE status = 'aberta' "
        "AND (resp IS NULL OR resp = '' OR prazo IS NULL) ORDER BY id"
    ).fetchall()
    return {"pendencias_velhas": [list(r) for r in pendencias],
            "tarefas_incompletas": [list(r) for r in tarefas]}


def postura(con):
    contagem = dict(con.execute(
        "SELECT aceito, count(*) FROM ia GROUP BY aceito").fetchall())
    integral = contagem.get("integral", 0)
    parcial = contagem.get("parcial", 0)
    descarte = contagem.get("descarte", 0)
    total = integral + parcial + descarte
    return {"integral": integral, "parcial": parcial, "descarte": descarte,
            "total": total, "taxa_integral": _pct(integral, total)}


def selo(m):
    motivos = []
    if m["rastreabilidade"]["orfaos"]:
        motivos.append(f"{len(m['rastreabilidade']['orfaos'])} no(s) orfao(s)")
    if m["rastreabilidade"]["decisoes_com_meta"] < MINIMO_RASTREABILIDADE:
        motivos.append("decisoes sem meta vinculada abaixo de "
                       f"{MINIMO_RASTREABILIDADE:.0f}%")
    velhas = [p for p in m["higiene"]["pendencias_velhas"]
              if p[3] > LIMITE_SELO_DIAS]
    if velhas:
        motivos.append(f"{len(velhas)} pendencia(s) aberta(s) ha mais de "
                       f"{LIMITE_SELO_DIAS} dias")
    if m["postura"]["total"] and m["postura"]["taxa_integral"] == 100.0:
        motivos.append("aceite integral em 100% das interacoes com IA")
    return ("verde" if not motivos else "vermelho", motivos)


def calcula(con):
    m = {"rastreabilidade": rastreabilidade(con), "cadencia": cadencia(con),
         "higiene": higiene(con), "postura": postura(con)}
    m["selo"] = selo(m)
    return m
