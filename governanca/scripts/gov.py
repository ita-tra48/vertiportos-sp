import argparse
import json
import sys

import banco

MIN_CRITICA = 20


def _erro(msg):
    print(f"gov: {msg}", file=sys.stderr)
    return 2


def _pares(lista):
    saida = {}
    for item in lista or []:
        if "=" not in item:
            raise SystemExit(f"gov: parametro sem '=': {item}")
        chave, valor = item.split("=", 1)
        chave = chave.strip()
        if not chave:
            raise SystemExit(f"gov: parametro com chave vazia: {item}")
        if chave in saida:
            raise SystemExit(f"gov: parametro duplicado: {chave}")
        saida[chave] = valor.strip()
    return saida


def cmd_meta(a):
    banco.registra("meta", banco.novo_id("met"),
                   {"titulo": a.titulo, "desc": a.desc, "status": "aberta"})
    return 0


def cmd_tarefa(a):
    banco.registra("tarefa", banco.novo_id("tar"),
                   {"titulo": a.titulo, "resp": a.resp, "prazo": a.prazo,
                    "status": "aberta"})
    return 0


def cmd_pendencia(a):
    banco.registra("pendencia", banco.novo_id("pen"),
                   {"titulo": a.titulo, "status": "aberta"})
    return 0


def cmd_decisao(a):
    banco.registra("decisao", banco.novo_id("dec"),
                   {"titulo": a.titulo, "just": a.just, "alt": a.alt or [],
                    "status": "vigente"})
    return 0


def cmd_fonte(a):
    banco.registra("fonte", banco.novo_id("fon"),
                   {"titulo": a.nome, "origem": a.origem, "formato": a.formato,
                    "cobertura": a.cobertura, "limitacoes": a.limitacoes})
    return 0


def cmd_arquivo(a):
    banco.registra("arquivo", banco.novo_id("arq"),
                   {"titulo": a.caminho, "desc": a.desc})
    return 0


def cmd_referencia(a):
    banco.registra("referencia", banco.novo_id("ref"),
                   {"titulo": a.citacao, "url": a.url, "doi": a.doi})
    return 0


def cmd_experimento(a):
    numeros = {}
    for nome in ("obj", "gap", "tempo"):
        bruto = getattr(a, nome)
        if bruto is None:
            numeros[nome] = None
            continue
        try:
            numeros[nome] = float(bruto)
        except ValueError:
            return _erro(f"valor numerico invalido para --{nome}: {bruto}")
    banco.registra("experimento", banco.novo_id("exp"),
                   {"variante": a.variante, "p": _pares(a.p),
                    "commit": a.commit, "obj": numeros["obj"],
                    "gap": numeros["gap"], "tempo": numeros["tempo"],
                    "hipotese": a.hipotese, "conclusao": a.conclusao})
    return 0


def cmd_ia(a):
    if len(a.critica.strip()) < MIN_CRITICA:
        return _erro("critica humana precisa de pelo menos "
                     f"{MIN_CRITICA} caracteres: quem nao consegue criticar "
                     "a resposta nao a entendeu (enunciado 5.6.2)")
    banco.registra("ia", banco.novo_id("ia"),
                   {"proposito": a.proposito, "modelo": a.modelo,
                    "pedido": a.pedido, "retorno": a.retorno,
                    "aceito": a.aceito, "critica": a.critica})
    return 0


def cmd_liga(a):
    if a.relacao not in banco.RELACOES:
        raise SystemExit(f"gov: relacao invalida: {a.relacao}. "
                         f"validas: {', '.join(sorted(banco.RELACOES))}")
    try:
        origem = banco.resolve(a.origem)
        destino = banco.resolve(a.destino)
    except ValueError as exc:
        return _erro(str(exc))
    banco.registra("aresta", origem,
                   {"relacao": a.relacao, "destino": destino})
    return 0


def _payload_atual(entidade_id):
    con = banco.conecta()
    linha = con.execute(
        "SELECT tipo, payload FROM no WHERE entidade_id = ?",
        [entidade_id]).fetchone()
    if linha is None:
        raise ValueError(f"sem registro para {entidade_id}")
    return linha[0], json.loads(linha[1])


def cmd_fecha(a):
    try:
        entidade_id = banco.resolve(a.id)
        tipo, payload = _payload_atual(entidade_id)
    except ValueError as exc:
        return _erro(str(exc))
    payload["status"] = {"tarefa": "feita", "pendencia": "resolvida",
                         "meta": "concluida"}.get(tipo, "encerrada")
    if a.resolucao:
        payload["resolucao"] = a.resolucao
    banco.registra(tipo, entidade_id, payload)
    return 0


def cmd_patch(a):
    try:
        entidade_id = banco.resolve(a.id)
        tipo, payload = _payload_atual(entidade_id)
    except ValueError as exc:
        return _erro(str(exc))
    payload.update(_pares(a.campos))
    banco.registra(tipo, entidade_id, payload)
    return 0


def cmd_consulta(a):
    sql = a.sql.strip().rstrip(";")
    if not sql.lower().startswith(("select", "with")):
        raise SystemExit("gov: consulta aceita apenas SELECT ou WITH")
    if ";" in sql:
        raise SystemExit("gov: um statement por consulta")
    con = banco.conecta(somente_leitura=True)
    con.execute("SET enable_external_access = false")
    cur = con.execute(sql)
    colunas = [d[0] for d in cur.description]
    print(" | ".join(colunas))
    for linha in cur.fetchall():
        print(" | ".join("" if v is None else str(v) for v in linha))
    return 0


def _orfaos(con):
    return [r[0] for r in con.execute(
        "SELECT entidade_id FROM no n WHERE NOT EXISTS "
        "(SELECT 1 FROM aresta a WHERE a.origem = n.entidade_id "
        "OR a.destino = n.entidade_id) ORDER BY entidade_id").fetchall()]


def cmd_status(a):
    con = banco.conecta()
    print("== estado do banco ==")
    for tipo in banco.PREFIXOS:
        n = con.execute("SELECT count(*) FROM no WHERE tipo = ?",
                        [tipo]).fetchone()[0]
        print(f"{tipo:>12}: {n}")
    arestas = con.execute("SELECT count(*) FROM aresta").fetchone()[0]
    print(f"{'arestas':>12}: {arestas}")
    orfaos = _orfaos(con)
    print(f"\nnos orfaos: {len(orfaos)}")
    for oid in orfaos:
        titulo = con.execute(
            "SELECT coalesce(payload->>'titulo', payload->>'variante', "
            "payload->>'proposito') FROM no WHERE entidade_id = ?",
            [oid]).fetchone()[0]
        print(f"  {oid}  {titulo}")
    abertas = con.execute(
        "SELECT id, titulo, resp, prazo FROM tarefa WHERE status = 'aberta' "
        "ORDER BY prazo NULLS LAST").fetchall()
    print(f"\ntarefas abertas: {len(abertas)}")
    for tid, titulo, resp, prazo in abertas:
        print(f"  {tid}  {titulo}  [{resp}]  {prazo or 'sem prazo'}")
    return 0


def cmd_rebuild(a):
    banco.rebuild()
    print("banco reconstruido a partir de governanca/dump.sql")
    return 0


def constroi_parser():
    p = argparse.ArgumentParser(prog="gov")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("meta")
    s.add_argument("titulo")
    s.add_argument("--desc")
    s.set_defaults(func=cmd_meta)

    s = sub.add_parser("tarefa")
    s.add_argument("titulo")
    s.add_argument("--resp", required=True)
    s.add_argument("--prazo")
    s.set_defaults(func=cmd_tarefa)

    s = sub.add_parser("pendencia")
    s.add_argument("titulo")
    s.set_defaults(func=cmd_pendencia)

    s = sub.add_parser("decisao")
    s.add_argument("titulo")
    s.add_argument("--just", required=True)
    s.add_argument("--alt", action="append")
    s.set_defaults(func=cmd_decisao)

    s = sub.add_parser("fonte")
    s.add_argument("nome")
    s.add_argument("--origem", required=True)
    s.add_argument("--formato")
    s.add_argument("--cobertura")
    s.add_argument("--limitacoes", required=True)
    s.set_defaults(func=cmd_fonte)

    s = sub.add_parser("arquivo")
    s.add_argument("caminho")
    s.add_argument("--desc")
    s.set_defaults(func=cmd_arquivo)

    s = sub.add_parser("referencia")
    s.add_argument("citacao")
    s.add_argument("--url")
    s.add_argument("--doi")
    s.set_defaults(func=cmd_referencia)

    s = sub.add_parser("experimento")
    s.add_argument("--variante", required=True)
    s.add_argument("--p", action="append")
    s.add_argument("--commit")
    s.add_argument("--obj")
    s.add_argument("--gap")
    s.add_argument("--tempo")
    s.add_argument("--hipotese")
    s.add_argument("--conclusao")
    s.set_defaults(func=cmd_experimento)

    s = sub.add_parser("ia")
    s.add_argument("--proposito", required=True)
    s.add_argument("--aceito", required=True,
                   choices=["integral", "parcial", "descarte"])
    s.add_argument("--critica", required=True)
    s.add_argument("--modelo")
    s.add_argument("--pedido")
    s.add_argument("--retorno")
    s.set_defaults(func=cmd_ia)

    s = sub.add_parser("liga")
    s.add_argument("origem")
    s.add_argument("relacao")
    s.add_argument("destino")
    s.set_defaults(func=cmd_liga)

    s = sub.add_parser("fecha")
    s.add_argument("id")
    s.add_argument("--resolucao")
    s.set_defaults(func=cmd_fecha)

    s = sub.add_parser("patch")
    s.add_argument("id")
    s.add_argument("campos", nargs="+")
    s.set_defaults(func=cmd_patch)

    s = sub.add_parser("consulta")
    s.add_argument("sql")
    s.set_defaults(func=cmd_consulta)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("rebuild")
    s.set_defaults(func=cmd_rebuild)

    return p


def main(argv=None):
    a = constroi_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
