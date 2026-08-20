# TRA-48 — Inteligência Analítica: Dados, Modelos e Decisões (ITA, 2º sem/2026)

Projeto em grupo: aplicar os métodos da disciplina a um problema de **transporte aéreo**.

## Entregas

| Bloco | Métodos | Apresentação | Relatório |
|---|---|---|---|
| B1 | Pesquisa Operacional (PL, Simplex, dual, redes, transporte/transbordo) | 23/09/2026 | 23/09/2026 |
| B2 | Aprendizado de Máquina (cluster, classificação, regressão, anomalia) | 25/11/2026 | 02/12/2026 |

Peso: apresentação = 30% do bimestre; relatórios = 100% da nota de exame.

## Stack

- **R** é a linguagem da disciplina. Código em `R/`, um script por etapa, numerado (`01-carrega.R`, `02-modelo.R`).
- Otimização: `lpSolve` / `ROI`. ML: `tidymodels`, `cluster`. Dados: `tidyverse`.
- Relatório em Quarto/RMarkdown dentro de `relatorio/`.

## Convenções

- `dados/bruto/` é somente-leitura: nunca sobrescrever, todo tratamento gera saída em `dados/tratado/`.
- Figuras do relatório sempre geradas por script, nunca coladas à mão.
- Resultado numérico citado no relatório tem que sair de um script versionado.

## Fontes de dados candidatas

ANAC (dados estatísticos, VRA), DECEA, BTS/T-100 (EUA), OpenSky.
