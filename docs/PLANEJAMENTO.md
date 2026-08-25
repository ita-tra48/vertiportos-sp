# Planejamento preliminar — fatores de decisão para localização de vertiportos

Esta é uma proposta inicial do Gustavo, aberta para validação do grupo até
26/08. A escolha do local dos vertiportos será estruturada por uma análise de
fatores ponderados: cada alternativa de local é avaliada em múltiplos fatores,
não apenas em demanda. Pesos de cada fator e o método de agregação (soma
ponderada, AHP, otimização multiobjetivo etc.) são decisão futura do grupo, a
ser registrada via `./gov` quando fechada.

## Fatores propostos

| Fator | O que mede | Fonte candidata | Como entra no modelo |
|---|---|---|---|
| Demanda OD capturável | Volume de viagens na região que poderiam migrar para o modo aéreo urbano | Pesquisa OD 2017 do Metrô de São Paulo | Função objetivo (maximizar demanda capturada) |
| Renda por zona | Poder aquisitivo médio das zonas de origem/destino, proxy de disposição a pagar | OD 2017, atributo renda | Parâmetro (pondera a demanda por disposição a pagar) |
| Congestionamento / tempo de acesso terrestre | Tempo economizado ao substituir trajeto terrestre por trecho aéreo | OD 2017 (duração de viagens); malha viária OSM | Parâmetro (ganho de tempo por par OD) |
| Infraestrutura existente — helipontos | Locais já habilitados para pouso e decolagem, reduzindo custo de implantação | Cadastro ANAC/DECEA | Restrição (candidatos elegíveis) ou parâmetro de custo |
| Zoneamento e viabilidade urbanística | Compatibilidade do uso do solo e restrições legais de instalação | PDE/zoneamento de SP via GeoSampa | Restrição (exclui locais inviáveis) |
| Custo de implantação | Investimento estimado para viabilizar o local como vertiporto | Literatura, proxy por uso do solo | Parâmetro de custo na função objetivo |
| Complementaridade de rede | Ganho de cobrir pares OD adicionais quando outros vertiportos já estão abertos | Endógeno ao modelo de hubs — interdependência entre locais abertos | Função objetivo (termo de interação entre locais) |

## Como contribuir

Cada integrante revisa a tabela acima: propõe fatores novos, sugere remoção
dos que não fizerem sentido, e comenta a fonte de dados quando tiver uma
melhor. A divisão de responsáveis por fator se fecha em 26/08. Cada fator
aprovado vira uma tarefa no banco de governança (`./gov tarefa`), com um
worktree próprio (`./gov worktree TAR-ID`) para o integrante responsável
trabalhar isolado.

## Fluxo de trabalho paralelo

Antes de criar um worktree ou abrir um PR:

```
git fetch origin && git rebase origin/main
```

Registros de governança (`decisao`, `tarefa`, `pendencia`, `experimento`,
`ia`) sempre entram pelo `./gov` antes do commit correspondente. Toda PR
segue a estrutura de `docs/PADRAO_PR.md`.

## IA no projeto

Estrutura atual: o Mach1-Bot revisa PRs automaticamente, o MCP `gov` dá
contexto do grafo de governança para quem está trabalhando, e toda interação
de IA que chega ao produto é registrada com crítica humana via `./gov ia`.

Fase futura: uso de agents para processos da operação (tratamento de dados,
rodadas de experimento), a ser definido depois que os fatores e os pesos
estiverem fechados pelo grupo.
