# TRA-48 — Projeto

Estrutura:

```
dados/bruto      # dados originais, somente-leitura
dados/tratado    # saídas dos scripts de preparação
app/             # camada A em R: scripts numerados + app/R/ auxiliares
relatorio/       # Quarto/RMarkdown + figuras
apresentacao/    # slides
docs/            # plano de disciplina, enunciados, referências
```

Ver `CLAUDE.md` para prazos, stack e convenções.

## Como rodar

```
python3 -m venv governanca/.venv
governanca/.venv/bin/pip install -r governanca/requirements.txt
./gov rebuild
./gov status
```

Depois disso o `.mcp.json` já conecta o Claude Code ao servidor MCP `gov`
automaticamente.

Site do projeto: https://ita-tra48.github.io/vertiportos-sp/
