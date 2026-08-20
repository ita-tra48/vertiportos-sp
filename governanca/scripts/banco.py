import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[2]
DB = RAIZ / "governanca" / "projeto.duckdb"
DUMP = RAIZ / "governanca" / "dump.sql"
SCHEMA = RAIZ / "governanca" / "schemas" / "schema.sql"

TIPOS = ("meta", "tarefa", "pendencia", "decisao", "fonte", "arquivo",
         "referencia", "experimento", "ia", "aresta")

PREFIXOS = {"meta": "met", "tarefa": "tar", "pendencia": "pen",
            "decisao": "dec", "fonte": "fon", "arquivo": "arq",
            "referencia": "ref", "experimento": "exp", "ia": "ia"}

RELACOES = frozenset({"tem", "atende", "usa", "produz", "justifica",
                      "apoia", "deriva", "bloqueia", "informa"})

_ALFABETO = "0123456789abcdefghijklmnopqrstuvwxyz"
_CON = None
_CON_SOMENTE_LEITURA = None


def novo_id(prefixo):
    corpo = "".join(_ALFABETO[b % 36] for b in os.urandom(6))
    return f"{prefixo}-{corpo}"


def autor_atual():
    autor = os.environ.get("GOV_AUTOR", "").strip()
    if autor:
        return autor
    try:
        autor = subprocess.run(["git", "config", "user.name"], cwd=RAIZ,
                               capture_output=True, text=True,
                               check=False).stdout.strip()
    except OSError:
        autor = ""
    if not autor:
        sys.exit("autor indeterminado: rode `git config user.name \"Seu Nome\"` "
                 "ou exporte GOV_AUTOR")
    return autor


def _cria(con):
    con.execute(SCHEMA.read_text())


def rebuild():
    global _CON, _CON_SOMENTE_LEITURA
    if _CON is not None:
        _CON.close()
        _CON = None
    _CON_SOMENTE_LEITURA = None
    if DB.exists():
        DB.unlink()
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    _cria(con)
    if DUMP.exists():
        con.execute(DUMP.read_text())
    con.close()


def _desatualizado():
    if not DB.exists():
        return True
    if DUMP.exists() and DUMP.stat().st_mtime > DB.stat().st_mtime:
        return True
    return False


def conecta(somente_leitura=False):
    global _CON, _CON_SOMENTE_LEITURA
    if _desatualizado():
        rebuild()
    if _CON is None or _CON_SOMENTE_LEITURA != somente_leitura:
        if _CON is not None:
            _CON.close()
        DB.parent.mkdir(parents=True, exist_ok=True)
        _CON = duckdb.connect(str(DB), read_only=somente_leitura)
        if not somente_leitura:
            _cria(_CON)
        _CON_SOMENTE_LEITURA = somente_leitura
    return _CON


def _sql_literal(texto):
    return "'" + texto.replace("'", "''") + "'"


def registra(tipo, entidade_id, payload, autor=None, ts=None):
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconhecido: {tipo}")
    autor = autor or autor_atual()
    ts = ts or datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    evento_id = novo_id("evt")
    corpo = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    valores = [_sql_literal(evento_id), _sql_literal(ts.isoformat(sep=" ")),
               _sql_literal(autor), _sql_literal(tipo),
               _sql_literal(entidade_id), _sql_literal(corpo)]
    stmt = "INSERT INTO evento VALUES (" + ", ".join(valores) + ");"
    con = conecta()
    DUMP.parent.mkdir(parents=True, exist_ok=True)
    with DUMP.open("a", encoding="utf-8") as fh:
        fh.write(stmt + "\n")
    con.execute(stmt)
    os.utime(DB, None)
    return evento_id


def resolve(ref):
    con = conecta()
    achados = [r[0] for r in con.execute(
        "SELECT DISTINCT entidade_id FROM evento WHERE entidade_id LIKE ? "
        "ORDER BY entidade_id", [ref + "%"]).fetchall()]
    if not achados:
        raise ValueError(f"id nao encontrado: {ref}")
    if len(achados) > 1:
        raise ValueError(f"prefixo ambiguo {ref}: {', '.join(achados)}")
    return achados[0]
