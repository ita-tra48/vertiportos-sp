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
    if not nome:
        raise ValueError("ferramenta desconhecida")
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
        params = msg.get("params") or {}
        nome = params.get("name")
        args = params.get("arguments") or {}
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
        try:
            msg = json.loads(linha)
        except json.JSONDecodeError:
            resposta = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": "json invalido"}}
            sys.stdout.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue
        resposta = despacha(msg)
        if resposta is not None:
            sys.stdout.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
