# TRA-48 — Infraestrutura de governança computável (camada B)

Data: 2026-08-20
Status: aprovado
Escopo desta spec: **somente a infraestrutura**. O problema de localização de
vertiportos (camada A) não é tratado aqui.

## 1. Contexto e restrições

O Projeto B1 de TRA-48 tem duas camadas avaliadas de forma independente:

- **Camada A (substantiva, 55%)** — modelar e resolver um problema de programação
  matemática para localizar vertiportos em São Paulo (AAM/UAM).
- **Camada B (metodológica, 25% governança + parte dos 20% de comunicação)** — como
  o grupo conduziu, registrou e auditou o próprio trabalho com apoio de IA,
  publicado e verificável.

Regra fundamental do enunciado, que governa todo este desenho:

> O que não estiver no banco, não aconteceu.

Restrições herdadas do enunciado (`~/Documents/ITA/TRA-48/Projeto_TRA48.pdf`):

| # | Restrição | Origem |
|---|---|---|
| R1 | Banco DuckDB é a fonte de verdade; Markdown e site são derivados | §5.2 |
| R2 | 9 classes de entidade obrigatórias no registro | §5.3 |
| R3 | Entidades são nós de um grafo com relações nomeadas | §5.4 |
| R4 | Nó órfão é defeito, detectado pela auditoria e exibido no site | §5.4 |
| R5 | Site no GitHub Pages com 8 seções específicas | §5.5 |
| R6 | Registro de IA exige campo de crítica humana; sem crítica não se registra | §5.6.2 |
| R7 | Taxa de aceite integral é métrica pública; ~100% é sinal de ausência de revisão | §5.6.3 |
| R8 | Cada integrante defende qualquer linha do modelo, do código e do relatório | §5.6.4 |
| R9 | Auditoria publica rastreabilidade, cadência, higiene e postura crítica | §5.7 |
| R10 | Escrita sempre pelo `./gov`; leitura pelo assistente via MCP | §5.8 |
| R11 | Contribuição individual visível em registros do banco e commits do repo | §7.3 |
| R12 | Banco preenchido em bloco na semana da entrega compromete a nota | §8.4 |
| R13 | Projeto reprodutível do zero, a partir dos dados brutos, por terceiros | §6.2 |

### 1.1 Divergência conhecida do enunciado

§5.2 afirma que cada grupo **recebe** um repositório-modelo funcionando, e o marco
de 19/08 diz "repositório clonado". Esse repositório não foi disponibilizado até
20/08. Decisão do grupo: construir a infraestrutura própria agora, para não perder
cadência (R12 pune justamente a perda de cadência), e migrar os registros por
script caso o modelo do professor chegue. A migração é viável porque as 9 entidades
e as relações são ditadas pelo enunciado; o que pode diferir é a implementação, não
o conteúdo. `governanca/scripts/migrar.py` é previsto como ponto de extensão.

### 1.2 Correção deliberada ao organograma

O organograma de §5.2 posiciona `projeto.duckdb` como arquivo do repositório. Com 4
pessoas commitando, um binário DuckDB produz conflito de merge irresolvível: Git não
sabe fundir dois bancos. Este desenho mantém o organograma, mas invertendo o que é
versionado:

- `governanca/dump.sql` — **versionado**, append-only, é o artefato de verdade em Git.
- `governanca/projeto.duckdb` — **ignorado pelo Git**, reconstruído do dump por `./gov`.

Isso é fiel à intenção do enunciado, que já chama o dump de "história legível,
versionada no git", e torna o merge de dois registros simultâneos um merge de texto.
O merge driver `union` em `.gitattributes` resolve o caso comum sem intervenção.

## 2. Papéis e fronteiras

Papel é **dono da revisão**, não silo. R8 exige que cada integrante defenda qualquer
linha; portanto o dono responde pela frente e é CODEOWNER dela, mas o revisor
obrigatório de cada PR é sempre de outra frente, em round-robin. Ninguém aprova o
próprio PR.

| Papel | Frente | CODEOWNER |
|---|---|---|
| Dados & Demanda | fontes, zonas OD, agregação, demanda capturável | `app/dados/`, `app/R/prep-*.R` |
| Modelagem | formulação, variáveis, restrições, tratabilidade, solver | `app/R/modelo/` |
| Experimentos & Análise | rodadas, relaxação linear, dual, sensibilidade, fronteira | `app/R/exp/`, `app/resultados/` |
| Governança & Publicação | motor `gov`, auditoria, site, CI, integração do relatório | `governanca/`, `.github/`, `docs/` |

Cada capítulo do relatório é arquivo separado com CODEOWNER individual, satisfazendo
R11 no nível de arquivo.

## 3. A ponte Git ↔ banco

R1 e R12 só são efetivos se for mecanicamente impossível mergear código sem registro.
Quatro mecanismos, em camadas:

1. **Corpo do PR declara os registros** que ele materializa: `Registros: D-014, E-007, IA-031`.
   Template de PR obriga o campo.
2. **CI valida os IDs** contra `dump.sql` e falha se algum não existir. PR que toca
   `app/R/modelo/` sem citar decisão registrada não passa.
3. **`./gov` grava o `commit_sha`** em cada registro, fechando o vínculo nos dois
   sentidos: o experimento aponta para o código exato que o produziu (R13).
4. **Auditoria acusa órfãos** — arquivo sem decisão, conclusão sem experimento — como
   warning no site (R4).

## 4. Esquema do banco

Todo nó tem: `id` legível (`D-014`), `autor`, `criado_em`, `commit_sha`, `titulo`.

| Tabela | Prefixo | Campos próprios |
|---|---|---|
| `meta` | `M-` | `descricao` |
| `tarefa` | `T-` | `responsavel`, `prazo`, `status` |
| `pendencia` | `P-` | `depende_de`, `aberta_em`, `fechada_em` |
| `decisao` | `D-` | `justificativa`, `alternativas_descartadas`, `status` |
| `fonte` | `F-` | `origem`, `formato`, `cobertura`, `limitacoes`, `url` |
| `arquivo` | `A-` | `caminho`, `tipo`, `descricao` |
| `referencia` | `R-` | `citacao`, `doi_url`, `tipo` |
| `experimento` | `E-` | `hipotese`, `parametros_json`, `obj`, `gap`, `tempo_s`, `conclusao` |
| `ia` | `IA-` | `proposito`, `pedido`, `retorno_resumo`, `aceite`, `critica_humana`, `transcricao_path` |

`aresta(origem_id, relacao, destino_id, criado_em, autor)`.

Vocabulário fechado de relações: `tem_tarefa`, `usou_fonte`, `produziu`, `apoia`,
`decorre_de`, `cita`, `bloqueia`, `implementa`. Fechado por escolha: é o que permite
à auditoria decidir se um nó é órfão sem heurística.

### 4.1 Constraints que carregam regra de avaliação

- `ia.critica_humana` — `NOT NULL`, mínimo de 40 caracteres. Implementa R6 como
  constraint, não como convenção.
- `ia.aceite` — `CHECK IN ('integral','parcial','descarte')`. Alimenta R7.
- `tarefa.responsavel` e `tarefa.prazo` — `NOT NULL`. Alimenta a métrica de higiene (R9).
- `decisao.alternativas_descartadas` — `NOT NULL`. O enunciado exige alternativa
  descartada em toda decisão (§5.3).

## 5. CLI `./gov`

Comandos idênticos ao guia rápido de §5.8, mais três:

    ./gov meta        "..."
    ./gov tarefa      "..." --resp NOME --prazo AAAA-MM-DD
    ./gov decisao     "..." --just "..." --alt "..."
    ./gov pendencia   "..." --depende-de "..."
    ./gov fonte       "..." --origem ... --formato ... --cobertura ... --limitacoes ...
    ./gov ia          --proposito ... --aceito integral|parcial|descarte --critica "..."
    ./gov experimento --hipotese ... --p chave=valor --obj N --gap N --tempo N
    ./gov link        D-014 usou_fonte F-003
    ./gov status
    ./gov auditoria
    ./gov update

`update` regenera, em ordem: `dump.sql`, grafo, auditoria, painel e as páginas de
`docs/`. É idempotente: rodar duas vezes produz o mesmo resultado, o que o torna
seguro dentro do CI.

## 6. MCP só-leitura

Servidor local (`governanca/scripts/mcp_server.py`) que expõe consulta SQL ao banco
para o assistente, sem qualquer caminho de escrita. Implementa R10 literalmente. A
assimetria é intencional e defensável: a IA pode ler todo o histórico do projeto para
responder "quais conclusões ainda não têm experimento?", mas nenhum registro entra no
banco sem um humano tê-lo digitado.

## 7. Automação local: hooks e agents

### 7.1 Hooks

| Gatilho | Ação |
|---|---|
| pre-commit | `styler` + `lintr` nos `.R` alterados; falha bloqueia o commit |
| pre-commit | valida sintaxe do `dump.sql` e que ele é append-only em relação a `origin/main` |
| pre-commit | bloqueia se não há registro novo no banco desde o último commit |
| pre-push | roda `./gov auditoria`; aviso se surgiu órfão novo |

### 7.2 Agents

| Agent | Função |
|---|---|
| `revisor-r` | revisão de código R: correção, estilo, reprodutibilidade |
| `auditor-governanca` | caça nó órfão, pendência velha, tarefa sem prazo, cadência |
| `revisor-formulacao` | confere a formulação matemática contra as referências registradas |
| `interrogador` | faz 3 perguntas duras sobre a saída de IA recebida, para o humano responder |

O `interrogador` existe por uma razão de integridade: gerar a crítica automaticamente
fraudaria R6, que exige crítica **humana**. O agent não escreve a crítica; ele torna
difícil registrar "aceito, tudo ok" sem ter entendido. A resposta do humano é que vai
para `ia.critica_humana`.

## 8. CI (GitHub Actions)

| Job | Falha quando |
|---|---|
| `lint-r` | `lintr` acusa problema, ou `styler` mudaria arquivo |
| `testes-r` | `testthat` falha |
| `repro` | pipeline não roda de ponta a ponta em máquina limpa (R13) |
| `governanca` | ID citado no PR não existe no dump; registro de IA sem crítica; taxa de aceite integral acima de 70% no acumulado (aviso a partir de 50%); órfão novo |
| `revisao-bot` | nunca falha; comenta inline no PR |
| `publica` | só em `main`: `./gov update`, gera site, publica no Pages |

Branch protection em `main`: 1 aprovação de outro integrante, jobs obrigatórios
verdes, sem push direto, sem force-push.

Workflow agendado semanal: abre issue se qualquer integrante ficar com zero registros novos no banco na
semana corrente (defesa antecipada contra R12).

## 9. Site (GitHub Pages)

As 8 seções de §5.5, todas geradas do banco: Estado · Grafo executivo (interativo,
`vis-network`, clique no nó abre o registro) · Trilha · Tarefas e pendências ·
Interações com IA (com taxa de aceite e as críticas) · Experimentos · Resultados ·
Reprodutibilidade.

## 10. Onboarding do grupo

`docs/GUIA-GIT.md`, escrito para quem nunca usou Git: o fluxo branch → commit → PR
com comandos para copiar, o que fazer em conflito, e a lista do que não fazer
(commitar em `main`, `git push --force`, aprovar o próprio PR). Mesmo fluxo já em uso
no repositório da Brendi.

## 11. Fora de escopo

- Formulação, dados e resultados do problema de vertiportos (camada A).
- Relatório de engenharia e apresentação.
- Migração a partir do repositório-modelo do professor, se e quando ele chegar
  (previsto como `migrar.py`, não implementado agora).

## 12. Critério de pronto

1. Repo público na org do grupo, os 4 com acesso de escrita, `main` protegida.
2. `./gov` grava as 9 entidades e as arestas; `./gov update` regenera tudo.
3. Site no ar no GitHub Pages com as 8 seções, alimentado pelo banco.
4. CI verde num PR de teste; PR sem registro citado é reprovado pelo CI.
5. Hooks e 4 agents instalados e funcionando.
6. `docs/GUIA-GIT.md` e `README.md` permitem a terceiro clonar e operar sem ajuda.
