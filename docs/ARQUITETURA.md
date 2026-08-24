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
