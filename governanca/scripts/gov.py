import argparse
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
        saida[chave.strip()] = valor.strip()
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
    banco.registra("experimento", banco.novo_id("exp"),
                   {"variante": a.variante, "p": _pares(a.p),
                    "commit": a.commit, "obj": a.obj, "gap": a.gap,
                    "tempo": a.tempo, "hipotese": a.hipotese,
                    "conclusao": a.conclusao})
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

    return p


def main(argv=None):
    a = constroi_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
