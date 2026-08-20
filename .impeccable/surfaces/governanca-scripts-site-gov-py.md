---
version: 1
slug: "governanca-scripts-site-gov-py"
primary_target: "governanca/scripts/site_gov.py"
related_targets: []
---

# Surface brief — site de governança (governanca/scripts/site_gov.py)

## Escopo e modo

Oito páginas estáticas geradas do banco DuckDB e publicadas no GitHub Pages:
Estado, Grafo executivo, Trilha, Tarefas e pendências, Interações com IA,
Experimentos, Resultados, Reprodutibilidade. Modo: **Operate**. A Estado e a
Reprodutibilidade carregam um segundo dever de **Read**, porque são as duas que
alguém sem contexto abre primeiro.

## Audiência, tarefa e ação

Dois professores auditando proveniência, projetado na sala ou no notebook. A
tarefa não é "ver um resumo": é responder uma pergunta específica em um clique —
por que este parâmetro tem este valor, quem decidiu, qual script gerou esta
figura, quais conclusões ainda não têm experimento, onde o grupo discordou da IA.
Secundariamente: os 4 do grupo vendo o que está órfão, atrasado ou sem dono; os
outros grupos comparando números; e leitores de fora depois do curso.

## Conteúdo e prova

Tudo vem do banco. Nada é escrito à mão, então nada pode ser melhorado em
silêncio. O banco está **vazio agora** e fica quase vazio por semanas — vazio é
estado de primeira classe, não caso de borda. A camada de PO não existe ainda:
a página Resultados não pode mostrar figura de placeholder nem número inventado.

## Restrições duras

- Zero dependência de rede em runtime: sem CDN, sem fonte remota, sem fetch.
  Fontes auto-hospedadas em `governanca/assets/fontes/`.
- Determinismo byte-a-byte entre duas gerações.
- Todo texto é livre, digitado por integrante: escapado em conteúdo e atributo.
- Legível a 3 metros projetado e a 50cm no notebook.
- Cor nunca é o único sinal (selo, tipo de registro, relação).

## Direção escolhida

**Documento Controlado** (seed `b1f01bde`, candidato 6). O site é um documento
normativo sob revisão: bloco de título com projeto/revisão/data/autor, cláusulas
numeradas que servem de handle de citação, selo de auditoria estampado como
carimbo, tabelas normativas densas, sistema de fios.

Paleta com quatro papéis reservados: **anil** (estrutura, em escala de página),
**violeta carimbo** (aprovado, vigente), **lápis vermelho** (falha de auditoria,
órfão, atraso — reservado, nunca decorativo), **grafite** (encerrado, inativo).
Ground branco frio, nanquim para texto. Derivada dos materiais reais do mundo —
cópia diazo, carimbo de anilina, marcação de revisão — e não do aglomerado
creme-mais-terracota.

Tipografia **B612** (Airbus, para telas de cockpit; OFL, auto-hospedada). Lei:
mono para identificador, revisão, data, contagem e número de cláusula; sans para
prosa. Escolhida porque é a única face na mesa projetada para ler sob luz ruim,
que é o requisito de projetor — não por associação temática.

## Momento memorável

O carimbo de auditoria na Estado: quando o selo está vermelho, os motivos são
impressos como cláusulas numeradas embaixo dele, com o número de nós órfãos e
os ids. O site delata o próprio grupo, na primeira dobra, em tipografia de
documento controlado. É a prova visual da propriedade que o projeto reivindica.

## Elevações herdadas da rodada de direção

Um objeto dominante por página; estado com forma e rótulo além de cor; grade
modular única compartilhada por tabela, bloco e grafo; paleta com papel
reservado por lei; estado impresso como linha do documento em vez de badge.

## Decisões em aberto

- Se a Estado deve abrir com o selo ou com as metas quando o selo está verde.
- Se o grafo ganha faixa própria por tipo ou densifica quando há muitos nós.
