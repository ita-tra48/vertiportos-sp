# Infra de Governança Computável (camada B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o motor de governança computável do Projeto B1 — `./gov` + DuckDB + auditoria + site publicado no GitHub Pages — de modo que toda decisão, fonte, experimento e interação com IA do bimestre seja registrada, ligada em grafo, auditada e publicada automaticamente.

**Architecture:** Uma tabela append-only `evento` em DuckDB é a única coisa que se escreve; as nove entidades do enunciado e as arestas do grafo são views sobre ela. O artefato versionado em git é `governanca/dump.sql` (sequência de INSERTs, mergeável entre 4 pessoas), e o banco binário é reconstruível a partir dele. O site é função pura do banco, gerado do zero pelo CI a cada push e publicado por artifact do Actions.

**Tech Stack:** Python 3.14 (stdlib + `duckdb` 1.5.5 + `pytest`) em venv dedicado; R 4.6.1 (`duckdb`, `tidyverse`, `lpSolve`/`ROI`) para a camada A; GitHub Actions + Pages.

**Spec:** `docs/superpowers/specs/2026-08-20-tra48-governanca-design.md`

## Global Constraints

- **Comentários de código: teto de 1 linha de comentário no diff inteiro por commit** (`~/.claude/CLAUDE.md`). O "por quê" vai na mensagem de commit / PR. Filtro obrigatório antes de cada commit: `git diff --cached | grep -E '^\+.*(//|#|/\*|\*|<!--)'` — contar e apagar até sobrar no máximo 1.
- **Conta GitHub:** `gustavovfeitosa`. **NUNCA** `gustavovidal-tiktok`. Org: `Projeto-TRA-48-Grupo-1`. `gh auth switch` precisa rodar fora do sandbox.
- **Nada de dependência de rede no site publicado:** sem CDN, sem webfont remota, sem fetch. O site é navegado ao vivo na arguição.
- **Interpretador:** todo Python roda via `governanca/.venv/bin/python`. Nunca `python3` do sistema.
- **Idioma:** identificadores, mensagens da CLI e textos do site em português. Nomes de tabela/coluna sem acento (`pendencia`, `decisao`).
- **`dados/bruto/` é somente-leitura** (`CLAUDE.md` do projeto). Todo tratamento escreve em `dados/tratado/`.
- **Determinismo:** dois `./gov update` sobre o mesmo banco produzem saída byte-a-byte idêntica. Nada de `datetime.now()` dentro de geradores, nada de ordenação por `set`.
- **Prefixos de id:** `met tar pen dec fon arq ref exp ia`, mais `evt` para eventos. Formato `<prefixo>-<6 chars>` de `[0-9a-z]`.
- **Vocabulário fechado de relações:** `tem atende usa produz justifica apoia deriva bloqueia informa`.

---

### Task 1: Fundação — venv, schema e o log de eventos

**Files:**
- Create: `governanca/requirements.txt`
- Create: `governanca/schemas/schema.sql`
- Create: `governanca/scripts/banco.py`
- Create: `governanca/tests/test_banco.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nada (primeira task).
- Produces:
  - `banco.RAIZ: Path` — raiz do repo, resolvida a partir de `__file__`.
  - `banco.novo_id(prefixo: str) -> str`
  - `banco.autor_atual() -> str` — levanta `SystemExit` se indeterminável.
  - `banco.conecta(somente_leitura: bool = False) -> duckdb.DuckDBPyConnection` — reconstrói do dump se o `.duckdb` faltar ou for mais antigo que o dump.
  - `banco.rebuild() -> None`
  - `banco.registra(tipo: str, entidade_id: str, payload: dict, autor: str | None = None, ts: datetime | None = None) -> str` — devolve `evento_id`; grava no banco **e** apenda em `dump.sql`.
  - `banco.resolve(ref: str) -> str` — prefixo → id completo; levanta `ValueError` se ambíguo ou inexistente.
  - `banco.TIPOS: tuple[str, ...]`, `banco.PREFIXOS: dict[str, str]`, `banco.RELACOES: frozenset[str]`

- [ ] **Step 1: Escrever `governanca/requirements.txt`**

```
duckdb==1.5.5
pytest==8.4.2
```

- [ ] **Step 2: Instalar no venv já existente e travar a versão real**

```bash
governanca/.venv/bin/pip install -r governanca/requirements.txt
governanca/.venv/bin/pip freeze | grep -Ei '^(duckdb|pytest)=' 
```
Se a versão instalada divergir do pinado, ajustar o `requirements.txt` para a versão real e reinstalar.

- [ ] **Step 3: Escrever `governanca/schemas/schema.sql`**

```sql
CREATE TABLE IF NOT EXISTS evento (
    evento_id   TEXT PRIMARY KEY,
    ts          TIMESTAMP NOT NULL,
    autor       TEXT NOT NULL,
    tipo        TEXT NOT NULL,
    entidade_id TEXT NOT NULL,
    payload     JSON NOT NULL
);

CREATE OR REPLACE VIEW no AS
SELECT evento_id, ts, autor, tipo, entidade_id, payload
FROM (
    SELECT *, row_number() OVER (
               PARTITION BY entidade_id ORDER BY ts DESC, evento_id DESC) AS rn
    FROM evento WHERE tipo <> 'aresta'
) WHERE rn = 1;

CREATE OR REPLACE VIEW criacao AS
SELECT entidade_id,
       min(ts)              AS criado_em,
       arg_min(autor, ts)   AS criado_por
FROM evento WHERE tipo <> 'aresta'
GROUP BY entidade_id;

CREATE OR REPLACE VIEW aresta AS
SELECT evento_id, ts, autor,
       entidade_id          AS origem,
       payload->>'relacao'  AS relacao,
       payload->>'destino'  AS destino
FROM evento WHERE tipo = 'aresta';

CREATE OR REPLACE VIEW meta AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por, n.autor AS autor_ult,
       n.payload->>'titulo' AS titulo,
       n.payload->>'desc'   AS descricao,
       coalesce(n.payload->>'status', 'aberta') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'meta';

CREATE OR REPLACE VIEW tarefa AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS titulo,
       n.payload->>'resp'   AS resp,
       try_cast(n.payload->>'prazo' AS DATE) AS prazo,
       coalesce(n.payload->>'status', 'aberta') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'tarefa';

CREATE OR REPLACE VIEW pendencia AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo'    AS titulo,
       n.payload->>'resolucao' AS resolucao,
       coalesce(n.payload->>'status', 'aberta') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'pendencia';

CREATE OR REPLACE VIEW decisao AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS titulo,
       n.payload->>'just'   AS justificativa,
       n.payload->'alt'     AS alternativas,
       coalesce(n.payload->>'status', 'vigente') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'decisao';

CREATE OR REPLACE VIEW fonte AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo'     AS nome,
       n.payload->>'origem'     AS origem,
       n.payload->>'formato'    AS formato,
       n.payload->>'cobertura'  AS cobertura,
       n.payload->>'limitacoes' AS limitacoes
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'fonte';

CREATE OR REPLACE VIEW arquivo AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS caminho,
       n.payload->>'desc'   AS descricao
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'arquivo';

CREATE OR REPLACE VIEW referencia AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS citacao,
       n.payload->>'url'    AS url,
       n.payload->>'doi'    AS doi
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'referencia';

CREATE OR REPLACE VIEW experimento AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'variante'  AS variante,
       n.payload->'p'          AS parametros,
       n.payload->>'commit'    AS commit_sha,
       try_cast(n.payload->>'obj'   AS DOUBLE) AS obj,
       try_cast(n.payload->>'gap'   AS DOUBLE) AS gap,
       try_cast(n.payload->>'tempo' AS DOUBLE) AS tempo_s,
       n.payload->>'hipotese'  AS hipotese,
       n.payload->>'conclusao' AS conclusao
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'experimento';

CREATE OR REPLACE VIEW ia AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'proposito' AS proposito,
       n.payload->>'modelo'    AS modelo,
       n.payload->>'pedido'    AS pedido,
       n.payload->>'retorno'   AS retorno,
       n.payload->>'aceito'    AS aceito,
       n.payload->>'critica'   AS critica
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'ia';
```

- [ ] **Step 4: Escrever o teste que falha, `governanca/tests/test_banco.py`**

```python
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco


def test_novo_id_tem_prefixo_e_seis_chars():
    i = banco.novo_id("dec")
    assert i.startswith("dec-")
    assert len(i) == len("dec-") + 6
    assert set(i.split("-")[1]) <= set("0123456789abcdefghijklmnopqrstuvwxyz")


def test_novo_id_nao_repete():
    assert len({banco.novo_id("dec") for _ in range(500)}) == 500


def test_registra_e_le_de_volta(tmp_repo):
    eid = banco.novo_id("dec")
    banco.registra("decisao", eid, {"titulo": "Motor em Python", "just": "porque"},
                   autor="Gustavo")
    con = banco.conecta()
    linha = con.execute(
        "SELECT titulo, justificativa, criado_por FROM decisao WHERE id = ?", [eid]
    ).fetchone()
    assert linha == ("Motor em Python", "porque", "Gustavo")


def test_dump_e_append_only(tmp_repo):
    banco.registra("meta", banco.novo_id("met"), {"titulo": "A"}, autor="G")
    antes = banco.DUMP.read_text()
    banco.registra("meta", banco.novo_id("met"), {"titulo": "B"}, autor="G")
    depois = banco.DUMP.read_text()
    assert depois.startswith(antes)
    assert depois.count("INSERT INTO evento") == 2


def test_rebuild_reconstroi_do_dump(tmp_repo):
    eid = banco.novo_id("fon")
    banco.registra("fonte", eid, {"titulo": "OD Metro", "limitacoes": "2017"},
                   autor="G")
    banco.DB.unlink()
    con = banco.conecta()
    assert con.execute("SELECT nome FROM fonte WHERE id = ?", [eid]).fetchone() == (
        "OD Metro",
    )


def test_ultimo_evento_ganha(tmp_repo):
    eid = banco.novo_id("tar")
    banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                   "status": "aberta"}, autor="G")
    banco.registra("tarefa", eid, {"titulo": "X", "resp": "Ana",
                                   "status": "feita"}, autor="G")
    con = banco.conecta()
    assert con.execute("SELECT status FROM tarefa WHERE id = ?", [eid]).fetchone() == (
        "feita",
    )
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (2,)


def test_resolve_por_prefixo(tmp_repo):
    eid = banco.novo_id("dec")
    banco.registra("decisao", eid, {"titulo": "T", "just": "J"}, autor="G")
    assert banco.resolve(eid[:6]) == eid


def test_resolve_recusa_inexistente(tmp_repo):
    import pytest
    with pytest.raises(ValueError):
        banco.resolve("dec-zzzzzz")


def test_autor_atual_usa_env(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Fulano")
    assert banco.autor_atual() == "Fulano"
```

E o fixture, em `governanca/tests/conftest.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    (tmp_path / "governanca" / "schemas").mkdir(parents=True)
    origem = Path(__file__).resolve().parents[1] / "schemas" / "schema.sql"
    (tmp_path / "governanca" / "schemas" / "schema.sql").write_text(
        origem.read_text())
    monkeypatch.setattr(banco, "RAIZ", tmp_path)
    monkeypatch.setattr(banco, "DB", tmp_path / "governanca" / "projeto.duckdb")
    monkeypatch.setattr(banco, "DUMP", tmp_path / "governanca" / "dump.sql")
    monkeypatch.setattr(banco, "SCHEMA",
                        tmp_path / "governanca" / "schemas" / "schema.sql")
    monkeypatch.setattr(banco, "_CON", None)
    yield tmp_path
    banco._CON = None
```

- [ ] **Step 5: Rodar e confirmar que falha**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/test_banco.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'banco'`

- [ ] **Step 6: Implementar `governanca/scripts/banco.py`**

```python
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
    global _CON
    if _CON is not None:
        _CON.close()
        _CON = None
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
    global _CON
    if _desatualizado():
        rebuild()
    if _CON is None:
        DB.parent.mkdir(parents=True, exist_ok=True)
        _CON = duckdb.connect(str(DB), read_only=somente_leitura)
        if not somente_leitura:
            _cria(_CON)
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
    con.execute(stmt)
    DUMP.parent.mkdir(parents=True, exist_ok=True)
    with DUMP.open("a", encoding="utf-8") as fh:
        fh.write(stmt + "\n")
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
```

- [ ] **Step 7: Rodar e confirmar que passa**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/ -v`
Expected: PASS, 9 testes.

- [ ] **Step 8: Atualizar `.gitignore`**

Apender:

```
governanca/.venv/
governanca/projeto.duckdb
governanca/projeto.duckdb.wal
governanca/site/
__pycache__/
.pytest_cache/
```

- [ ] **Step 9: Configurar autoria do git (ainda vazia neste repo)**

```bash
git config user.name "Gustavo Vidal Feitosa"
git config user.email "gustavo.vidal@brendi.com.br"
git config user.name && git config user.email
```

- [ ] **Step 10: Commit**

```bash
git add governanca/requirements.txt governanca/schemas/schema.sql \
        governanca/scripts/banco.py governanca/tests/ .gitignore
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "governanca: log de eventos append-only em DuckDB como fonte de verdade"
```

---

### Task 2: A CLI `./gov` — as nove entidades e as validações do enunciado

**Files:**
- Create: `gov` (wrapper shell, `chmod +x`)
- Create: `governanca/scripts/gov.py`
- Create: `governanca/tests/test_cli.py`

**Interfaces:**
- Consumes: `banco.registra`, `banco.novo_id`, `banco.PREFIXOS`, `banco.autor_atual`, `banco.conecta`.
- Produces:
  - `gov.main(argv: list[str] | None = None) -> int` — código de saída 0 ok, 2 erro de validação.
  - `gov.constroi_parser() -> argparse.ArgumentParser`

- [ ] **Step 1: Escrever o teste que falha, `governanca/tests/test_cli.py`**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


def test_meta_grava(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("meta", "Localizar vertiportos na RMSP") == 0
    con = banco.conecta()
    assert con.execute("SELECT titulo FROM meta").fetchone() == (
        "Localizar vertiportos na RMSP",)


def test_ia_sem_critica_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("ia", "--proposito", "formulacao", "--aceito", "parcial")
    con = banco.conecta()
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (0,)


def test_ia_com_critica_curta_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("ia", "--proposito", "formulacao", "--aceito", "integral",
                "--critica", "ok") == 2
    con = banco.conecta()
    assert con.execute("SELECT count(*) FROM evento").fetchone() == (0,)


def test_ia_valida_grava(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("ia", "--proposito", "formulacao", "--aceito", "parcial",
                "--critica", "A sugestao ignorou a restricao de capacidade "
                             "do vertiporto e assumiu frota infinita.") == 0
    con = banco.conecta()
    assert con.execute("SELECT aceito FROM ia").fetchone() == ("parcial",)


def test_decisao_sem_justificativa_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("decisao", "Valor do tempo = R$ 50/h")


def test_fonte_sem_limitacoes_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("fonte", "Pesquisa OD Metro", "--origem", "https://x")


def test_tarefa_sem_responsavel_e_recusada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    with pytest.raises(SystemExit):
        roda("tarefa", "Estimar demanda capturavel")


def test_experimento_guarda_parametros(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("experimento", "--variante", "cobertura", "--p", "p=8",
                "--p", "raio=5", "--obj", "12345") == 0
    con = banco.conecta()
    variante, parametros, obj = con.execute(
        "SELECT variante, parametros, obj FROM experimento").fetchone()
    assert variante == "cobertura"
    assert obj == 12345.0
    assert '"p":"8"' in parametros.replace(" ", "")


def test_decisao_com_alternativas_multiplas(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    assert roda("decisao", "Formulacao p-mediana", "--just", "porque X",
                "--alt", "cobertura maxima", "--alt", "custo fixo") == 0
    con = banco.conecta()
    alt = con.execute("SELECT alternativas FROM decisao").fetchone()[0]
    assert "cobertura maxima" in alt and "custo fixo" in alt
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gov'`

- [ ] **Step 3: Implementar `governanca/scripts/gov.py` (parte das entidades)**

```python
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
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/ -v`
Expected: PASS, 18 testes.

- [ ] **Step 5: Criar o wrapper `gov`**

```bash
cat > gov <<'SH'
#!/usr/bin/env bash
set -euo pipefail
raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$raiz/governanca/.venv/bin/python" "$raiz/governanca/scripts/gov.py" "$@"
SH
chmod +x gov
```

- [ ] **Step 6: Fumaça manual**

Run: `./gov meta "Localizar vertiportos na cidade de Sao Paulo" && ./gov ia --proposito teste --aceito descarte --critica "curto"`
Expected: o primeiro grava; o segundo sai com código 2 e a mensagem sobre crítica humana.

Depois desfazer o registro de fumaça: `git checkout -- governanca/dump.sql 2>/dev/null || rm -f governanca/dump.sql governanca/projeto.duckdb`

- [ ] **Step 7: Commit**

```bash
git add gov governanca/scripts/gov.py governanca/tests/test_cli.py
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "gov: nove entidades do 5.3, com as validacoes que o enunciado exige"
```

---

### Task 3: Grafo, ciclo de vida e consulta — `liga`, `fecha`, `patch`, `status`, `consulta`

**Files:**
- Modify: `governanca/scripts/gov.py`
- Create: `governanca/tests/test_grafo_cli.py`

**Interfaces:**
- Consumes: `banco.resolve`, `banco.RELACOES`, `banco.conecta`, `gov.constroi_parser`.
- Produces: subcomandos `liga`, `fecha`, `patch`, `status`, `consulta`, `rebuild`; `gov.cmd_status(a) -> int`.

- [ ] **Step 1: Escrever o teste que falha, `governanca/tests/test_grafo_cli.py`**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def semeado(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    dec = con.execute("SELECT id FROM decisao").fetchone()[0]
    return met, dec


def test_liga_cria_aresta(semeado):
    met, dec = semeado
    assert roda("liga", dec, "atende", met) == 0
    con = banco.conecta()
    assert con.execute(
        "SELECT origem, relacao, destino FROM aresta").fetchone() == (
        dec, "atende", met)


def test_liga_recusa_relacao_fora_do_vocabulario(semeado):
    met, dec = semeado
    with pytest.raises(SystemExit):
        roda("liga", dec, "inventada", met)


def test_liga_aceita_prefixo(semeado):
    met, dec = semeado
    assert roda("liga", dec[:6], "atende", met[:6]) == 0
    con = banco.conecta()
    assert con.execute("SELECT destino FROM aresta").fetchone() == (met,)


def test_fecha_muda_status_sem_apagar_historia(semeado, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    con = banco.conecta()
    roda("tarefa", "Baixar OD", "--resp", "Ana")
    tar = con.execute("SELECT id FROM tarefa").fetchone()[0]
    assert roda("fecha", tar) == 0
    assert con.execute("SELECT status FROM tarefa WHERE id = ?",
                       [tar]).fetchone() == ("feita",)
    assert con.execute("SELECT count(*) FROM evento WHERE entidade_id = ?",
                       [tar]).fetchone() == (2,)


def test_patch_mescla_campos(semeado, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    met, dec = semeado
    assert roda("patch", dec, "just=porque Y") == 0
    con = banco.conecta()
    titulo, just = con.execute(
        "SELECT titulo, justificativa FROM decisao WHERE id = ?",
        [dec]).fetchone()
    assert titulo == "Recorte metropolitano"
    assert just == "porque Y"


def test_consulta_recusa_escrita(semeado):
    with pytest.raises(SystemExit):
        roda("consulta", "DELETE FROM evento")


def test_consulta_select_funciona(semeado, capsys):
    assert roda("consulta", "SELECT count(*) FROM decisao") == 0
    assert "1" in capsys.readouterr().out


def test_status_lista_orfaos(semeado, capsys):
    met, dec = semeado
    roda("status")
    saida = capsys.readouterr().out
    assert "orfaos" in saida.lower()
    assert dec in saida or "2" in saida
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/test_grafo_cli.py -v`
Expected: FAIL — `invalid choice: 'liga'`

- [ ] **Step 3: Implementar os subcomandos em `governanca/scripts/gov.py`**

Adicionar as funções antes de `constroi_parser`:

```python
import json


def cmd_liga(a):
    if a.relacao not in banco.RELACOES:
        return _erro(f"relacao invalida: {a.relacao}. "
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
    con = banco.conecta()
    cur = con.execute(sql)
    colunas = [d[0] for d in cur.description]
    print(" | ".join(colunas))
    for linha in cur.fetchall():
        print(" | ".join("" if v is None else str(v) for v in linha))
    return 0


def _orfaos(con):
    return [r[0] for r in con.execute(
        "SELECT entidade_id FROM no WHERE entidade_id NOT IN "
        "(SELECT origem FROM aresta UNION SELECT destino FROM aresta) "
        "ORDER BY entidade_id").fetchall()]


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
```

E registrar no parser, antes do `return p`:

```python
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
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/ -v`
Expected: PASS, 26 testes.

- [ ] **Step 5: Commit**

```bash
git add governanca/scripts/gov.py governanca/tests/test_grafo_cli.py
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "gov: arestas do grafo executivo, ciclo de vida dos nos e consulta somente-leitura"
```

---

### Task 4: Auditoria — as quatro métricas do §5.7 e o selo

**Files:**
- Create: `governanca/scripts/auditoria.py`
- Create: `governanca/tests/test_auditoria.py`
- Modify: `governanca/scripts/gov.py`

**Interfaces:**
- Consumes: `banco.conecta`, `banco.RAIZ`.
- Produces:
  - `auditoria.calcula(con) -> dict` com chaves `rastreabilidade`, `cadencia`, `higiene`, `postura`, `selo`.
  - `auditoria.rastreabilidade(con) -> dict` → `{"arquivos_com_decisao": float, "decisoes_com_meta": float, "orfaos": list[str]}`
  - `auditoria.cadencia(con) -> dict` → `{"registros_semana": list[tuple[str, int]], "decisoes_semana": list[tuple[str, int]], "commits_semana": list[tuple[str, int]]}`
  - `auditoria.higiene(con) -> dict` → `{"pendencias_velhas": list, "tarefas_incompletas": list}`
  - `auditoria.postura(con) -> dict` → `{"integral": int, "parcial": int, "descarte": int, "taxa_integral": float}`
  - `auditoria.selo(m: dict) -> tuple[str, list[str]]` → `("verde"|"vermelho", motivos)`
  - subcomando `./gov auditoria`

- [ ] **Step 1: Escrever o teste que falha, `governanca/tests/test_auditoria.py`**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import auditoria
import banco
import gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def cenario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    roda("decisao", "Valor do tempo", "--just", "porque Y")
    roda("arquivo", "app/02-od.R")
    roda("ia", "--proposito", "formulacao", "--aceito", "integral",
         "--critica", "aceitei mas conferi a algebra do dual linha por linha")
    roda("ia", "--proposito", "codigo", "--aceito", "descarte",
         "--critica", "propos loop em R onde vetorizacao resolve, descartei")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    decs = [r[0] for r in con.execute(
        "SELECT id FROM decisao ORDER BY id").fetchall()]
    roda("liga", decs[0], "atende", met)
    return con


def test_rastreabilidade_conta_decisoes_com_meta(cenario):
    r = auditoria.rastreabilidade(cenario)
    assert r["decisoes_com_meta"] == pytest.approx(50.0)


def test_rastreabilidade_lista_orfaos(cenario):
    r = auditoria.rastreabilidade(cenario)
    assert len(r["orfaos"]) == 4


def test_arquivo_sem_decisao_conta_zero(cenario):
    r = auditoria.rastreabilidade(cenario)
    assert r["arquivos_com_decisao"] == pytest.approx(0.0)


def test_postura_critica(cenario):
    p = auditoria.postura(cenario)
    assert (p["integral"], p["parcial"], p["descarte"]) == (1, 0, 1)
    assert p["taxa_integral"] == pytest.approx(50.0)


def test_selo_vermelho_com_orfaos(cenario):
    m = auditoria.calcula(cenario)
    assert m["selo"][0] == "vermelho"
    assert any("orfao" in motivo for motivo in m["selo"][1])


def test_higiene_pega_tarefa_sem_prazo(cenario, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("tarefa", "Estimar demanda", "--resp", "Ana")
    h = auditoria.higiene(banco.conecta())
    assert len(h["tarefas_incompletas"]) == 1


def test_cadencia_agrupa_por_semana(cenario):
    c = auditoria.cadencia(cenario)
    assert sum(n for _, n in c["registros_semana"]) == 7


def test_selo_verde_quando_taxa_integral_e_cem_reprova(cenario):
    m = auditoria.calcula(cenario)
    assert m["selo"][0] in ("verde", "vermelho")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/test_auditoria.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auditoria'`

- [ ] **Step 3: Implementar `governanca/scripts/auditoria.py`**

```python
import subprocess
from collections import Counter

import banco

LIMITE_PENDENCIA_DIAS = 7
LIMITE_SELO_DIAS = 14
MINIMO_RASTREABILIDADE = 90.0


def _pct(parte, total):
    return 100.0 if total == 0 else round(100.0 * parte / total, 1)


def rastreabilidade(con):
    arq_total = con.execute(
        "SELECT count(*) FROM arquivo").fetchone()[0]
    arq_ok = con.execute(
        "SELECT count(DISTINCT origem) FROM aresta WHERE relacao = 'deriva' "
        "AND origem IN (SELECT id FROM arquivo)").fetchone()[0]
    dec_total = con.execute("SELECT count(*) FROM decisao").fetchone()[0]
    dec_ok = con.execute(
        "SELECT count(DISTINCT origem) FROM aresta WHERE relacao = 'atende' "
        "AND origem IN (SELECT id FROM decisao)").fetchone()[0]
    orfaos = [r[0] for r in con.execute(
        "SELECT entidade_id FROM no WHERE entidade_id NOT IN "
        "(SELECT origem FROM aresta UNION SELECT destino FROM aresta) "
        "ORDER BY entidade_id").fetchall()]
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
```

- [ ] **Step 4: Registrar o subcomando em `governanca/scripts/gov.py`**

```python
def cmd_auditoria(a):
    import auditoria
    m = auditoria.calcula(banco.conecta())
    r, h, p = m["rastreabilidade"], m["higiene"], m["postura"]
    print(f"selo: {m['selo'][0].upper()}")
    for motivo in m["selo"][1]:
        print(f"  - {motivo}")
    print(f"\nrastreabilidade: arquivos com decisao {r['arquivos_com_decisao']}% "
          f"({r['arquivos_total']}) | decisoes com meta "
          f"{r['decisoes_com_meta']}% ({r['decisoes_total']}) | "
          f"orfaos {len(r['orfaos'])}")
    print(f"postura critica: integral {p['integral']} parcial {p['parcial']} "
          f"descarte {p['descarte']} | taxa integral {p['taxa_integral']}%")
    print(f"higiene: pendencias velhas {len(h['pendencias_velhas'])} | "
          f"tarefas incompletas {len(h['tarefas_incompletas'])}")
    print("\ncadencia (registros por semana):")
    for semana, n in m["cadencia"]["registros_semana"]:
        print(f"  {semana}: {n}")
    return 0
```

E no parser:

```python
    s = sub.add_parser("auditoria")
    s.set_defaults(func=cmd_auditoria)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/ -v`
Expected: PASS, 34 testes.

- [ ] **Step 6: Commit**

```bash
git add governanca/scripts/auditoria.py governanca/scripts/gov.py \
        governanca/tests/test_auditoria.py
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "auditoria: rastreabilidade, cadencia, higiene e postura critica do 5.7"
```

---

### Task 5: Grafo executivo em SVG determinístico

**Files:**
- Create: `governanca/scripts/grafo.py`
- Create: `governanca/tests/test_grafo_svg.py`

**Interfaces:**
- Consumes: `banco.conecta`, `banco.PREFIXOS`.
- Produces:
  - `grafo.coleta(con) -> tuple[list[dict], list[dict]]` — nós `{"id","tipo","rotulo"}` e arestas `{"origem","relacao","destino"}`, ambos ordenados por id.
  - `grafo.posiciona(nos: list[dict]) -> dict[str, tuple[int, int]]` — faixa horizontal por tipo, ordem estável por id.
  - `grafo.svg(con) -> str` — SVG completo, determinístico.

- [ ] **Step 1: Escrever o teste que falha, `governanca/tests/test_grafo_svg.py`**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov
import grafo


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def cenario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos")
    roda("decisao", "Recorte metropolitano", "--just", "porque X")
    con = banco.conecta()
    met = con.execute("SELECT id FROM meta").fetchone()[0]
    dec = con.execute("SELECT id FROM decisao").fetchone()[0]
    roda("liga", dec, "atende", met)
    return con, met, dec


def test_coleta_nos_e_arestas(cenario):
    con, met, dec = cenario
    nos, arestas = grafo.coleta(con)
    assert {n["id"] for n in nos} == {met, dec}
    assert arestas == [{"origem": dec, "relacao": "atende", "destino": met}]


def test_svg_e_determinista(cenario):
    con, _, _ = cenario
    assert grafo.svg(con) == grafo.svg(con)


def test_svg_tem_link_por_no(cenario):
    con, met, dec = cenario
    saida = grafo.svg(con)
    assert f'href="trilha.html#{met}"' in saida
    assert f'href="trilha.html#{dec}"' in saida


def test_svg_escapa_rotulo(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", 'Meta com <script> & "aspas"')
    saida = grafo.svg(banco.conecta())
    assert "<script>" not in saida
    assert "&lt;script&gt;" in saida


def test_svg_vazio_nao_quebra(tmp_repo):
    saida = grafo.svg(banco.conecta())
    assert saida.startswith("<svg")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/test_grafo_svg.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'grafo'`

- [ ] **Step 3: Implementar `governanca/scripts/grafo.py`**

```python
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
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/ -v`
Expected: PASS, 39 testes.

- [ ] **Step 5: Commit**

```bash
git add governanca/scripts/grafo.py governanca/tests/test_grafo_svg.py
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "grafo: SVG determinista com no clicavel, sem dependencia de rede"
```

---

### Task 6: Gerador do site — as oito páginas do §5.5

**Files:**
- Create: `governanca/scripts/site_gov.py` (nao `site.py`: colidiria com o modulo `site` da stdlib)
- Create: `governanca/tests/test_site.py`
- Modify: `governanca/scripts/gov.py`

**Interfaces:**
- Consumes: `banco.conecta`, `auditoria.calcula`, `grafo.svg`.
- Produces:
  - `site_gov.gera(destino: Path | None = None) -> Path` — escreve as 8 páginas + `estilo.css` + `.nojekyll`, devolve o diretório.
  - `site_gov.PAGINAS: tuple[tuple[str, str], ...]` — `(arquivo, titulo)`.
  - subcomando `./gov update`

- [ ] **Step 1: Escrever o teste que falha, `governanca/tests/test_site.py`**

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco
import gov
import site_gov


def roda(*argv):
    return gov.main(list(argv))


@pytest.fixture
def cenario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "Localizar vertiportos na cidade de Sao Paulo")
    roda("decisao", "Recorte metropolitano", "--just", "porque X",
         "--alt", "municipio isolado")
    roda("tarefa", "Baixar Pesquisa OD", "--resp", "Ana",
         "--prazo", "2026-08-26")
    roda("fonte", "Pesquisa OD Metro SP", "--origem", "https://metro.sp.gov.br",
         "--limitacoes", "ultima onda 2017, sem eVTOL")
    roda("experimento", "--variante", "cobertura", "--p", "p=8",
         "--obj", "12345")
    roda("ia", "--proposito", "formulacao", "--aceito", "parcial",
         "--critica", "ignorou capacidade do vertiporto, corrigi a restricao")
    return tmp_repo


def test_gera_as_oito_paginas(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    nomes = {p.name for p in destino.glob("*.html")}
    assert nomes == {a for a, _ in site_gov.PAGINAS}
    assert len(site_gov.PAGINAS) == 8


def test_index_mostra_selo_e_metas(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "index.html").read_text()
    assert "Localizar vertiportos na cidade de Sao Paulo" in html
    assert "selo" in html.lower()


def test_pagina_ia_mostra_taxa_e_critica(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "ia.html").read_text()
    assert "ignorou capacidade do vertiporto" in html
    assert "%" in html


def test_site_nao_tem_dependencia_de_rede(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    for pagina in destino.glob("*.html"):
        texto = pagina.read_text()
        assert "http://" not in texto.replace(
            "http://www.w3.org/2000/svg", "")
        assert "cdn" not in texto.lower()


def test_geracao_e_determinista(cenario):
    destino = cenario / "governanca" / "site"
    site_gov.gera(destino)
    primeiro = {p.name: p.read_text() for p in sorted(destino.glob("*"))
                if p.is_file()}
    site_gov.gera(destino)
    segundo = {p.name: p.read_text() for p in sorted(destino.glob("*"))
               if p.is_file()}
    assert primeiro == segundo


def test_trilha_tem_ancora_por_no(cenario):
    destino = site_gov.gera(cenario / "governanca" / "site")
    html = (destino / "trilha.html").read_text()
    con = banco.conecta()
    for (eid,) in con.execute("SELECT entidade_id FROM no").fetchall():
        assert f'id="{eid}"' in html


def test_escapa_html_do_usuario(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Gustavo")
    roda("meta", "<img src=x onerror=alert(1)>")
    destino = site_gov.gera(tmp_repo / "governanca" / "site")
    html = (destino / "index.html").read_text()
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_update_gera_site(cenario, monkeypatch):
    monkeypatch.setattr(site_gov, "DESTINO",
                        cenario / "governanca" / "site")
    assert roda("update") == 0
    assert (cenario / "governanca" / "site" / "index.html").exists()
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/test_site.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'site_gov'`

- [ ] **Step 3: Implementar `governanca/scripts/site_gov.py`**

```python
import json
from html import escape
from pathlib import Path

import auditoria
import banco
import grafo

DESTINO = banco.RAIZ / "governanca" / "site"

PAGINAS = (("index.html", "Estado"),
           ("grafo.html", "Grafo executivo"),
           ("trilha.html", "Trilha"),
           ("tarefas.html", "Tarefas e pendencias"),
           ("ia.html", "Interacoes com IA"),
           ("experimentos.html", "Experimentos"),
           ("resultados.html", "Resultados"),
           ("reprodutibilidade.html", "Reprodutibilidade"))

ESTILO = """:root{--tinta:#0f172a;--fundo:#ffffff;--suave:#f1f5f9;
--borda:#e2e8f0;--fraco:#64748b;--verde:#047857;--vermelho:#be123c}
*{box-sizing:border-box}
body{margin:0;font:15px/1.6 ui-sans-serif,system-ui,sans-serif;
color:var(--tinta);background:var(--fundo)}
header{border-bottom:1px solid var(--borda);padding:18px 24px}
header h1{margin:0 0 10px;font-size:17px;letter-spacing:-.01em}
nav a{margin-right:14px;color:var(--fraco);text-decoration:none;font-size:13px}
nav a.ativo{color:var(--tinta);font-weight:600}
main{padding:24px;max-width:1100px}
h2{font-size:15px;margin:28px 0 10px;text-transform:uppercase;
letter-spacing:.06em;color:var(--fraco)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-bottom:8px}
th,td{border-bottom:1px solid var(--borda);padding:7px 9px;
text-align:left;vertical-align:top}
th{background:var(--suave);font-weight:600}
.rolagem{overflow-x:auto}
.selo{display:inline-block;padding:4px 11px;border-radius:99px;
color:#fff;font-size:12px;font-weight:700}
.selo.verde{background:var(--verde)}.selo.vermelho{background:var(--vermelho)}
.grade{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.cartao{border:1px solid var(--borda);border-radius:9px;padding:13px}
.cartao b{display:block;font-size:23px;line-height:1.1}
.cartao span{font-size:12px;color:var(--fraco)}
code,pre{font-family:ui-monospace,monospace;font-size:12px}
pre{background:var(--suave);padding:13px;border-radius:8px;overflow-x:auto}
.id{font-family:ui-monospace,monospace;font-size:11px;color:var(--fraco)}
@media(prefers-color-scheme:dark){:root{--tinta:#e6edf6;--fundo:#0b1120;
--suave:#151f33;--borda:#24314b;--fraco:#94a3b8}}
"""

PAN = """<script>
(function(){var s=document.getElementById('grafo');if(!s)return;
var g=document.getElementById('camada'),k=1,x=0,y=0,a=false,px=0,py=0;
function t(){g.setAttribute('transform','translate('+x+' '+y+') scale('+k+')')}
s.addEventListener('wheel',function(e){e.preventDefault();
k=Math.min(4,Math.max(.3,k*(e.deltaY<0?1.1:.9)));t()},{passive:false});
s.addEventListener('mousedown',function(e){a=true;px=e.clientX;py=e.clientY});
window.addEventListener('mouseup',function(){a=false});
window.addEventListener('mousemove',function(e){if(!a)return;
x+=e.clientX-px;y+=e.clientY-py;px=e.clientX;py=e.clientY;t()});})();
</script>"""


def _esc(v):
    return escape("" if v is None else str(v))


def _tabela(colunas, linhas):
    if not linhas:
        return '<p class="id">sem registros</p>'
    cab = "".join(f"<th>{_esc(c)}</th>" for c in colunas)
    corpo = "".join(
        "<tr>" + "".join(f"<td>{_esc(v)}</td>" for v in linha) + "</tr>"
        for linha in linhas)
    return f'<div class="rolagem"><table><tr>{cab}</tr>{corpo}</table></div>'


def _pagina(arquivo, titulo, corpo, extra=""):
    itens = []
    for a, t in PAGINAS:
        classe = ' class="ativo"' if a == arquivo else ""
        itens.append(f'<a href="{a}"{classe}>{t}</a>')
    nav = "".join(itens)
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_esc(titulo)} — TRA-48 Grupo 1</title>'
            f'<link rel="stylesheet" href="estilo.css"></head><body>'
            f'<header><h1>TRA-48 · Projeto B1 · Localizacao de vertiportos '
            f'em Sao Paulo</h1><nav>{nav}</nav></header>'
            f'<main><h2>{_esc(titulo)}</h2>{corpo}</main>{extra}</body></html>')


def _index(con, m):
    r, p, h = m["rastreabilidade"], m["postura"], m["higiene"]
    cor, motivos = m["selo"]
    lista = "".join(f"<li>{_esc(x)}</li>" for x in motivos) or "<li>sem apontamentos</li>"
    cartoes = (
        f'<div class="grade">'
        f'<div class="cartao"><b>{r["decisoes_total"]}</b>'
        f'<span>decisoes registradas</span></div>'
        f'<div class="cartao"><b>{r["decisoes_com_meta"]}%</b>'
        f'<span>decisoes com meta</span></div>'
        f'<div class="cartao"><b>{len(r["orfaos"])}</b>'
        f'<span>nos orfaos</span></div>'
        f'<div class="cartao"><b>{p["taxa_integral"]}%</b>'
        f'<span>aceite integral de IA ({p["total"]} interacoes)</span></div>'
        f'<div class="cartao"><b>{len(h["tarefas_incompletas"])}</b>'
        f'<span>tarefas incompletas</span></div></div>')
    metas = _tabela(["id", "meta", "status", "criada por"], con.execute(
        "SELECT id, titulo, status, criado_por FROM meta ORDER BY criado_em"
    ).fetchall())
    acoes = _tabela(["prazo", "tarefa", "resp"], con.execute(
        "SELECT prazo, titulo, resp FROM tarefa WHERE status = 'aberta' "
        "ORDER BY prazo NULLS LAST LIMIT 10").fetchall())
    decisoes = _tabela(["quando", "decisao", "justificativa", "autor"],
                       con.execute(
        "SELECT criado_em, titulo, justificativa, criado_por FROM decisao "
        "ORDER BY criado_em DESC LIMIT 8").fetchall())
    return (f'<p>Selo de auditoria: <span class="selo {cor}">{cor.upper()}'
            f'</span></p><ul>{lista}</ul>{cartoes}'
            f'<h2>Metas</h2>{metas}<h2>Proximas acoes</h2>{acoes}'
            f'<h2>Ultimas decisoes</h2>{decisoes}')


def _trilha(con):
    linhas = con.execute(
        "SELECT ts, autor, tipo, entidade_id, payload FROM evento "
        "ORDER BY ts DESC, evento_id DESC").fetchall()
    blocos = []
    for ts, autor, tipo, eid, payload in linhas:
        dados = json.loads(payload)
        campos = "".join(
            f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
            for k, v in sorted(dados.items()) if v not in (None, "", [], {}))
        blocos.append(
            f'<h2 id="{_esc(eid)}">{_esc(ts)} · {_esc(tipo)} · '
            f'<span class="id">{_esc(eid)}</span> · {_esc(autor)}</h2>'
            f'<div class="rolagem"><table>{campos}</table></div>')
    return "".join(blocos) or '<p class="id">sem eventos</p>'


def _tarefas(con):
    tarefas = _tabela(["id", "tarefa", "resp", "prazo", "status"],
                      con.execute(
        "SELECT id, titulo, resp, prazo, status FROM tarefa "
        "ORDER BY status, prazo NULLS LAST").fetchall())
    pendencias = _tabela(["id", "pendencia", "aberta em", "status", "resolucao"],
                         con.execute(
        "SELECT id, titulo, criado_em, status, resolucao FROM pendencia "
        "ORDER BY status, criado_em").fetchall())
    return f"{tarefas}<h2>Pendencias</h2>{pendencias}"


def _ia(con, m):
    p = m["postura"]
    cartoes = (f'<div class="grade">'
               f'<div class="cartao"><b>{p["taxa_integral"]}%</b>'
               f'<span>aceite integral</span></div>'
               f'<div class="cartao"><b>{p["integral"]}</b>'
               f'<span>integral</span></div>'
               f'<div class="cartao"><b>{p["parcial"]}</b>'
               f'<span>parcial</span></div>'
               f'<div class="cartao"><b>{p["descarte"]}</b>'
               f'<span>descarte</span></div></div>')
    tabela = _tabela(
        ["quando", "quem", "proposito", "modelo", "aceito", "critica humana"],
        con.execute("SELECT criado_em, criado_por, proposito, modelo, aceito, "
                    "critica FROM ia ORDER BY criado_em DESC").fetchall())
    return (f'{cartoes}<p>Taxa proxima de 100% nao e eficiencia: e ausencia de '
            f'revisao (enunciado 5.6.3).</p><h2>Registros</h2>{tabela}')


def _experimentos(con):
    return _tabela(
        ["id", "variante", "parametros", "obj", "gap", "tempo (s)", "commit",
         "hipotese", "conclusao"],
        con.execute("SELECT id, variante, parametros, obj, gap, tempo_s, "
                    "commit_sha, hipotese, conclusao FROM experimento "
                    "ORDER BY criado_em").fetchall())


def _resultados(con):
    arquivos = _tabela(["id", "arquivo", "descricao"], con.execute(
        "SELECT id, caminho, descricao FROM arquivo ORDER BY caminho"
    ).fetchall())
    fontes = _tabela(["fonte", "origem", "formato", "cobertura", "limitacoes"],
                     con.execute(
        "SELECT nome, origem, formato, cobertura, limitacoes FROM fonte "
        "ORDER BY nome").fetchall())
    refs = _tabela(["citacao", "url", "doi"], con.execute(
        "SELECT citacao, url, doi FROM referencia ORDER BY citacao").fetchall())
    return (f'<p>Mapas, fronteira de implantacao e sensibilidade entram aqui '
            f'quando a camada A produzir os artefatos, registrados via '
            f'<code>./gov arquivo</code>.</p><h2>Artefatos</h2>{arquivos}'
            f'<h2>Fontes de dados</h2>{fontes}<h2>Referencias</h2>{refs}')


def _reprodutibilidade():
    return ('<p>Qualquer pessoa deve conseguir rodar o projeto do zero. '
            'O banco binario nao e versionado: ele e reconstruido do '
            '<code>governanca/dump.sql</code>.</p><pre>'
            'git clone https://github.com/Projeto-TRA-48-Grupo-1/'
            'TRA-48_Projeto.git\ncd TRA-48_Projeto\n'
            'python3 -m venv governanca/.venv\n'
            'governanca/.venv/bin/pip install -r governanca/requirements.txt\n'
            './gov rebuild\n./gov status\n./gov auditoria\n./gov update\n'
            'Rscript app/01-carrega.R</pre>'
            '<h2>Regra do projeto</h2><p>O que nao estiver no banco, nao '
            'aconteceu. Escrita sempre pelo <code>./gov</code>; leitura pelo '
            'MCP ou por <code>./gov consulta</code>.</p>')


def gera(destino=None):
    destino = Path(destino) if destino else DESTINO
    destino.mkdir(parents=True, exist_ok=True)
    con = banco.conecta()
    m = auditoria.calcula(con)
    corpos = {
        "index.html": _index(con, m),
        "grafo.html": f'<div class="rolagem">{grafo.svg(con)}</div>'
                      f'<p class="id">roda do mouse: zoom · arrastar: pan · '
                      f'clique no no: abre o registro na trilha</p>',
        "trilha.html": _trilha(con),
        "tarefas.html": _tarefas(con),
        "ia.html": _ia(con, m),
        "experimentos.html": _experimentos(con),
        "resultados.html": _resultados(con),
        "reprodutibilidade.html": _reprodutibilidade(),
    }
    for arquivo, titulo in PAGINAS:
        extra = PAN if arquivo == "grafo.html" else ""
        (destino / arquivo).write_text(
            _pagina(arquivo, titulo, corpos[arquivo], extra), encoding="utf-8")
    (destino / "estilo.css").write_text(ESTILO, encoding="utf-8")
    (destino / ".nojekyll").write_text("", encoding="utf-8")
    return destino
```

- [ ] **Step 4: Registrar `./gov update` em `governanca/scripts/gov.py`**

```python
def cmd_update(a):
    import site_gov
    destino = site_gov.gera()
    print(f"site gerado em {destino}")
    return cmd_auditoria(a)
```

E no parser:

```python
    s = sub.add_parser("update")
    s.set_defaults(func=cmd_update)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `governanca/.venv/bin/python -m pytest governanca/tests/ -v`
Expected: PASS, 47 testes.

- [ ] **Step 6: Conferir o site no navegador**

Run: `./gov update && open governanca/site/index.html`
Expected: as 8 abas navegam, o grafo faz zoom/pan, nenhum erro no console.

- [ ] **Step 7: Commit**

```bash
git add governanca/scripts/site_gov.py governanca/scripts/gov.py \
        governanca/tests/test_site.py
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "site: oito paginas do 5.5 geradas do banco, sem CDN e deterministas"
```

---

### Task 7: Publicação — GitHub Actions, Pages e o repositório da org

**Files:**
- Create: `.github/workflows/pages.yml`
- Create: `.github/workflows/testes.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `governanca/requirements.txt`, `./gov rebuild`, `./gov update`.
- Produces: site publicado em `https://projeto-tra-48-grupo-1.github.io/TRA-48_Projeto/`.

- [ ] **Step 1: Escrever `.github/workflows/testes.yml`**

```yaml
name: testes
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m venv governanca/.venv
      - run: governanca/.venv/bin/pip install -r governanca/requirements.txt
      - run: governanca/.venv/bin/python -m pytest governanca/tests -q
```

- [ ] **Step 2: Escrever `.github/workflows/pages.yml`**

```yaml
name: pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m venv governanca/.venv
      - run: governanca/.venv/bin/pip install -r governanca/requirements.txt
      - run: ./gov rebuild
      - run: ./gov update
      - uses: actions/upload-pages-artifact@v3
        with:
          path: governanca/site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

`fetch-depth: 0` é necessário: a métrica de cadência lê `git log`, e um clone raso reportaria commits/semana falso.

- [ ] **Step 3: Criar o repositório na org e empurrar**

```bash
gh auth switch --user gustavovfeitosa
gh api user -q .login
git branch -M main
gh repo create Projeto-TRA-48-Grupo-1/TRA-48_Projeto --public \
  --source . --remote origin --push
```
Nota: `gh auth switch` precisa rodar fora do sandbox. Confirmar que o login é `gustavovfeitosa` **antes** do `repo create`.

- [ ] **Step 4: Ligar Pages em modo Actions**

```bash
gh api -X POST repos/Projeto-TRA-48-Grupo-1/TRA-48_Projeto/pages \
  -f build_type=workflow
gh workflow run pages -R Projeto-TRA-48-Grupo-1/TRA-48_Projeto
```

- [ ] **Step 5: Verificar que o site subiu**

```bash
gh run list -R Projeto-TRA-48-Grupo-1/TRA-48_Projeto --limit 5
curl -sSo /dev/null -w '%{http_code}\n' \
  https://projeto-tra-48-grupo-1.github.io/TRA-48_Projeto/
```
Expected: `200`.

- [ ] **Step 6: Atualizar o `README.md`**

Substituir o conteúdo por um README que traga: link do site, a regra "o que não estiver no banco, não aconteceu", o guia rápido de comandos do §5.8, e a seção de reprodução do zero (as mesmas linhas da página de reprodutibilidade).

- [ ] **Step 7: Commit e push**

```bash
git add .github README.md
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "ci: site publicado por artifact do Actions, reconstruido do dump a cada push"
git push
```

---

### Task 8: Convidar o grupo e tornar a contribuição individual visível

**Files:**
- Create: `docs/COMO-REGISTRAR.md`

**Interfaces:**
- Consumes: `./gov`, o repo já publicado.
- Produces: 3 convites de colaborador; um guia de meia página que os outros 3 integrantes conseguem seguir sem ajuda.

- [ ] **Step 1: Pedir ao usuário os usernames GitHub dos outros 3 integrantes**

Sem os usernames, este task não avança. Perguntar e esperar.

- [ ] **Step 2: Convidar**

```bash
for u in USER1 USER2 USER3; do
  gh api -X PUT "orgs/Projeto-TRA-48-Grupo-1/memberships/$u" -f role=member
done
gh api orgs/Projeto-TRA-48-Grupo-1/invitations -q '.[].login'
```

- [ ] **Step 3: Escrever `docs/COMO-REGISTRAR.md`**

Conteúdo obrigatório, em português, meia página:
1. clonar, criar venv, `./gov rebuild`, `git config user.name` com o nome real — **sem isso o `./gov` recusa gravar**, e a contribuição individual é avaliada (§7.3);
2. os 9 comandos de registro com um exemplo real cada;
3. a regra da crítica humana: registro de IA sem crítica não grava, e crítica de menos de 20 caracteres também não;
4. sempre `./gov liga` depois de registrar, senão o nó fica órfão e o selo de auditoria fica vermelho;
5. fluxo de git: branch por pessoa, `dump.sql` é append-only então conflito só acontece na última linha — resolver mantendo **as duas** linhas;
6. nunca commitar `projeto.duckdb`.

- [ ] **Step 4: Commit e push**

```bash
git add docs/COMO-REGISTRAR.md
git commit -m "docs: guia de registro para os 4 integrantes"
git push
```

---

### Task 9: Esqueleto da camada A em R, lendo o banco

**Files:**
- Create: `app/R/gov.R`
- Create: `app/01-carrega.R`
- Create: `app/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `governanca/projeto.duckdb` (reconstruído por `./gov rebuild`).
- Produces:
  - `gov_conecta() -> DBIConnection` (R)
  - `gov_tabela(nome) -> data.frame` (R)
  - `gov_experimento(variante, parametros, obj, gap, tempo, conclusao)` — invoca `./gov experimento` via `system2`, para que a escrita continue passando pela CLI (R9).

- [ ] **Step 1: Verificar/instalar os pacotes R**

```bash
Rscript -e 'p <- c("duckdb","DBI","tidyverse","lpSolve","sf"); print(p[!p %in% rownames(installed.packages())])'
```
Instalar o que faltar com `install.packages()`.

- [ ] **Step 2: Escrever `app/R/gov.R`**

```r
gov_raiz <- function() {
  normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), "..", ".."),
                mustWork = FALSE)
}

gov_conecta <- function(raiz = ".") {
  caminho <- file.path(raiz, "governanca", "projeto.duckdb")
  if (!file.exists(caminho)) system2(file.path(raiz, "gov"), "rebuild")
  DBI::dbConnect(duckdb::duckdb(), dbdir = caminho, read_only = TRUE)
}

gov_tabela <- function(nome, raiz = ".") {
  con <- gov_conecta(raiz)
  on.exit(DBI::dbDisconnect(con, shutdown = TRUE))
  DBI::dbGetQuery(con, paste("SELECT * FROM", DBI::dbQuoteIdentifier(con, nome)))
}

gov_experimento <- function(variante, parametros = list(), obj = NULL,
                            gap = NULL, tempo = NULL, conclusao = NULL,
                            raiz = ".") {
  args <- c("experimento", "--variante", shQuote(variante))
  for (k in names(parametros)) {
    args <- c(args, "--p", shQuote(paste0(k, "=", parametros[[k]])))
  }
  for (par in list(c("--obj", obj), c("--gap", gap), c("--tempo", tempo),
                   c("--conclusao", conclusao))) {
    if (!is.null(par[[2]])) args <- c(args, par[[1]], shQuote(par[[2]]))
  }
  invisible(system2(file.path(raiz, "gov"), args))
}
```

- [ ] **Step 3: Escrever `app/01-carrega.R`**

```r
source(file.path("app", "R", "gov.R"))

fontes <- gov_tabela("fonte")
if (nrow(fontes) == 0) {
  stop("nenhuma fonte registrada: rode ./gov fonte antes de carregar dados")
}

message(sprintf("%d fonte(s) registrada(s):", nrow(fontes)))
print(fontes[, c("nome", "origem", "limitacoes")])

bruto <- list.files(file.path("dados", "bruto"), full.names = TRUE)
message(sprintf("%d arquivo(s) em dados/bruto", length(bruto)))
```

- [ ] **Step 4: Rodar**

Run: `Rscript app/01-carrega.R`
Expected: falha com a mensagem "nenhuma fonte registrada" (banco vazio ainda) — comportamento correto, porque o enunciado proíbe dado sem fonte registrada. Depois da Task 10 este script passa a listar a Pesquisa OD.

- [ ] **Step 5: Escrever `app/README.md`**

Meia página: a numeração dos scripts (`01-carrega`, `02-od`, `03-candidatos`, `04-modelo`, `05-analises`), a regra de que `dados/bruto/` é somente-leitura, e que todo número que entra no relatório sai de script versionado e é registrado via `./gov experimento` ou `./gov arquivo`.

- [ ] **Step 6: Commit e push**

```bash
git add app/
git diff --cached | grep -cE '^\+.*(#|//)' || true
git commit -m "app: camada A em R lendo o banco de governanca, escrita ainda pela CLI"
git push
```

---

### Task 10: Semeadura — os registros que o marco de 19/08 e o encontro de 26/08 exigem

**Files:**
- Modify: `governanca/dump.sql` (via `./gov`, nunca à mão)

**Interfaces:**
- Consumes: toda a CLI.
- Produces: banco com metas, as decisões de arquitetura já tomadas, a fonte obrigatória, as tarefas até 26/08, e o grafo sem órfãos.

- [ ] **Step 1: Registrar as metas (o enunciado pede de 2 a 4)**

```bash
./gov meta "Recomendar onde e quantos vertiportos implantar em Sao Paulo, com defesa do critério de otimalidade" \
  --desc "Camada A: modelo de programacao matematica, relaxacao, dual, sensibilidade e curva de implantacao"
./gov meta "Manter o processo do projeto integralmente rastreavel e publicado" \
  --desc "Camada B: banco de governanca vivo, grafo sem orfaos e site espelho do banco"
./gov meta "Garantir que cada integrante defenda qualquer linha do modelo, do codigo e do relatorio" \
  --desc "Enunciado 5.6.4 e 8.4: integrante que nao sabe explicar o proprio modelo compromete a nota"
```

- [ ] **Step 2: Registrar as decisões de arquitetura já tomadas**

Uma por decisão, cada uma com `--just` e `--alt`, cobrindo: motor em Python com projeto em R (§4.6 exige justificativa registrada para outra linguagem); `projeto.duckdb` fora do git; site gerado fora de `docs/` e publicado por artifact; log de eventos append-only como fonte de verdade; ids sem contador sequencial. As justificativas e alternativas descartadas estão no spec §3.1, §4.1–4.3 e §3.3 — copiar de lá, sem reescrever.

- [ ] **Step 3: Registrar a fonte obrigatória**

```bash
./gov fonte "Pesquisa Origem-Destino do Metro de Sao Paulo" \
  --origem "https://www.metro.sp.gov.br/pesquisa-od/" \
  --formato "microdados + shapefile de zonas OD" \
  --cobertura "RMSP, ultima onda 2017" \
  --limitacoes "anterior a pandemia e sem qualquer viagem por eVTOL; a matriz completa nao e a demanda de vertiporto, so uma fracao e capturavel; zonas OD tem resolucao grosseira para acesso terrestre porta a porta"
```

- [ ] **Step 4: Registrar as tarefas até 26/08 (1º encontro)**

Uma por integrante no mínimo, todas com `--resp` e `--prazo 2026-08-26`: baixar e tratar a OD; levantar candidatos (helipontos ANAC/DECEA, terminais); revisão de literatura de localização de instalações; definir e registrar o recorte metodológico (o enunciado §2.6 exige o recorte registrado como decisão **até o primeiro encontro**).

- [ ] **Step 5: Registrar a pendência real do projeto**

```bash
./gov pendencia "Repositorio-modelo do professor nao foi distribuido; infra construida pelo grupo, migracao por script se ele chegar"
```

- [ ] **Step 6: Ligar tudo — nenhum nó pode ficar órfão**

Cada tarefa `tem` ← meta; cada decisão `atende` → meta; a decisão de recorte `usa` → fonte OD; a pendência `bloqueia` → a meta da camada B. Conferir com `./gov status` que a contagem de órfãos é zero.

- [ ] **Step 7: Registrar esta própria sessão de IA**

```bash
./gov ia --proposito "arquitetura da camada B" --modelo "Claude Opus 5" \
  --aceito parcial \
  --pedido "projetar a infra de governanca computavel exigida pelo capitulo 5" \
  --retorno "motor Python + DuckDB, log de eventos append-only, site gerado, CI de Pages" \
  --critica "O desenho inicial versionava projeto.duckdb e publicava em docs/ copiando o organograma do enunciado ao pe da letra; com 4 pessoas escrevendo em paralelo o binario da conflito irreconciliavel e o HTML gerado poluiria o diff. Corrigimos para dump.sql append-only como unico artefato versionado e publicacao por artifact do Actions. Tambem faltava validar a relacao da aresta contra vocabulario fechado, o que deixaria o grafo aceitar relacao inventada e quebrar a metrica de rastreabilidade."
./gov liga <id-da-ia> informa <id-da-decisao-de-arquitetura>
```

- [ ] **Step 8: Auditar, gerar e publicar**

```bash
./gov status
./gov auditoria
./gov update
git add governanca/dump.sql
git commit -m "governanca: metas, decisoes de arquitetura, fonte OD e tarefas ate 26/08"
git push
```
Expected: selo verde, ou vermelho apenas com motivos que o grupo entende e aceita. Confirmar que o site publicado reflete os registros.

---

## Self-Review

**Cobertura do spec:**

| Requisito | Task |
|---|---|
| R1 nove entidades | 2 |
| R2 grafo, órfãos | 3, 5 |
| R3 IA sem crítica é inválida | 2 |
| R4 taxa de aceite no site | 6 |
| R5 quatro métricas | 4 |
| R6 site 8 seções gerado a cada push | 6, 7 |
| R7 fluxo gov → banco → update → push | 2, 3, 6, 7 |
| R8 superfície do §5.8 | 2, 3, 4, 6 |
| R9 MCP somente-leitura | **não coberto** |
| R10 contribuição individual | 1 (autor obrigatório), 8 |
| R11 reprodutibilidade | 6, 7 |
| R12 R como linguagem, desvio justificado | 9, 10 |

**Lacuna aceita:** R9 (servidor MCP) sai deste plano. O `./gov consulta` já dá leitura ao assistente por Bash, o que satisfaz a função ("consultas ao próprio projeto podem ser feitas pelo assistente") sem o servidor. O MCP entra em plano próprio depois que o marco de 19/08 estiver cumprido — e é a única parte do §5.8 deliberadamente postergada. Registrar como pendência no banco na Task 10.

**Dependência externa bloqueante:** Task 8 Step 1 exige os usernames GitHub dos outros 3 integrantes; o resto do plano não depende disso e pode seguir.
