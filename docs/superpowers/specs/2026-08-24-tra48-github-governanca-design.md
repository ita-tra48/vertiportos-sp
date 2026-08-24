# Camada B pública — GitHub, Mach1-Bot, worktrees e grafo-como-contexto (TRA-48)

**Status:** aprovado (sessão 24/08/2026)
**Complementa:** `2026-08-20-tra48-governanca-design.md` (motor local, já construído)
**Enunciado:** `Enunciado/Projeto_TRA48.pdf`, cap. 5–8

## 1. Problema

O motor da camada B (gov.py + DuckDB + site de 8 páginas + auditoria + grafo)
existe e passa nos testes, mas é invisível: não há repo no GitHub, não há site
publicado, não há processo de PR. O professor acompanha o projeto pelo GitHub
e pelo site (§5.5, §7.2), e o marco de 19/08 ("repositório clonado; site no ar")
está vencido. Este spec define a parte pública: org, repo, Pages, regras de PR,
bot de review, trabalho paralelo por worktrees e o grafo como índice de
contexto para IA.

## 2. Decisões (todas registráveis via `./gov decisao` na implementação)

| # | Decisão | Alternativa descartada |
|---|---|---|
| D1 | Org nova `ita-tra48`, repo público `vertiportos-sp` | repo pessoal em `gustavovfeitosa` — atrela o grupo a uma conta |
| D2 | Conta operadora: `gustavovfeitosa`; `gustavovidal-tiktok` proibida | — |
| D3 | Merge na `main` só por PR com **1 aprovação** obrigatória | 3 aprovações (todos) — gargalo com prazo 23/09 |
| D4 | Review solicitado automaticamente aos 3 não-autores em toda PR | CODEOWNERS com team — menos controle sobre quem é chamado |
| D5 | Bot de review em 2 camadas: CI determinístico (gate) + **Mach1-Bot** (Claude, juízo) | só lint (não lê código) ou só IA (sem gate objetivo) |
| D6 | Credencial do Mach1-Bot: `CLAUDE_CODE_OAUTH_TOKEN` da assinatura do Gustavo | `ANTHROPIC_API_KEY` — custo por chamada |
| D7 | 1 tarefa = 1 branch = 1 worktree, via `./gov worktree` | branches soltos sem vínculo com o grafo |
| D8 | CI roda só os checks dos paths alterados; um job agregador é o único check obrigatório | rodar tudo sempre — lento e ruidoso |
| D9 | Grafo é o índice de contexto da IA: `./gov contexto` + MCP somente-leitura | IA lê docs/ inteiro a cada sessão |

## 3. Org, repo e pessoas

- `gh` ativado em `gustavovfeitosa`; `git config user.name/email` configurados
  no clone local (a CLI exige autor).
- Org `ita-tra48`; repo público `ita-tra48/vertiportos-sp` recebe push do
  histórico local existente.
- Convites com **write**: `t27matheus`, `oitalorabelo`, `monteirocarloss021`.
  Gustavo é owner.
- `governanca/integrantes.json` mapeia username GitHub → nome. É a única fonte
  da lista de membros: o workflow de reviewers lê dele, o `--resp` das tarefas
  usa os mesmos nomes.
- Site: `https://ita-tra48.github.io/vertiportos-sp`.

## 4. Regras de PR

Proteção da `main` (ruleset, vale para admins):

- merge só por PR; **1 approval**; aprovações antigas dispensadas a cada commit
  novo; check obrigatório: `ci / resultado`; force-push e delete bloqueados.

Automação e padrão:

- `.github/workflows/reviewers.yml` — em `pull_request: opened/ready_for_review`,
  solicita review de todos os integrantes de `integrantes.json` exceto o autor.
- `.github/pull_request_template.md` — seções fixas: **O que muda / Por quê /
  Registros** (ids `dec-`/`tar-`/`exp-` obrigatórios) **/ Como verificar**.
- `docs/PADRAO_PR.md` — instrui quem escreve a descrição (humano ou IA): tom,
  formato das seções, obrigação de citar os ids de registro, proibição de
  descrição vazia. O CLAUDE.md do repo aponta para ele.

## 5. CI determinístico (`.github/workflows/ci.yml`)

Jobs condicionados por path (via filtro de paths alterados na PR):

| job | roda quando muda | faz |
|---|---|---|
| `governanca` | `governanca/**`, `gov` | pytest; `./gov rebuild` do dump.sql; gera site do zero |
| `app` | `app/**` | `lintr` (estilo tidyverse) |
| `estrutura` | sempre | script que valida as regras mecânicas do ARQUITETURA.md: scripts de `app/` numerados, nenhum arquivo novo/alterado em `dados/bruto/`, figuras de `relatorio/figuras/` com script gerador ligado no grafo, layout de pastas |
| `resultado` | sempre (needs: todos) | agrega; é o único check obrigatório na proteção — verde se cada job pulado ou verde |

## 6. Mach1-Bot (`.github/workflows/mach1-bot.yml`)

- `anthropics/claude-code-action@v1`, secret `CLAUDE_CODE_OAUTH_TOKEN`
  (gerado por `claude setup-token`, passo interativo do Gustavo).
- Comenta na PR assinando **Mach1-Bot**. Prompt em `governanca/mach1/PROMPT.md`:
  1. extrai os ids de registro da descrição da PR;
  2. roda `./gov contexto <id>` para cada um e lê **só essa vizinhança do
     grafo**, não o repo;
  3. revisa o diff contra `docs/ARQUITETURA.md` (incongruências de sintaxe,
     estrutura, distribuição de arquivos) e contra a coerência com os registros
     citados;
  4. não aprova nem bloqueia — comenta; o gate é o CI e o review humano.
- PR sem ids de registro na descrição: Mach1-Bot comenta apontando a violação
  do PADRAO_PR.md (a regra dura "o que não está no banco não aconteceu" chega
  ao processo de PR por aqui).

## 7. Documentos de ordem

- `docs/ARQUITETURA.md` — a ordem de arquitetura de código que o Mach1-Bot e o
  job `estrutura` aplicam: layout de pastas (do spec anterior §3), R estilo
  tidyverse com um script por etapa numerado, motor Python restrito a
  `governanca/scripts/`, `dados/bruto/` somente-leitura, figura só via script,
  comentários de código próximos de zero (contexto vai na PR), nomes em
  português sem acento em identificadores.
- `docs/PADRAO_PR.md` — ver §4.

## 8. Worktrees para trabalho paralelo

Novo comando:

```
./gov worktree TAR-ID [--slug texto]
```

- cria branch `tarefa/tar-xxxxxx[-slug]` a partir da `main` atualizada;
- monta worktree em `../vertiportos-sp.worktrees/tar-xxxxxx/`;
- grava no banco a ligação tarefa → branch (payload da tarefa ganha
  `branch=...`; evento novo, história preservada);
- se o worktree já existe, apenas informa o caminho (idempotente).

Racional: 4 pessoas + agentes de IA em paralelo sem disputa de checkout; o
`dump.sql` append-only já garante merge por concatenação. O quadro de tarefas
do site passa a exibir o branch de cada tarefa em andamento.

## 9. Grafo como índice de contexto para IA

Novo comando:

```
./gov contexto ID [--raio N]      # N=1 default
```

- BFS na vizinhança do nó até raio N sobre as arestas tipadas;
- emite Markdown (default) ou JSON (`--json`): registros completos da
  vizinhança + caminhos dos arquivos ligados;
- é a resposta computável a "o que tem a ver com esta meta/tarefa/pendência".

MCP somente-leitura (`governanca/scripts/mcp_gov.py`, cumpre o R9 postergado):

- ferramentas: `consultar(sql)` (SELECT/WITH apenas), `no(id)`, `vizinhos(id)`,
  `contexto(id, raio)`, `auditoria()`;
- `.mcp.json` versionado na raiz conecta o Claude de todos os integrantes;
- escrita continua exclusivamente pelo `./gov` (validações e autor humano).

O CLAUDE.md do repo passa a instruir: contexto de trabalho se adquire por
`./gov contexto`/MCP a partir dos ids; ler `docs/` inteiro é o último recurso.

## 10. GitHub Pages

`.github/workflows/pages.yml` — a cada push na `main`: instala deps, reconstrói
o banco do `dump.sql`, roda `./gov update`, publica `governanca/site/` como
artifact do Pages. Site não versionado, espelho fiel por construção (desvio já
aprovado no spec anterior §4.3).

## 11. Registro no banco (dogfooding)

Antes do primeiro push: D1–D9 registradas via `./gov decisao` com justificativa
e alternativa; arquivos novos ligados às decisões (`deriva`); 2–3 metas
propostas a partir do enunciado + primeiras tarefas com `--resp` e prazo dos
marcos (26/08, 02/09) — metas e atribuições a validar com o grupo, marcadas
como tal na descrição.

## 12. Fora de escopo

- Camada A (formulação, dados OD, solver).
- Migração para o repo-modelo do professor, se chegar.
- Qualquer ferramenta de escrita no MCP.

## 13. Riscos aceitos

- Mach1-Bot roda com a assinatura Claude do Gustavo em repo público (D6):
  aceito; o token é secret e revogável.
- 1 approval permite merge com 3 revisores ainda pendentes (D3): aceito em
  favor da cadência; o convite a todos preserva a visibilidade.
- `claude setup-token` e criação de org são passos interativos que o plano
  marca explicitamente como do usuário.
