import argparse
import re
import subprocess
import sys

import banco

PADRAO_ETAPA = re.compile(r"^\d{2}-[a-z0-9-]+\.R$")


def scripts_fora_do_padrao(raiz):
    app = raiz / "app"
    if not app.is_dir():
        return []
    return sorted(p.name for p in app.glob("*.R")
                  if not PADRAO_ETAPA.match(p.name))


def bruto_alterado(raiz, base):
    r = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                       cwd=raiz, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"valida_estrutura: git diff falhou para base {base}: {r.stderr.strip()}")
    return sorted(c for c in r.stdout.splitlines()
                  if c.startswith("dados/bruto/")
                  and not c.endswith(".gitkeep"))


def figuras_sem_gerador(raiz):
    pasta = raiz / "relatorio" / "figuras"
    if not pasta.is_dir():
        return []
    con = banco.conecta(somente_leitura=True)
    ligadas = {t for (t,) in con.execute(
        "SELECT n.payload->>'titulo' FROM no n "
        "JOIN aresta a ON a.destino = n.entidade_id "
        "WHERE n.tipo = 'arquivo' AND a.relacao = 'produz'").fetchall()}
    soltas = []
    for p in sorted(pasta.rglob("*")):
        if p.is_file() and p.name != ".gitkeep":
            rel = str(p.relative_to(raiz))
            if rel not in ligadas:
                soltas.append(rel)
    return soltas


def main(argv=None):
    ap = argparse.ArgumentParser(prog="valida_estrutura")
    ap.add_argument("--base")
    a = ap.parse_args(argv)
    problemas = [f"script fora do padrao NN-nome.R: app/{n}"
                 for n in scripts_fora_do_padrao(banco.RAIZ)]
    if a.base:
        problemas += [f"alteracao proibida em dados/bruto: {c}"
                      for c in bruto_alterado(banco.RAIZ, a.base)]
    problemas += [f"figura sem script gerador ligado no grafo: {c}"
                  for c in figuras_sem_gerador(banco.RAIZ)]
    for p in problemas:
        print(f"estrutura: {p}", file=sys.stderr)
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
