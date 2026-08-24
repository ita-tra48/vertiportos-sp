# Camada B pública — GitHub, Mach1-Bot, worktrees e grafo-como-contexto

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar o projeto TRA-48 no GitHub (org `ita-tra48`, repo `vertiportos-sp`) com Pages, regras de PR, bot de review Mach1-Bot, trabalho paralelo por worktrees e o grafo de governança como índice de contexto para IA.

**Architecture:** O motor local (gov.py + DuckDB + site) já existe. Este plano adiciona: dois comandos novos na CLI (`contexto`, `worktree`), um servidor MCP somente-leitura, um validador de estrutura, os documentos de ordem (ARQUITETURA, PADRAO_PR, PROMPT do bot), quatro workflows do GitHub Actions e a criação/configuração do repo remoto. Fecha registrando tudo no próprio banco.

**Tech Stack:** Python 3.12 (stdlib + duckdb), pytest, GitHub Actions, gh CLI, anthropics/claude-code-action@v1, R/lintr (só no CI).

**Spec:** `docs/superpowers/specs/2026-08-24-tra48-github-governanca-design.md` (e o anterior `2026-08-20-tra48-governanca-design.md` para o motor).

## Global Constraints

- Dependências Python: **somente** `duckdb` e `pytest` (`governanca/requirements.txt`); todo o resto é stdlib.
- Comentários de código: quase zero — teto de 1 linha de comentário por commit (preferência global do usuário). Antes de cada commit: `git diff --cached | grep -cE '^\+.*(//|#|/\*|<!--)'` e apagar excedentes (cuidado: `#!/usr/bin/env` e strings não contam).
- Identificadores e mensagens de commit em português sem acento; conteúdo de docs pode ter acento.
- Conta GitHub: `gustavovfeitosa`. A conta `gustavovidal-tiktok` é PROIBIDA neste projeto.
- Saídas geradas (site, SVG) devem ser determinísticas — nunca usar `datetime.now()`/aleatoriedade em geração de site.
- Todos os testes rodam com: `cd ~/Documents/ITA/TRA-48_Projeto && governanca/.venv/bin/python -m pytest governanca/tests -q` (abreviado abaixo como `pytest ...`).
- A CLI se testa em processo via `gov.main([...])` com a fixture `tmp_repo` (já existe em `governanca/tests/conftest.py`), nunca contra o banco real.
- Passos marcados **[USUÁRIO]** são interativos e do Gustavo — o executor para e pede.

---

### Task 1: Identidade — conta gh e autor git

**Files:** nenhum (configuração local).

**Interfaces:**
- Produces: `gh` ativo em `gustavovfeitosa`; `git config user.name`/`user.email` definidos no repo (a CLI `gov` exige autor para registrar).

- [ ] **Step 1: Trocar a conta ativa do gh**

Run: `gh auth switch --user gustavovfeitosa && gh auth status --active`
Expected: `Active account: true` para `gustavovfeitosa`.

- [ ] **Step 2: Configurar autor git local do repo**

```bash
cd ~/Documents/ITA/TRA-48_Projeto
git config user.name "Gustavo Vidal"
git config user.email "gustavo.vidal@brendi.com.br"
git config user.name && git config user.email
```
Expected: os dois valores impressos.

- [ ] **Step 3: [USUÁRIO] Confirmar e-mail de commit**

Perguntar ao Gustavo se prefere o e-mail pessoal/acadêmico ao da Brendi para commits públicos do ITA (ou o noreply do GitHub: `gustavovfeitosa@users.noreply.github.com`). Ajustar `git config user.email` conforme a resposta.

---

### Task 2: `./gov contexto` — vizinhança do grafo como pacote de contexto

**Files:**
- Create: `governanca/scripts/contexto.py`
- Modify: `governanca/scripts/gov.py` (novo subcomando)
- Test: `governanca/tests/test_contexto.py`

**Interfaces:**
- Consumes: `banco.conecta(somente_leitura=True)`, `banco.resolve(ref)`, views `no` e `aresta`.
- Produces: `contexto.vizinhanca(con, entidade_id, raio) -> (set[str], list[tuple[str,str,str]])`; `contexto.registros(con, ids) -> list[dict]`; `contexto.markdown(centro, raio, regs, arestas) -> str`; CLI `./gov contexto ID [--raio N] [--json]`.

- [ ] **Step 1: Escrever os testes que falham**

```python
import json

import banco
import contexto
import gov


def _semeia(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("meta", "met-000001",
                   {"titulo": "meta um", "status": "aberta"})
    banco.registra("tarefa", "tar-000001",
                   {"titulo": "tarefa um", "resp": "Ana", "status": "aberta"})
    banco.registra("decisao", "dec-000001",
                   {"titulo": "decisao um", "just": "porque sim", "alt": [],
                    "status": "vigente"})
    banco.registra("fonte", "fon-000001",
                   {"titulo": "fonte um", "origem": "https://x",
                    "limitacoes": "poucas"})
    banco.registra("arquivo", "arq-000001",
                   {"titulo": "app/01-carrega.R", "desc": None})
    banco.registra("aresta", "met-000001",
                   {"relacao": "tem", "destino": "tar-000001"})
    banco.registra("aresta", "dec-000001",
                   {"relacao": "atende", "destino": "met-000001"})
    banco.registra("aresta", "dec-000001",
                   {"relacao": "usa", "destino": "fon-000001"})
    banco.registra("aresta", "arq-000001",
                   {"relacao": "deriva", "destino": "dec-000001"})


def test_raio_1_traz_so_vizinhos_diretos(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    nos, arestas = contexto.vizinhanca(banco.conecta(), "met-000001", 1)
    assert nos == {"met-000001", "tar-000001", "dec-000001"}
    assert ("met-000001", "tem", "tar-000001") in arestas
    assert ("dec-000001", "usa", "fon-000001") not in arestas


def test_raio_2_alcanca_fonte_e_arquivo(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    nos, arestas = contexto.vizinhanca(banco.conecta(), "met-000001", 2)
    assert {"fon-000001", "arq-000001"} <= nos
    assert ("dec-000001", "usa", "fon-000001") in arestas


def test_no_isolado_tem_vizinhanca_vazia(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("pendencia", "pen-000001",
                   {"titulo": "solta", "status": "aberta"})
    nos, arestas = contexto.vizinhanca(banco.conecta(), "pen-000001", 3)
    assert nos == {"pen-000001"}
    assert arestas == []


def test_cli_markdown_lista_registros_e_arquivos(tmp_repo, monkeypatch, capsys):
    _semeia(monkeypatch)
    assert gov.main(["contexto", "met-000001", "--raio", "2"]) == 0
    saida = capsys.readouterr().out
    assert "met-000001" in saida
    assert "porque sim" in saida
    assert "app/01-carrega.R" in saida
    assert "—tem→" in saida


def test_cli_json_estruturado(tmp_repo, monkeypatch, capsys):
    _semeia(monkeypatch)
    assert gov.main(["contexto", "dec-000001", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["centro"] == "dec-000001"
    ids = {r["id"] for r in doc["registros"]}
    assert "met-000001" in ids
    assert {"origem", "relacao", "destino"} <= set(doc["arestas"][0])


def test_cli_aceita_prefixo_e_rejeita_desconhecido(tmp_repo, monkeypatch, capsys):
    _semeia(monkeypatch)
    assert gov.main(["contexto", "met-0"]) == 0
    assert gov.main(["contexto", "zzz-999999"]) == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest governanca/tests/test_contexto.py -q`
Expected: FAIL/ERROR com `ModuleNotFoundError: contexto`.

- [ ] **Step 3: Implementar `governanca/scripts/contexto.py`**

```python
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
```

- [ ] **Step 4: Ligar na CLI (`gov.py`)**

Adicionar `import contexto` no topo (junto de `auditoria`/`banco`), a função:

```python
def cmd_contexto(a):
    try:
        entidade_id = banco.resolve(a.id)
    except ValueError as exc:
        return _erro(str(exc))
    con = banco.conecta(somente_leitura=True)
    nos, arestas = contexto.vizinhanca(con, entidade_id, a.raio)
    regs = contexto.registros(con, nos)
    if a.json:
        print(json.dumps(
            {"centro": entidade_id, "raio": a.raio, "registros": regs,
             "arestas": [{"origem": o, "relacao": r, "destino": d}
                         for o, r, d in arestas]},
            ensure_ascii=False, indent=2))
    else:
        print(contexto.markdown(entidade_id, a.raio, regs, arestas))
    return 0
```

e em `constroi_parser()`:

```python
    s = sub.add_parser("contexto")
    s.add_argument("id")
    s.add_argument("--raio", type=int, default=1)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_contexto)
```

- [ ] **Step 5: Rodar todos os testes**

Run: `pytest governanca/tests -q`
Expected: tudo PASS (os antigos continuam verdes).

- [ ] **Step 6: Commit**

```bash
git add governanca/scripts/contexto.py governanca/scripts/gov.py governanca/tests/test_contexto.py
git commit -m "gov contexto: vizinhanca do grafo como pacote de contexto para IA"
```

---

### Task 3: `./gov worktree` — 1 tarefa = 1 branch = 1 worktree

**Files:**
- Modify: `governanca/scripts/gov.py`
- Test: `governanca/tests/test_worktree.py`

**Interfaces:**
- Consumes: `banco.resolve`, `_payload_atual(entidade_id) -> (tipo, payload)`, `banco.registra`, `banco.RAIZ`.
- Produces: CLI `./gov worktree TAR-ID [--slug texto] [--base main]`; branch `tarefa/<tar-id>[-slug]`; worktree em `<raiz>.worktrees/<tar-id>/` (irmã da raiz); payload da tarefa ganha `branch`.

- [ ] **Step 1: Escrever os testes que falham**

```python
import subprocess

import banco
import gov


def _git(raiz, *args):
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


def _repo_git(raiz):
    _git(raiz, "init", "-b", "main")
    _git(raiz, "config", "user.name", "Teste")
    _git(raiz, "config", "user.email", "t@t")
    (raiz / "raiz.txt").write_text("x")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-m", "raiz")


def test_cria_branch_worktree_e_registra(tmp_repo, monkeypatch, capsys):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("tarefa", "tar-000001",
                   {"titulo": "estimar demanda", "resp": "Ana",
                    "status": "aberta"})
    _repo_git(tmp_repo)
    assert gov.main(["worktree", "tar-000001", "--slug", "demanda"]) == 0
    destino = tmp_repo.parent / f"{tmp_repo.name}.worktrees" / "tar-000001"
    assert destino.is_dir()
    assert str(destino) in capsys.readouterr().out
    ramos = subprocess.run(["git", "branch", "--list", "tarefa/*"],
                           cwd=tmp_repo, capture_output=True,
                           text=True).stdout
    assert "tarefa/tar-000001-demanda" in ramos
    branch = banco.conecta().execute(
        "SELECT payload->>'branch' FROM no WHERE entidade_id = 'tar-000001'"
    ).fetchone()[0]
    assert branch == "tarefa/tar-000001-demanda"


def test_idempotente_se_worktree_existe(tmp_repo, monkeypatch, capsys):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("tarefa", "tar-000002",
                   {"titulo": "t", "resp": "Ana", "status": "aberta"})
    _repo_git(tmp_repo)
    assert gov.main(["worktree", "tar-000002"]) == 0
    eventos_antes = banco.conecta().execute(
        "SELECT count(*) FROM evento").fetchone()[0]
    assert gov.main(["worktree", "tar-000002"]) == 0
    eventos_depois = banco.conecta().execute(
        "SELECT count(*) FROM evento").fetchone()[0]
    assert eventos_depois == eventos_antes


def test_recusa_no_que_nao_e_tarefa(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("meta", "met-000001",
                   {"titulo": "m", "status": "aberta"})
    _repo_git(tmp_repo)
    assert gov.main(["worktree", "met-000001"]) == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest governanca/tests/test_worktree.py -q`
Expected: FAIL (argparse: `invalid choice: 'worktree'`).

- [ ] **Step 3: Implementar em `gov.py`**

Adicionar `import subprocess` no topo, a função:

```python
def cmd_worktree(a):
    try:
        entidade_id = banco.resolve(a.tarefa)
        tipo, payload = _payload_atual(entidade_id)
    except ValueError as exc:
        return _erro(str(exc))
    if tipo != "tarefa":
        return _erro(f"worktree exige tarefa, mas {entidade_id} e do tipo {tipo}")
    destino = banco.RAIZ.parent / f"{banco.RAIZ.name}.worktrees" / entidade_id
    if destino.exists():
        print(destino)
        return 0
    sufixo = f"-{a.slug}" if a.slug else ""
    branch = payload.get("branch") or f"tarefa/{entidade_id}{sufixo}"
    destino.parent.mkdir(parents=True, exist_ok=True)

    def _existe(ref):
        return subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=banco.RAIZ, capture_output=True).returncode == 0

    if _existe(branch):
        cmd = ["git", "worktree", "add", str(destino), branch]
    else:
        cmd = ["git", "worktree", "add", "-b", branch, str(destino)]
        if _existe(a.base):
            cmd.append(a.base)
    r = subprocess.run(cmd, cwd=banco.RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        return _erro(r.stderr.strip())
    if payload.get("branch") != branch:
        payload["branch"] = branch
        banco.registra("tarefa", entidade_id, payload)
    print(destino)
    return 0
```

e no parser:

```python
    s = sub.add_parser("worktree")
    s.add_argument("tarefa")
    s.add_argument("--slug")
    s.add_argument("--base", default="main")
    s.set_defaults(func=cmd_worktree)
```

- [ ] **Step 4: Rodar todos os testes**

Run: `pytest governanca/tests -q`
Expected: tudo PASS.

- [ ] **Step 5: Adicionar `*.worktrees/` ao `.gitignore` da raiz** (linha `../` não funciona; o diretório é irmão da raiz, então nada a ignorar — pular se for o caso; confirmar com `git status` que nada novo aparece).

- [ ] **Step 6: Commit**

```bash
git add governanca/scripts/gov.py governanca/tests/test_worktree.py
git commit -m "gov worktree: uma tarefa, um branch, um worktree, com vinculo no grafo"
```

---

### Task 4: MCP somente-leitura ligado ao DuckDB

**Files:**
- Create: `governanca/scripts/mcp_gov.py`, `.mcp.json`
- Test: `governanca/tests/test_mcp.py`

**Interfaces:**
- Consumes: `banco.conecta(somente_leitura=True)`, `banco.resolve`, `contexto.vizinhanca/registros/markdown`, `auditoria.calcula`.
- Produces: `mcp_gov.despacha(msg: dict) -> dict | None` (JSON-RPC 2.0); ferramentas `consultar`, `no`, `vizinhos`, `contexto`, `auditoria`; servidor stdio via `main()`.

- [ ] **Step 1: Escrever os testes que falham**

```python
import json

import banco
import mcp_gov


def _chama(nome, argumentos, mid=7):
    return mcp_gov.despacha({"jsonrpc": "2.0", "id": mid,
                             "method": "tools/call",
                             "params": {"name": nome,
                                        "arguments": argumentos}})


def _texto(resposta):
    return resposta["result"]["content"][0]["text"]


def _semeia(monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    banco.registra("decisao", "dec-000001",
                   {"titulo": "usar p-mediana", "just": "literatura",
                    "alt": [], "status": "vigente"})
    banco.registra("meta", "met-000001",
                   {"titulo": "m", "status": "aberta"})
    banco.registra("aresta", "dec-000001",
                   {"relacao": "atende", "destino": "met-000001"})


def test_initialize_e_tools_list(tmp_repo):
    ini = mcp_gov.despacha({"jsonrpc": "2.0", "id": 1,
                            "method": "initialize", "params": {}})
    assert ini["result"]["protocolVersion"]
    assert mcp_gov.despacha({"jsonrpc": "2.0",
                             "method": "notifications/initialized"}) is None
    lista = mcp_gov.despacha({"jsonrpc": "2.0", "id": 2,
                              "method": "tools/list"})
    nomes = {t["name"] for t in lista["result"]["tools"]}
    assert nomes == {"consultar", "no", "vizinhos", "contexto", "auditoria"}


def test_consultar_select_funciona(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    r = _chama("consultar", {"sql": "SELECT count(*) AS n FROM decisao"})
    assert r["result"]["isError"] is False
    assert "1" in _texto(r)


def test_consultar_recusa_escrita(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    r = _chama("consultar", {"sql": "DELETE FROM evento"})
    assert r["result"]["isError"] is True


def test_no_aceita_prefixo(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    r = _chama("no", {"id": "dec-0"})
    assert "usar p-mediana" in _texto(r)


def test_contexto_e_vizinhos(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    assert "met-000001" in _texto(_chama("vizinhos", {"id": "dec-000001"}))
    assert "atende" in _texto(_chama("contexto", {"id": "dec-000001",
                                                  "raio": 2}))


def test_auditoria_retorna_selo(tmp_repo, monkeypatch):
    _semeia(monkeypatch)
    doc = json.loads(_texto(_chama("auditoria", {})))
    assert "selo" in doc


def test_metodo_desconhecido_da_erro(tmp_repo):
    r = mcp_gov.despacha({"jsonrpc": "2.0", "id": 9, "method": "prompts/list"})
    assert r["error"]["code"] == -32601
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest governanca/tests/test_mcp.py -q`
Expected: `ModuleNotFoundError: mcp_gov`.

- [ ] **Step 3: Implementar `governanca/scripts/mcp_gov.py`**

```python
import json
import sys

import auditoria
import banco
import contexto

PROTOCOLO = "2024-11-05"

FERRAMENTAS = [
    {"name": "consultar",
     "description": "roda SELECT/WITH no banco de governanca",
     "inputSchema": {"type": "object",
                     "properties": {"sql": {"type": "string"}},
                     "required": ["sql"]}},
    {"name": "no",
     "description": "registro completo de um no (aceita prefixo de id)",
     "inputSchema": {"type": "object",
                     "properties": {"id": {"type": "string"}},
                     "required": ["id"]}},
    {"name": "vizinhos",
     "description": "arestas diretas de um no",
     "inputSchema": {"type": "object",
                     "properties": {"id": {"type": "string"}},
                     "required": ["id"]}},
    {"name": "contexto",
     "description": "pacote de contexto: vizinhanca do no ate o raio dado",
     "inputSchema": {"type": "object",
                     "properties": {"id": {"type": "string"},
                                    "raio": {"type": "integer", "default": 1}},
                     "required": ["id"]}},
    {"name": "auditoria",
     "description": "metricas de rastreabilidade, cadencia, higiene e postura",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _leitura():
    con = banco.conecta(somente_leitura=True)
    con.execute("SET enable_external_access = false")
    return con


def _consultar(sql):
    sql = sql.strip().rstrip(";")
    if not sql.lower().startswith(("select", "with")):
        raise ValueError("apenas SELECT ou WITH")
    if ";" in sql:
        raise ValueError("um statement por consulta")
    cur = _leitura().execute(sql)
    colunas = [d[0] for d in cur.description]
    linhas = [" | ".join(colunas)]
    for linha in cur.fetchall():
        linhas.append(" | ".join("" if v is None else str(v) for v in linha))
    return "\n".join(linhas)


def executa(nome, args):
    if nome == "consultar":
        return _consultar(args["sql"])
    if nome == "auditoria":
        return json.dumps(auditoria.calcula(_leitura()),
                          ensure_ascii=False, default=str, indent=2)
    entidade_id = banco.resolve(args["id"])
    con = _leitura()
    if nome == "no":
        regs = contexto.registros(con, {entidade_id})
        return json.dumps(regs[0], ensure_ascii=False, indent=2)
    if nome == "vizinhos":
        _, arestas = contexto.vizinhanca(con, entidade_id, 1)
        return "\n".join(f"{o} —{r}→ {d}" for o, r, d in arestas) or "sem arestas"
    if nome == "contexto":
        raio = int(args.get("raio") or 1)
        nos, arestas = contexto.vizinhanca(con, entidade_id, raio)
        return contexto.markdown(entidade_id, raio,
                                 contexto.registros(con, nos), arestas)
    raise ValueError(f"ferramenta desconhecida: {nome}")


def despacha(msg):
    mid = msg.get("id")
    metodo = msg.get("method")
    if metodo == "initialize":
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"protocolVersion": PROTOCOLO,
                           "capabilities": {"tools": {}},
                           "serverInfo": {"name": "gov", "version": "1.0.0"}}}
    if mid is None:
        return None
    if metodo == "tools/list":
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"tools": FERRAMENTAS}}
    if metodo == "tools/call":
        nome = msg["params"]["name"]
        args = msg["params"].get("arguments") or {}
        try:
            texto, erro = executa(nome, args), False
        except Exception as exc:
            texto, erro = f"erro: {exc}", True
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text", "text": texto}],
                           "isError": erro}}
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601,
                      "message": f"metodo desconhecido: {metodo}"}}


def main():
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        resposta = despacha(json.loads(linha))
        if resposta is not None:
            sys.stdout.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Criar `.mcp.json` na raiz**

```json
{
  "mcpServers": {
    "gov": {
      "command": "governanca/.venv/bin/python",
      "args": ["governanca/scripts/mcp_gov.py"]
    }
  }
}
```

- [ ] **Step 5: Rodar todos os testes**

Run: `pytest governanca/tests -q`
Expected: tudo PASS.

- [ ] **Step 6: Fumaça manual do servidor**

Run: `printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | governanca/.venv/bin/python governanca/scripts/mcp_gov.py`
Expected: duas linhas JSON, a segunda listando as 5 ferramentas.

- [ ] **Step 7: Commit**

```bash
git add governanca/scripts/mcp_gov.py governanca/tests/test_mcp.py .mcp.json
git commit -m "mcp somente-leitura: consultar, no, vizinhos, contexto e auditoria via stdio"
```

---

### Task 5: `valida_estrutura.py` — as regras mecânicas do ARQUITETURA.md

**Files:**
- Create: `governanca/scripts/valida_estrutura.py`
- Test: `governanca/tests/test_valida_estrutura.py`

**Interfaces:**
- Consumes: `banco.RAIZ`, `banco.conecta(somente_leitura=True)`, views `no`/`aresta`.
- Produces: `scripts_fora_do_padrao(raiz) -> list[str]`; `bruto_alterado(raiz, base) -> list[str]`; `figuras_sem_gerador(raiz) -> list[str]`; `main(argv) -> int` (0 limpo, 1 com problemas em stderr). CLI: `python governanca/scripts/valida_estrutura.py [--base REF]`.

- [ ] **Step 1: Escrever os testes que falham**

```python
import subprocess

import banco
import valida_estrutura


def _git(raiz, *args):
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


def test_scripts_de_app_devem_ser_numerados(tmp_repo):
    app = tmp_repo / "app"
    app.mkdir()
    (app / "01-carrega.R").write_text("x <- 1\n")
    (app / "modelo.R").write_text("x <- 1\n")
    (app / "R").mkdir()
    (app / "R" / "gov.R").write_text("x <- 1\n")
    assert valida_estrutura.scripts_fora_do_padrao(tmp_repo) == ["modelo.R"]


def test_bruto_alterado_no_diff(tmp_repo):
    _git(tmp_repo, "init", "-b", "main")
    _git(tmp_repo, "config", "user.name", "T")
    _git(tmp_repo, "config", "user.email", "t@t")
    bruto = tmp_repo / "dados" / "bruto"
    bruto.mkdir(parents=True)
    (bruto / ".gitkeep").write_text("")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-m", "base")
    _git(tmp_repo, "checkout", "-b", "tarefa/x")
    (bruto / "od.csv").write_text("a,b\n")
    _git(tmp_repo, "add", "-A")
    _git(tmp_repo, "commit", "-m", "mexe no bruto")
    assert valida_estrutura.bruto_alterado(tmp_repo, "main") == \
        ["dados/bruto/od.csv"]


def test_figura_sem_produz_e_apontada(tmp_repo, monkeypatch):
    monkeypatch.setenv("GOV_AUTOR", "Teste")
    figuras = tmp_repo / "relatorio" / "figuras"
    figuras.mkdir(parents=True)
    (figuras / "mapa.png").write_bytes(b"png")
    (figuras / "curva.png").write_bytes(b"png")
    banco.registra("arquivo", "arq-000001",
                   {"titulo": "app/04-mapa.R", "desc": None})
    banco.registra("arquivo", "arq-000002",
                   {"titulo": "relatorio/figuras/mapa.png", "desc": None})
    banco.registra("aresta", "arq-000001",
                   {"relacao": "produz", "destino": "arq-000002"})
    assert valida_estrutura.figuras_sem_gerador(tmp_repo) == \
        ["relatorio/figuras/curva.png"]


def test_main_devolve_1_com_problema(tmp_repo, capsys):
    app = tmp_repo / "app"
    app.mkdir()
    (app / "solto.R").write_text("x <- 1\n")
    assert valida_estrutura.main([]) == 1
    assert "solto.R" in capsys.readouterr().err


def test_main_devolve_0_limpo(tmp_repo):
    assert valida_estrutura.main([]) == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest governanca/tests/test_valida_estrutura.py -q`
Expected: `ModuleNotFoundError: valida_estrutura`.

- [ ] **Step 3: Implementar**

```python
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
        return []
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
```

- [ ] **Step 4: Rodar todos os testes**

Run: `pytest governanca/tests -q`
Expected: tudo PASS. Rodar também contra o repo real: `governanca/.venv/bin/python governanca/scripts/valida_estrutura.py` → exit 0.

- [ ] **Step 5: Commit**

```bash
git add governanca/scripts/valida_estrutura.py governanca/tests/test_valida_estrutura.py
git commit -m "valida_estrutura: scripts numerados, bruto intocado e figura com gerador no grafo"
```

---

### Task 6: Documentos de ordem, integrantes e esqueleto do app/

**Files:**
- Create: `docs/ARQUITETURA.md`, `docs/PADRAO_PR.md`, `.github/pull_request_template.md`, `governanca/integrantes.json`, `governanca/mach1/PROMPT.md`, `app/.gitkeep`, `app/R/.gitkeep`
- Modify: `CLAUDE.md`, `README.md`, `.gitignore`

**Interfaces:**
- Produces: `governanca/integrantes.json` = objeto `{username: nome}` (consumido por `reviewers.yml`); `governanca/mach1/PROMPT.md` (consumido por `mach1-bot.yml`); regras que `valida_estrutura.py` e o Mach1-Bot aplicam.

- [ ] **Step 1: `governanca/integrantes.json`**

```json
{
  "gustavovfeitosa": "Gustavo Vidal",
  "t27matheus": "t27matheus",
  "oitalorabelo": "oitalorabelo",
  "monteirocarloss021": "monteirocarloss021"
}
```

(Os três nomes de exibição ficam iguais ao username até o grupo preencher — registrar tarefa disso na Task 9.)

- [ ] **Step 2: `docs/ARQUITETURA.md`**

```markdown
# Ordem de arquitetura de código

Este documento é lei para humanos, para a IA que escreve código e para o
Mach1-Bot que revisa PRs. O CI aplica a parte mecânica
(`governanca/scripts/valida_estrutura.py`); o resto é julgamento do revisor.

## Layout

| pasta | conteúdo | regra |
|---|---|---|
| `app/` | camada A, 100% R | um script por etapa, `NN-nome.R` (ex.: `01-carrega.R`); funções auxiliares em `app/R/` |
| `dados/bruto/` | dados originais | somente leitura; nunca aparece em diff |
| `dados/tratado/` | saídas de preparação | só escrito por script de `app/` |
| `governanca/` | motor da camada B | Python fica **só** em `governanca/scripts/` |
| `relatorio/` | Quarto/RMarkdown + `figuras/` | figura só nasce de script, ligada no grafo por `produz` |
| `apresentacao/` | slides | — |
| `docs/` | documentos-fonte, specs, planos | nunca artefato gerado |

## R (`app/`)

- Estilo tidyverse, verificado por `lintr` no CI.
- Caminhos sempre relativos à raiz do repo; `setwd()` é proibido.
- Sem `install.packages()` em script; dependências declaradas em
  `app/00-pacotes.R`.
- Nomes de objetos e arquivos em português, sem acento, `snake_case`.
- Todo resultado numérico citado no relatório sai de script versionado.

## Comentários

Quase zero. Só o que o código não diz sozinho. Contexto, justificativa e
"por quê" vão no registro `gov` e na descrição da PR — nunca no código.

## Governança antes do commit

Toda decisão metodológica, fonte, experimento e interação com IA vira
registro via `./gov` **antes** do commit que a materializa. PR sem ids de
registro na descrição é devolvida (ver docs/PADRAO_PR.md).
```

- [ ] **Step 3: `docs/PADRAO_PR.md`**

```markdown
# Padrão de descrição de PR

Vale para qualquer autor — humano ou IA. O Mach1-Bot cobra este padrão.

## Estrutura obrigatória

    ## O que muda
    Uma a três frases, no presente, sem jargão vazio.

    ## Por quê
    A motivação. Se existe decisão registrada, ela é citada aqui.

    ## Registros
    Ids `gov` desta PR (obrigatório ≥ 1): a tarefa que ela executa
    (`tar-...`), decisões que aplica (`dec-...`), experimentos que
    reporta (`exp-...`). Um id por linha, com um fragmento do título.

    ## Como verificar
    Comandos concretos: o teste que cobre, o script que roda, a página
    do site que muda.

## Regras

1. Sem seção vazia. Sem "vários ajustes", "melhorias gerais", "WIP".
2. Título da PR: minúsculo, imperativo, ≤ 72 caracteres
   (ex.: `estima demanda capturavel por limiar de tempo`).
3. PR de IA declara o registro `ia-...` correspondente em **Registros**.
4. Uma PR = uma tarefa. Se a descrição precisa de "além disso", divida.
```

- [ ] **Step 4: `.github/pull_request_template.md`**

```markdown
## O que muda

## Por quê

## Registros
<!-- obrigatorio: ids gov (tar-/dec-/exp-/ia-), um por linha — ver docs/PADRAO_PR.md -->

## Como verificar
```

- [ ] **Step 5: `governanca/mach1/PROMPT.md`**

```markdown
# Mach1-Bot — protocolo de revisão

Você é o **Mach1-Bot**, revisor automático deste repositório. Você não
aprova nem bloqueia: você comenta. O gate é o CI e o review humano.

Variáveis: o número da PR e o repositório chegam no prompt do workflow.

1. Rode `python governanca/scripts/gov.py rebuild`.
2. Leia título e corpo da PR (`gh pr view N --json title,body`). Extraia
   os ids de registro (`met-|tar-|pen-|dec-|fon-|arq-|ref-|exp-|ia-`).
   Se não houver nenhum id: publique um comentário apontando a violação
   do `docs/PADRAO_PR.md`, pedindo os registros, e PARE.
3. Para cada id, rode `python governanca/scripts/gov.py contexto ID --raio 2`.
   Esse é o seu contexto de trabalho. Não varra `docs/` nem o repositório
   inteiro atrás de contexto.
4. Leia `docs/ARQUITETURA.md`. Revise o diff (`gh pr diff N`) contra ele:
   layout de pastas, padrão `NN-nome.R`, R fora de `app/`, Python fora de
   `governanca/scripts/`, comentários além do teto, escrita em
   `dados/bruto/`, figura sem script gerador.
5. Cheque coerência com a governança: o diff faz o que a tarefa/decisão
   citada diz? A decisão está `vigente`? Experimento reportado bate com o
   registro?
6. Publique UM único comentário (`gh pr comment N --body ...`) começando
   por `**Mach1-Bot**`, contendo: incongruências (com `arquivo:linha`),
   o que está conforme, e um checklist do PADRAO_PR. Direto, sem elogio
   de cortesia. Se não houver incongruência, diga isso em uma linha.
```

- [ ] **Step 6: Atualizar `CLAUDE.md`** — acrescentar ao final:

```markdown
## Governança é lei

- Contexto de trabalho se adquire pelo grafo: `./gov contexto ID --raio 2`
  (ou MCP `gov`), a partir dos ids da tarefa/decisão. Ler `docs/` inteiro
  é último recurso.
- Fluxo de trabalho: tarefa registrada → `./gov worktree TAR-ID` → código
  no worktree → registros (`decisao`, `experimento`, `ia`) → `./gov update`
  → PR conforme `docs/PADRAO_PR.md`.
- Arquitetura de código: `docs/ARQUITETURA.md`. Descrição de PR:
  `docs/PADRAO_PR.md`. Toda interação de IA que chega ao produto vira
  `./gov ia --critica "..."` antes do commit.
```

- [ ] **Step 7: Esqueleto do `app/` e ajustes**

```bash
mkdir -p app/R
touch app/.gitkeep app/R/.gitkeep
```

Em `README.md`, trocar a linha `R/               # scripts numerados` por `app/             # camada A em R: scripts numerados + app/R/ auxiliares` e remover o diretório vazio `R/` (`rmdir R`). Em `.gitignore`, acrescentar:

```
Enunciado/
docs/*.pdf
```

(PDFs do professor têm direitos autorais — não vão para repo público; a remoção do que já está rastreado é a Task 8 Step 1.)

- [ ] **Step 8: Verificação**

Run: `governanca/.venv/bin/python governanca/scripts/valida_estrutura.py && python3 -c "import json; print(list(json.load(open('governanca/integrantes.json'))))"`
Expected: exit 0 e a lista dos 4 usernames.

- [ ] **Step 9: Commit**

```bash
git add docs/ARQUITETURA.md docs/PADRAO_PR.md .github/pull_request_template.md governanca/integrantes.json governanca/mach1/PROMPT.md app/.gitkeep app/R/.gitkeep CLAUDE.md README.md .gitignore
git commit -m "documentos de ordem: arquitetura, padrao de PR, prompt do mach1-bot e integrantes"
```

---

### Task 7: Workflows do GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/reviewers.yml`, `.github/workflows/mach1-bot.yml`, `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: `governanca/integrantes.json`, `governanca/mach1/PROMPT.md`, `valida_estrutura.py`, `gov.py update/rebuild`, secret `CLAUDE_CODE_OAUTH_TOKEN` (Task 8).
- Produces: check `resultado` (o único exigido pela proteção da main); deploy do Pages a partir de `governanca/site/`.

- [ ] **Step 1: `.github/workflows/ci.yml`**

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  mudancas:
    runs-on: ubuntu-latest
    outputs:
      governanca: ${{ steps.filtro.outputs.governanca }}
      app: ${{ steps.filtro.outputs.app }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: filtro
        run: |
          if [ "${{ github.event_name }}" = "push" ]; then
            echo "governanca=true" >> "$GITHUB_OUTPUT"
            echo "app=true" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          base="origin/${{ github.base_ref }}"
          mudou() { git diff --name-only "$base"...HEAD | grep -qE "$1" && echo true || echo false; }
          echo "governanca=$(mudou '^(governanca/|gov$|\.mcp\.json$)')" >> "$GITHUB_OUTPUT"
          echo "app=$(mudou '^app/')" >> "$GITHUB_OUTPUT"
  governanca:
    needs: mudancas
    if: needs.mudancas.outputs.governanca == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r governanca/requirements.txt
      - run: python -m pytest governanca/tests -q
      - run: python governanca/scripts/gov.py rebuild
      - run: python governanca/scripts/gov.py update
  app:
    needs: mudancas
    if: needs.mudancas.outputs.app == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: r-lib/actions/setup-r@v2
        with:
          use-public-rspm: true
      - run: Rscript -e 'install.packages("lintr")'
      - run: Rscript -e 'l <- lintr::lint_dir("app"); print(l); quit(status = as.integer(length(l) > 0))'
  estrutura:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r governanca/requirements.txt
      - run: |
          base=""
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            base="--base origin/${{ github.base_ref }}"
          fi
          python governanca/scripts/valida_estrutura.py $base
  resultado:
    needs: [mudancas, governanca, app, estrutura]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - run: |
          for r in "${{ needs.mudancas.result }}" "${{ needs.governanca.result }}" "${{ needs.app.result }}" "${{ needs.estrutura.result }}"; do
            case "$r" in failure|cancelled) exit 1;; esac
          done
```

- [ ] **Step 2: `.github/workflows/reviewers.yml`**

```yaml
name: reviewers
on:
  pull_request:
    types: [opened, reopened, ready_for_review]
permissions:
  pull-requests: write
jobs:
  convida:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - env:
          GH_TOKEN: ${{ github.token }}
          AUTOR: ${{ github.event.pull_request.user.login }}
          PR: ${{ github.event.pull_request.number }}
        run: |
          revisores=$(python3 -c "import json, os; m = json.load(open('governanca/integrantes.json')); print(','.join(u for u in m if u != os.environ['AUTOR']))")
          if [ -n "$revisores" ]; then
            gh pr edit "$PR" --repo "$GITHUB_REPOSITORY" --add-reviewer "$revisores"
          fi
```

- [ ] **Step 3: `.github/workflows/mach1-bot.yml`**

```yaml
name: mach1-bot
on:
  pull_request:
    types: [opened, synchronize, ready_for_review]
permissions:
  contents: read
  pull-requests: write
  issues: write
jobs:
  revisa:
    if: ${{ !github.event.pull_request.draft }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r governanca/requirements.txt
      - uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            REPO: ${{ github.repository }}
            PR: ${{ github.event.pull_request.number }}
            Leia governanca/mach1/PROMPT.md e execute o protocolo sobre esta PR.
          claude_args: |
            --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*),Bash(python governanca/scripts/gov.py rebuild),Bash(python governanca/scripts/gov.py contexto:*),Bash(python governanca/scripts/gov.py consulta:*),Bash(gh pr view:*),Bash(gh pr diff:*),Bash(gh pr comment:*)"
```

- [ ] **Step 4: `.github/workflows/pages.yml`**

```yaml
name: pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  publica:
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r governanca/requirements.txt
      - run: python governanca/scripts/gov.py update
      - uses: actions/upload-pages-artifact@v3
        with:
          path: governanca/site
      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 5: Validar sintaxe dos quatro YAML**

Run: `for f in .github/workflows/*.yml; do python3 -c "import yaml, sys; yaml.safe_load(open('$f'))" || echo "ERRO $f"; done`
(Se `yaml` não existir no python3 do sistema, usar `governanca/.venv/bin/pip install pyyaml --quiet` temporário ou `ruby -ryaml`.)
Expected: nenhuma linha `ERRO`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows
git commit -m "workflows: ci por escopo de paths, convite de revisores, mach1-bot e pages"
```

---

### Task 8: Org, repo, proteção, Pages e secret

**Files:** nenhum local além de limpeza de PDFs; tudo é estado remoto.

**Interfaces:**
- Consumes: workflows e docs das Tasks 6–7 já commitados.
- Produces: `ita-tra48/vertiportos-sp` público com branch `main`, ruleset ativo, Pages por workflow, 3 convites, secret `CLAUDE_CODE_OAUTH_TOKEN`.

- [ ] **Step 1: Tirar os PDFs do histórico antes do push público**

`docs/Plano de Disciplina TRA-48 2026.pdf` está rastreado e tem direitos autorais (MXG). O repo nunca foi pushado, então reescrever é seguro:

```bash
git rm --cached "docs/Plano de Disciplina TRA-48 2026.pdf"
git commit -m "remove pdf com direitos autorais do versionamento"
governanca/.venv/bin/pip install git-filter-repo --quiet
governanca/.venv/bin/python -m git_filter_repo --invert-paths --path "docs/Plano de Disciplina TRA-48 2026.pdf" --force
git log --all --name-only --format= | grep -i pdf || echo "historico limpo"
```

Expected: `historico limpo`. O arquivo continua no disco (agora ignorado). Nota: `git-filter-repo` remove o remote se existir — aqui ainda não existe.

- [ ] **Step 2: Consolidar a branch `main`**

```bash
git checkout master
git merge --no-ff infra-governanca -m "camada B: motor de governanca, contexto, worktree, mcp e workflows"
git branch -m master main
git log --oneline -3
```

- [ ] **Step 3: [USUÁRIO] Criar a org `ita-tra48`**

A API do GitHub não cria organizações com token de usuário. Gustavo cria em https://github.com/account/organizations/new?plan=free (nome `ita-tra48`, e-mail dele, "My personal account"). Alternativa: eu dirijo pelo Chrome com ele olhando.

- [ ] **Step 4: Criar o repo e push**

```bash
gh repo create ita-tra48/vertiportos-sp --public --description "TRA-48 (ITA 2/2026) — localizacao de vertiportos em Sao Paulo, com governanca computavel" 
git remote add origin https://github.com/ita-tra48/vertiportos-sp.git
git push -u origin main
gh repo view ita-tra48/vertiportos-sp --json defaultBranchRef -q .defaultBranchRef.name
```

Expected: `main`.

- [ ] **Step 5: Convidar os integrantes (write)**

```bash
for u in t27matheus oitalorabelo monteirocarloss021; do
  gh api "repos/ita-tra48/vertiportos-sp/collaborators/$u" -X PUT -f permission=push
done
gh api repos/ita-tra48/vertiportos-sp/invitations -q '.[].invitee.login'
```

Expected: os três logins listados como convites pendentes.

- [ ] **Step 6: Ruleset da `main`**

```bash
cat > /tmp/ruleset.json << 'JSON'
{
  "name": "main-protegida",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews_on_push": true,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false,
      "allowed_merge_methods": ["merge", "squash"]}},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false,
      "required_status_checks": [{"context": "resultado"}]}}
  ]
}
JSON
gh api repos/ita-tra48/vertiportos-sp/rulesets -X POST --input /tmp/ruleset.json
```

Expected: JSON de resposta com `"enforcement": "active"`. Sem lista de bypass: vale para todos, admins inclusive.

- [ ] **Step 7: Ativar o Pages por workflow**

```bash
gh api repos/ita-tra48/vertiportos-sp/pages -X POST -f build_type=workflow
gh run watch --repo ita-tra48/vertiportos-sp $(gh run list --repo ita-tra48/vertiportos-sp --workflow pages -L 1 --json databaseId -q '.[0].databaseId')
curl -sI https://ita-tra48.github.io/vertiportos-sp/ | head -1
```

Expected: `HTTP/2 200` (pode levar ~1 min após o primeiro deploy; se o run de pages do push inicial falhou porque o Pages ainda não existia, `gh run rerun`).

- [ ] **Step 8: [USUÁRIO] Gerar o token da assinatura Claude**

Gustavo roda `! claude setup-token` no prompt desta sessão e cola o token gerado. Em seguida:

```bash
gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo ita-tra48/vertiportos-sp
gh secret list --repo ita-tra48/vertiportos-sp
```

Expected: `CLAUDE_CODE_OAUTH_TOKEN` listado.

- [ ] **Step 9: Verificação do estado remoto**

```bash
gh api repos/ita-tra48/vertiportos-sp/rulesets -q '.[].name'
gh api repos/ita-tra48/vertiportos-sp/pages -q .build_type
```

Expected: `main-protegida` e `workflow`.

---

### Task 9: Dogfooding — registrar tudo no banco e publicar

**Files:**
- Modify: `governanca/dump.sql` (via `./gov`, nunca à mão)

**Interfaces:**
- Consumes: toda a CLI; site publicado pela Task 8.
- Produces: banco com metas, tarefas, decisões D1–D9, fonte OD, arquivos ligados e registro de IA; site refletindo tudo.

- [ ] **Step 1: Metas (propostas — o grupo valida)**

```bash
./gov meta "Recomendar onde e quantos vertiportos implantar em Sao Paulo, com valor defensavel" --desc "proposta inicial, validar com o grupo em 26/08"
./gov meta "Manter governanca computavel viva: toda decisao registrada enquanto acontece" --desc "proposta inicial, validar com o grupo em 26/08"
./gov meta "Entregar analise reprodutivel ponta a ponta a partir dos dados brutos" --desc "proposta inicial, validar com o grupo em 26/08"
```

Anotar os três ids impressos/consultados (`./gov consulta "SELECT id, titulo FROM meta"`) — abaixo chamados `MET_A` (recomendação), `MET_B` (governança), `MET_C` (reprodutibilidade).

- [ ] **Step 2: Decisões D1–D9 do spec, ligadas a `MET_B`**

```bash
./gov decisao "Org nova ita-tra48 com repo publico vertiportos-sp" --just "grupo de 4 nao deve ficar atrelado a conta pessoal; enunciado 6.2 exige repositorio publico" --alt "repo pessoal em gustavovfeitosa"
./gov decisao "Conta operadora gustavovfeitosa; gustavovidal-tiktok proibida no projeto" --just "separacao entre identidade academica e pessoal"
./gov decisao "Merge na main so por PR com 1 aprovacao obrigatoria e convite automatico aos 3 nao-autores" --just "revisao humana garantida sem travar a cadencia ate 23/09; todos veem tudo" --alt "3 aprovacoes obrigatorias: gargalo com um ausente"
./gov decisao "Bot de review em duas camadas: CI deterministico como gate e Mach1-Bot (Claude) como juizo" --just "regra mecanica nao le codigo; IA sozinha nao e gate objetivo" --alt "so lintr" --alt "so bot de IA"
./gov decisao "Mach1-Bot autentica com CLAUDE_CODE_OAUTH_TOKEN da assinatura do Gustavo" --just "sem custo por chamada; token revogavel guardado como secret" --alt "ANTHROPIC_API_KEY paga por uso"
./gov decisao "Uma tarefa = um branch = um worktree, criados por ./gov worktree" --just "4 pessoas e agentes de IA em paralelo sem disputa de checkout; dump append-only faz o merge dos registros ser concatenacao" --alt "branches soltos sem vinculo com o grafo"
./gov decisao "CI roda so os checks dos paths alterados; job resultado agrega e e o unico check obrigatorio" --just "PR de app nao paga pytest de governanca e vice-versa; protecao da main nao quebra com job pulado" --alt "rodar tudo sempre"
./gov decisao "Grafo e o indice de contexto da IA: ./gov contexto e MCP somente-leitura" --just "IA adquire contexto pela vizinhanca do no em vez de ler docs inteiro; escrita continua so pelo ./gov com autor e validacoes" --alt "IA le o repositorio inteiro a cada sessao"
./gov decisao "PDFs do professor fora do repo publico e do historico git" --just "material com direitos autorais da MXG; repo e publico" --alt "manter e restringir o repo a privado, contra o enunciado 6.2"
```

Depois, para cada `dec-...` impresso: `./gov liga DEC atende MET_B`.

- [ ] **Step 3: Fonte obrigatória**

```bash
./gov fonte "Pesquisa Origem-Destino 2017 do Metro de Sao Paulo" --origem "https://transparencia.metrosp.com.br/dataset/pesquisa-origem-e-destino" --formato "microdados + shapefile de zonas" --cobertura "RMSP, viagens por modo, motivo, renda e duracao" --limitacoes "retrato de 2017, pre-pandemia; viagens intermunicipais fora da RMSP nao cobertas"
```

- [ ] **Step 4: Tarefas dos marcos (26/08 e 02/09), ligadas a `MET_A`**

```bash
./gov tarefa "Definir recorte metodologico e revisar literatura inicial de localizacao" --resp "Gustavo Vidal" --prazo 2026-08-26
./gov tarefa "Preencher nomes de exibicao em governanca/integrantes.json" --resp "Gustavo Vidal" --prazo 2026-08-26
./gov tarefa "Estimar fatia de demanda capturavel da matriz OD" --resp "t27matheus" --prazo 2026-09-02
./gov tarefa "Montar conjunto de locais candidatos" --resp "oitalorabelo" --prazo 2026-09-02
./gov tarefa "Escrever formulacao matematica inicial" --resp "monteirocarloss021" --prazo 2026-09-02
```

Para cada `tar-...`: `./gov liga MET_A tem TAR` (as duas primeiras ligam em `MET_B`). Responsáveis dos colegas são proposta — anotar na tarefa 1 que a divisão se confirma em 26/08.

- [ ] **Step 5: Arquivos novos ligados às decisões**

```bash
./gov arquivo docs/ARQUITETURA.md --desc "ordem de arquitetura aplicada pelo CI e pelo Mach1-Bot"
./gov arquivo docs/PADRAO_PR.md --desc "padrao de descricao de PR para humanos e IA"
./gov arquivo governanca/mach1/PROMPT.md --desc "protocolo de revisao do Mach1-Bot"
./gov arquivo governanca/scripts/contexto.py --desc "vizinhanca do grafo como pacote de contexto"
./gov arquivo governanca/scripts/mcp_gov.py --desc "servidor MCP somente-leitura do banco"
./gov arquivo governanca/scripts/valida_estrutura.py --desc "regras mecanicas do ARQUITETURA no CI"
./gov arquivo .github/workflows/ci.yml --desc "checks por escopo de paths com job agregador"
```

Para cada `arq-...`: `./gov liga ARQ deriva DEC` na decisão correspondente (bot→D4/D5, worktree/contexto/mcp→D8, ci→D7, docs→D3/D4).

- [ ] **Step 6: [USUÁRIO] Registro de IA desta sessão**

A crítica humana é do Gustavo (a CLI recusa < 20 caracteres, e crítica de IA sobre si mesma não vale nada na arguição). Pedir a ele a crítica e rodar:

```bash
./gov ia --proposito "infraestrutura de governanca da camada B" --modelo "claude fable 5" --pedido "arquitetar github, bot de review, worktrees e grafo-como-contexto" --retorno "spec, plano e implementacao das tasks 1-8" --aceito parcial --critica "<TEXTO DO GUSTAVO>"
```

Depois: `./gov liga IA informa DEC` (na decisão D1) e o que mais ele apontar.

- [ ] **Step 7: Fechar pendência antiga e regenerar**

O plano anterior registrava o MCP como pendência; se existir (`./gov consulta "SELECT id, titulo FROM pendencia WHERE status = 'aberta'"`), fechar: `./gov fecha PEN --resolucao "mcp_gov.py entregue"`. Então:

```bash
./gov update
./gov auditoria
```

Expected: selo VERDE (zero órfãos, decisões ≥90% com meta, aceite integral < 100%). Se houver órfão, ligar o que faltou antes de seguir.

- [ ] **Step 8: Commit e push (site atualiza sozinho)**

```bash
git add governanca/dump.sql
git commit -m "governanca: metas, decisoes da infra publica, fonte OD, tarefas dos marcos e registro de ia"
git push
```

Verificar depois do run do Pages: `https://ita-tra48.github.io/vertiportos-sp/` mostra as metas, `tarefas.html` mostra responsáveis e prazos, `grafo.html` mostra os nós ligados.

---

### Task 10: PR de fumaça — o fluxo inteiro de ponta a ponta

**Files:** mudança trivial de exercício (uma linha no `README.md`).

**Interfaces:**
- Consumes: tudo das Tasks 1–9.
- Produces: prova de que reviewers, ci, Mach1-Bot e proteção funcionam; PR aberta como onboarding dos colegas.

- [ ] **Step 1: Tarefa + worktree**

```bash
./gov tarefa "Validar o fluxo de PR de ponta a ponta" --resp "Gustavo Vidal" --prazo 2026-08-25
./gov liga MET_B tem TAR_NOVA
./gov worktree TAR_NOVA --slug fluxo-pr
cd ../TRA-48_Projeto.worktrees/tar-*/
```

(No worktree, o `./gov` compartilha o mesmo `dump.sql`? NÃO — o worktree tem cópia própria do arquivo. Registrar sempre na raiz principal e fazer `git pull`/merge do branch trazer o dump: para esta PR, registrar a tarefa ANTES de criar o worktree, como acima, e commitar o dump na main? A main é protegida. Então: registrar a tarefa no worktree logo após criá-lo, para que o INSERT viaje na própria PR. Ordem correta: `./gov worktree` primeiro com a tarefa já existente vinda da Task 9 — está coberto: a tarefa foi registrada na raiz, e o dump com ela ainda não foi pushado? Foi, na Task 9 Step 8, antes desta task — então o branch novo já nasce com ela. Confirmar com `./gov status` dentro do worktree.)

- [ ] **Step 2: Mudança trivial + registros no worktree**

No worktree: acrescentar ao `README.md` a linha `Site do projeto: https://ita-tra48.github.io/vertiportos-sp/` e:

```bash
./gov arquivo README.md --desc "readme com link do site publico"
./gov update
git add -A
git commit -m "readme: link do site publico do projeto"
git push -u origin tarefa/tar-XXXXXX-fluxo-pr
```

- [ ] **Step 3: Abrir a PR conforme o padrão**

```bash
gh pr create --repo ita-tra48/vertiportos-sp --title "adiciona link do site publico ao readme" --body "$(cat <<'EOF'
## O que muda
Adiciona o link do site público ao README.

## Por quê
O professor acompanha o projeto pelo site; o README é a porta de entrada do repo.

## Registros
- tar-XXXXXX — validar o fluxo de PR de ponta a ponta
- arq-XXXXXX — readme com link do site publico

## Como verificar
Abrir o README na main após o merge e clicar no link.
EOF
)"
```

(Substituir os ids reais.)

- [ ] **Step 4: Verificar as quatro engrenagens**

```bash
gh pr view --json reviewRequests -q '.reviewRequests[].login'
gh pr checks --watch
gh pr view --comments | grep -A5 "Mach1-Bot"
```

Expected: os 3 colegas solicitados como reviewers; check `resultado` verde (jobs `governanca` e `app` pulados — a PR só toca README e dump); comentário começando com `**Mach1-Bot**`.

- [ ] **Step 5: Tentar merge sem aprovação (prova da proteção)**

Run: `gh pr merge --squash`
Expected: RECUSADO por falta de review. Deixar a PR aberta — é o exercício de onboarding: o primeiro colega que entrar aprova e mergeia.

- [ ] **Step 6: Fechar o registro**

Na raiz principal: `./gov fecha TAR_NOVA --resolucao "fluxo validado: reviewers, ci por escopo, mach1-bot e protecao da main"`, `./gov update`, commit do dump e push via a própria PR aberta (adicionar ao branch) ou nova PR curta. Comunicar ao Gustavo o estado final: URLs do repo, do site e da PR aberta.

---

## Self-Review

**Spec coverage:** D1/D2 → Tasks 1, 8; D3/D4 → Tasks 7, 8 (ruleset + reviewers + mach1); D5/D6 → Tasks 7, 8 (secret); D7 → Task 3; D8 → Task 7 (ci por paths); D9 → Tasks 2, 4 (contexto + MCP + `.mcp.json`); §4 docs → Task 6; §5 CI → Tasks 5, 7; §7 documentos → Task 6; §10 Pages → Tasks 7, 8; §11 dogfooding → Task 9. Lacuna consciente: nomes de exibição dos 3 colegas (tarefa registrada na Task 9 Step 4).

**Riscos sinalizados ao executor:**
- `anthropics/claude-code-action@v1`: conferir na execução os nomes exatos dos inputs (`claude_code_oauth_token`, `prompt`, `claude_args`) contra o README da action; ajustar se a versão mudou.
- Ruleset via API: se `allowed_merge_methods` for rejeitado pela API, remover o campo (default permite todos).
- Task 10 Step 1: o dump viaja pelo git; registrar na raiz e pushar antes de criar worktree, como sequenciado.
- `git-filter-repo` reescreve hashes: os commits citados em `RETOMADA.md`/docs não são citados por hash em lugar nenhum — verificado, seguro.
