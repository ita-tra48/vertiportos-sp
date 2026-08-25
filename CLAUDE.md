# TRA-48 — Inteligência Analítica: Dados, Modelos e Decisões (ITA, 2º sem/2026)

Projeto em grupo: aplicar os métodos da disciplina a um problema de **transporte aéreo**.

## Entregas

| Bloco | Métodos | Apresentação | Relatório |
|---|---|---|---|
| B1 | Pesquisa Operacional (PL, Simplex, dual, redes, transporte/transbordo) | 23/09/2026 | 23/09/2026 |
| B2 | Aprendizado de Máquina (cluster, classificação, regressão, anomalia) | 25/11/2026 | 02/12/2026 |

Peso: apresentação = 30% do bimestre; relatórios = 100% da nota de exame.

## Stack

- **R** é a linguagem da disciplina. Código em `app/`, um script por etapa, numerado (`01-carrega.R`, `02-modelo.R`).
- Otimização: `lpSolve` / `ROI`. ML: `tidymodels`, `cluster`. Dados: `tidyverse`.
- Relatório em Quarto/RMarkdown dentro de `relatorio/`.

## Convenções

- `dados/bruto/` é somente-leitura: nunca sobrescrever, todo tratamento gera saída em `dados/tratado/`.
- Figuras do relatório sempre geradas por script, nunca coladas à mão.
- Resultado numérico citado no relatório tem que sair de um script versionado.

## Fontes de dados candidatas

ANAC (dados estatísticos, VRA), DECEA, BTS/T-100 (EUA), OpenSky.

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
- Antes de criar worktree ou abrir PR: git fetch origin && git rebase origin/main.
