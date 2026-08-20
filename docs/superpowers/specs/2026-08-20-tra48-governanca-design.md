# Camada B — Governança Computável do Projeto B1 (TRA-48)

**Status:** aprovado (sessão 19-20/08/2026; documento reconstruído em 20/08/2026 após perda do original)
**Enunciado de origem:** `~/Documents/ITA/TRA-48/Projeto_TRA48.pdf`, cap. 5 e 8
**Repo:** `~/Documents/ITA/TRA-48_Projeto`

## 1. Problema que este sistema resolve

O Projeto B1 é avaliado em duas camadas. A camada A é o modelo de Pesquisa
Operacional (localização de vertiportos em São Paulo). A camada B, que vale
**25% da nota do projeto**, é a governança do próprio trabalho: metas, tarefas,
pendências, decisões, fontes, arquivos, referências, experimentos e interações
com IA, registrados enquanto o trabalho acontece, ligados em um grafo,
auditados por métricas e publicados em site gerado do banco.

A regra dura do enunciado (§5.1):

> O que não estiver no banco, não aconteceu.

O enunciado (§5.2) diz que cada grupo **recebe um repositório-modelo já
funcionando**. Até 20/08/2026 ele não foi distribuído. Este spec define a infra
que o grupo constrói no lugar dele. Se o repo-modelo chegar depois, os registros
migram por script (o log de eventos é portável — ver §4.3).

## 2. Requisitos derivados do enunciado

| # | Requisito | Fonte |
|---|---|---|
| R1 | Nove entidades registráveis: metas, tarefas, pendências, decisões, fontes, arquivos, referências, experimentos, interações com IA | §5.3 |
| R2 | Grafo executivo: entidades são nós, relações são arestas tipadas; nó órfão é defeito detectado pela auditoria e exibido no site | §5.4 |
| R3 | Interação com IA **inválida sem o campo crítica humana** | §5.6.2 |
| R4 | Taxa de aceite integral exibida no site | §5.6.3 |
| R5 | Auditoria automática: rastreabilidade, cadência, higiene, postura crítica | §5.7 |
| R6 | Site com 8 seções, gerado a cada push, espelho fiel do banco | §5.5 |
| R7 | Fluxo `./gov <cmd>` → banco → `./gov update` → `git push` → site | §5.2 |
| R8 | Superfície de comandos do §5.8 preservada literalmente | §5.8 |
| R9 | Leitura do banco pelo assistente de IA via MCP; **escrita sempre pelo `./gov`** | §5.8 |
| R10 | Contribuição individual visível: cada integrante autor de registros e de commits | §7.3 |
| R11 | Reprodutibilidade ponta a ponta a partir dos dados brutos | §6.2 |
| R12 | Linguagem padrão é R; outra linguagem exige justificativa registrada | §4.6 |

## 3. Arquitetura aprovada

```
TRA-48_Projeto/
|-- gov                        # wrapper shell -> governanca/.venv/bin/python
|-- governanca/
|   |-- .venv/                 # NAO versionado; duckdb + pytest
|   |-- requirements.txt
|   |-- projeto.duckdb         # NAO versionado (ver 4.2)
|   |-- dump.sql               # VERSIONADO, append-only: a fonte de verdade em git
|   |-- schemas/schema.sql     # DDL: tabela evento + views derivadas
|   |-- scripts/
|   |   |-- gov.py             # CLI: parsing, validacao, escrita de eventos
|   |   |-- banco.py           # conexao, rebuild a partir do dump, append de evento
|   |   |-- auditoria.py       # metricas do 5.7
|   |   |-- grafo.py           # layout determinístico -> SVG
|   |   |-- site.py            # gerador das 8 paginas
|   |   `-- mcp_gov.py         # servidor MCP somente-leitura
|   `-- site/                  # saida gerada; NAO versionada (ver 4.4)
|-- app/                       # camada A, 100% em R
|   |-- 01-carrega.R ... 05-analises.R
|   `-- R/gov.R                # leitura do banco pelo R
|-- dados/{bruto,tratado}/
|-- docs/                      # documentos-fonte (PDFs, specs, plans) — NAO e o site
|-- relatorio/ apresentacao/
`-- .github/workflows/pages.yml
```

### 3.1 Motor em Python, projeto em R

O motor de governança é Python + DuckDB; a camada A é 100% R. Justificativa:
DuckDB e o servidor MCP têm ferramental maduro em Python, e o motor é
infraestrutura, não análise — o enunciado exige R para *o projeto* (§4.6), e a
exigência é atendida integralmente pelo `app/`. Esta escolha é registrada como
decisão no próprio banco, conforme §4.6 exige.

### 3.2 O log de eventos é a única tabela escrita

Todas as nove entidades e todas as arestas são gravadas como linhas em uma
única tabela append-only `evento`:

| coluna | tipo | papel |
|---|---|---|
| `evento_id` | TEXT PK | `evt-` + 12 chars base32 de `os.urandom` |
| `ts` | TIMESTAMP | instante do registro (UTC) |
| `autor` | TEXT | `git config user.name`, ou `$GOV_AUTOR` |
| `tipo` | TEXT | uma das 9 entidades, ou `aresta` |
| `entidade_id` | TEXT | id do nó a que o evento se refere |
| `payload` | JSON | campos da entidade |

As entidades são **views** sobre `evento` (último payload por `entidade_id`,
mesclado com o `ts`/`autor` de criação). Consequências:

- `dump.sql` é uma sequência de `INSERT INTO evento`, então merge de git entre
  4 pessoas é concatenação — conflito só na cauda, nunca no meio;
- edição não destrói história: `patch` e `fecha` gravam um novo evento com o
  payload completo já mesclado, sob o mesmo `tipo` e `entidade_id`; a view lê o
  evento mais recente e o original permanece auditável, o que sustenta "banco vivo, não preenchido retroativamente" (§8.2);
- "preenchido em bloco na semana da entrega" (§8.4) é detectável pela própria
  distribuição de `ts` — é isso que a métrica de cadência lê.

### 3.3 Identificadores

`<prefixo>-<6 chars base32>`, ex. `dec-0a3f2b`, `exp-7k1m9d`. Prefixos:
`met`, `tar`, `pen`, `dec`, `fon`, `arq`, `ref`, `exp`, `ia`.

Sem contador sequencial: 4 pessoas registrando em branches paralelos com
contador colidiriam no merge. A CLI aceita prefixo único como referência, no
estilo do git (`./gov liga dec-0a3 usa fon-4c2`).

## 4. Desvios deliberados do organograma do professor

Ambos são desvios do §5.2 e ambos são registrados como decisão no banco, com
justificativa e alternativa descartada.

### 4.1 O que é versionado

O organograma lista `projeto.duckdb` dentro de `governanca/`. Um binário DuckDB
versionado com 4 pessoas escrevendo em paralelo dá conflito irreconciliável a
cada push — git não faz merge de binário, e o "vencedor" apaga registros do
outro silenciosamente. Isso destrói justamente a garantia de que o banco é a
fonte de verdade.

### 4.2 Decisão

`projeto.duckdb` **não é versionado** (entra no `.gitignore`). O artefato
versionado é `governanca/dump.sql`, append-only e legível. `./gov` reconstrói o
banco a partir dele quando ele não existe ou está desatualizado. O enunciado já
descreve `dump.sql` como "historia legivel, versionada no git" — este desvio só
remove a redundância conflitante, mantendo intacta a semântica de fonte de
verdade.

**Alternativa descartada:** versionar o `.duckdb` e serializar o trabalho (uma
pessoa registra por vez). Descartada porque inviabiliza cadência paralela, que
é métrica avaliada (§5.7).

### 4.3 O site gerado não é versionado, e não mora em `docs/`

O organograma põe a saída publicada em `docs/`. Duas objeções: (a) `docs/` neste
repo já guarda os documentos-fonte (enunciado, plano de disciplina, specs), e
misturar fonte com artefato gerado torna o `git status` ilegível; (b) HTML
gerado versionado por 4 pessoas conflita a cada `./gov update` sem trazer
informação nova — ele é função pura do banco.

**Decisão:** o site é gerado em `governanca/site/` (gitignored) e publicado pelo
GitHub Pages via *artifact* do Actions, não por branch/pasta. O CI reconstrói o
banco do `dump.sql` e gera o site do zero a cada push, o que torna a
propriedade "o site é espelho fiel do banco" (§5.2) **verificável por
construção** em vez de dependente de disciplina humana.

**Alternativa descartada:** `docs/` como pasta publicada, com `./gov update`
obrigatório antes de cada commit. Descartada porque um commit sem `update`
publica site defasado — exatamente a falha que o enunciado quer evitar.

## 5. Superfície da CLI

Preservada literalmente do §5.8, mais o mínimo necessário para operar o grafo:

```
./gov meta        "titulo" [--desc ...]
./gov tarefa      "titulo" --resp NOME [--prazo YYYY-MM-DD] [--meta ID]
./gov pendencia   "titulo" [--bloqueia ID]
./gov decisao     "titulo" --just "..." [--alt "..."]... [--meta ID]
./gov fonte       "nome" --origem URL [--formato ...] [--cobertura ...] --limitacoes "..."
./gov arquivo     CAMINHO [--desc ...] [--decisao ID]
./gov referencia  "citacao" [--url ...] [--doi ...]
./gov experimento --variante NOME [--p chave=valor]... [--obj N] [--gap N] [--tempo N] [--hipotese ...] [--conclusao ...]
./gov ia          --proposito NOME --aceito {integral,parcial,descarte} --critica "..." [--modelo ...] [--pedido ...] [--retorno ...]
./gov liga        ORIGEM RELACAO DESTINO
./gov fecha       ID [--resolucao ...]
./gov patch       ID campo=valor...
./gov status
./gov auditoria
./gov consulta    "SELECT ..."      # somente leitura
./gov update                        # dump + grafo + auditoria + site
./gov rebuild                       # banco a partir do dump.sql
```

### 5.1 Validações que a CLI recusa

Estas não são conveniências; são a codificação das regras do enunciado.

1. `ia` sem `--critica` **não grava** (§5.6.2), e `--critica` com menos de 20
   caracteres também não — "ok" não é crítica.
2. `decisao` sem `--just` não grava (§5.3 exige justificativa).
3. `fonte` sem `--limitacoes` não grava (§3.2, e §8.2 premia reconhecer a
   limitação do próprio dado).
4. `tarefa` sem `--resp` não grava (§5.7, higiene).
5. `consulta` rejeita qualquer statement que não seja `SELECT`/`WITH`.

### 5.2 Autoria

`autor` vem de `git config user.name`, com `$GOV_AUTOR` como override. Se
nenhum dos dois existir, a CLI **falha** em vez de gravar autor vazio: R10 exige
contribuição individual atribuível. (No repo atual `git config user.name` está
vazio — configurar é passo do plano.)

## 6. Relações do grafo

Vocabulário fechado, validado pela CLI:

| relação | de → para | serve para responder |
|---|---|---|
| `tem` | meta → tarefa | o que está sendo feito por qual objetivo |
| `atende` | decisao → meta | decisão vinculada a meta (métrica de rastreabilidade) |
| `usa` | decisao → fonte \| referencia | por que o parâmetro é este, com que base |
| `produz` | arquivo → arquivo | qual script gerou qual mapa |
| `justifica` | experimento → decisao | qual rodada sustenta a escolha |
| `apoia` | experimento → conclusao(arquivo) | conclusão com experimento que a sustenta |
| `deriva` | arquivo → decisao | arquivo vinculado a decisão (rastreabilidade) |
| `bloqueia` | pendencia → tarefa \| meta | o que trava o projeto |
| `informa` | ia → decisao \| arquivo | o que a IA tocou no produto final |

## 7. Auditoria (§5.7)

| grupo | métrica | cálculo |
|---|---|---|
| Rastreabilidade | % arquivos com decisão | arquivos com aresta `deriva` / total |
| | % decisões com meta | decisões com aresta `atende` / total |
| | nós órfãos | nós sem nenhuma aresta, listados por id |
| Cadência | registros/semana | `count(evento)` agrupado por `date_trunc('week', ts)` |
| | commits/semana | `git log --format=%aI` lido pelo motor |
| | decisões/semana | idem, filtrado por tipo |
| Higiene | pendências velhas | abertas há > 7 dias |
| | tarefas incompletas | sem `resp` ou sem `prazo` |
| Postura crítica | distribuição de aceite | `ia` agrupado por `aceito`, com % de integral |

O **selo de auditoria** exibido no site (§5.5.1) é verde só se: zero nós órfãos,
rastreabilidade de decisões ≥ 90%, nenhuma pendência aberta > 14 dias, e taxa de
aceite integral < 100%.

## 8. Site (§5.5)

Oito páginas, geradas por `site.py`, HTML estático sem CDN e sem dependência de
rede (o site é avaliado ao vivo na arguição; falha de CDN não pode derrubá-lo):

1. `index.html` — Estado: metas, próximas ações, últimas decisões, selo
2. `grafo.html` — grafo executivo em SVG gerado, nós clicáveis
3. `trilha.html` — linha do tempo de eventos com justificativas
4. `tarefas.html` — quadro de tarefas e pendências com prazos
5. `ia.html` — registro completo de IA, taxa de aceite, críticas humanas
6. `experimentos.html` — tabela de rodadas: parâmetros, obj, gap, tempo
7. `resultados.html` — mapas, fronteira de implantação, sensibilidade (camada A)
8. `reprodutibilidade.html` — como rodar do zero

O grafo é SVG com layout determinístico calculado em Python (faixas por tipo de
entidade, ordenação estável por id), com `<a>` em cada nó apontando para a
âncora do registro, mais ~40 linhas de JS inline para pan/zoom. Determinismo
importa: dois `./gov update` sobre o mesmo banco produzem byte-a-byte o mesmo
SVG, então diff de site é sinal, não ruído.

## 9. MCP somente-leitura (R9)

`mcp_gov.py` expõe ferramentas `consultar(sql)`, `no(id)`, `vizinhos(id)`,
`auditoria()`. Nenhuma ferramenta de escrita: a escrita passa pelo `./gov` para
que toda gravação tenha autor humano e passe pelas validações da §5.1.

## 10. Fora de escopo

- A camada A em si (formulação, dados OD, solver) — este spec é só a infra que
  a registra. O `app/` entra aqui apenas como esqueleto e como leitor do banco.
- Migração do repositório-modelo do professor, caso chegue: o log de eventos é
  exportável, mas o script de migração só se escreve contra o schema real dele.

## 11. Dependências

`governanca/requirements.txt`: `duckdb`, `pytest`. Nada mais — stdlib para
templates, HTML, SVG e JSON. Menos dependência é mais reprodutibilidade (R11),
e o grupo tem 4 máquinas para manter iguais.
