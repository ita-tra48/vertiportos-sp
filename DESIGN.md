# Design — Documento Controlado

<!-- impeccable:design 1 -->

Mundo visual do site de governança do Projeto B1 (TRA-48), gerado por
`governanca/scripts/site_gov.py` e `governanca/scripts/grafo.py`. Escrito a
partir do que foi construído, não do que foi planejado.

**Direção:** Documento Controlado — candidato 6 da lista ordenada, seed
`b1f01bde`. O contrato de direção vive como comentário HTML no topo de `<body>`
de cada página (`CONTRATO` em `site_gov.py`), então sobrevive ao build e é
auditável na página publicada.

## 1. A tese

O site é um documento normativo sob revisão, não um painel. Recusa
deliberadamente os dois arranjos que a categoria entrega: a fileira de tiles de
métrica ("número grande, rótulo pequeno") e a grade de cartões de tamanho igual
como estrutura de página. No lugar: bloco de título, cláusulas numeradas que
funcionam como handle de citação, carimbo de auditoria e tabelas normativas.

Derivado da tradição gráfica em que os próprios avaliadores publicam — o PDF do
enunciado tem capa com "Produzido por" e "Aprovado por".

## 2. Paleta: quatro papéis reservados por lei

Tokens em `:root` dentro de `ESTILO`. Cada cor tem **um** significado. Uma cor
usada decorativamente para de significar, e a lei existe para impedir isso.

| token | valor | papel exclusivo |
|---|---|---|
| `--papel` | `#fbfbf9` | a folha |
| `--mesa` | `#e7e8ea` | a mesa atrás da folha |
| `--nanquim` | `#14181c` | texto corrente |
| `--nanquim2` | `#48535e` | texto secundário, cabeçalho de tabela |
| `--anil` | `#14457f` | **estrutura**: bloco de título, fios, número de cláusula, nav, links |
| `--carimbo` | `#5a3a92` | **aprovação**: selo APROVADO, estado vigente |
| `--lapis` | `#ab2118` | **falha**: reprovação, órfão, atraso. Reservado. |
| `--grafite` | `#5c646d` | inativo, não auditado, id secundário |
| `--fio` / `--fio-forte` | `#c3c9d1` / `#98a1ab` | fios de régua |

A primeira paleta que eu escrevi era papel creme com vermelho de sinal — o
aglomerado exato em que modelos caem. Descartada e rederivada dos materiais
reais do mundo: folha de desenho técnico é branco frio com nanquim, cópia diazo
é azul anil, carimbo brasileiro é violeta anilina, marcação de revisão é lápis
vermelho.

**Claro, sem variante escura.** Escolhido pela cena de uso, não por categoria:
projetado numa sala iluminada e lido num notebook. Fundo escuro lava no
projetor, e um documento impresso não tem versão invertida. `color-scheme:light`
declarado para o cromo do navegador acompanhar.

### Cores do grafo

Nove tipos de entidade precisam ser distinguíveis, então o tipo **é** o
significado. A família é de tintas de desenho técnico, todas escuras o
suficiente para a folha clara: anil, violeta, verde nanquim, sépia, teal,
grafite, ocre, lápis, magenta anilina (`CORES` em `grafo.py`). Cor nunca é o
único sinal: cada nó carrega rótulo de texto, e a trilha carrega sigla de três
letras (`SIGLAS`).

## 3. Tipografia

**B612**, desenhada pela Airbus para telas de cockpit, SIL OFL 1.1,
auto-hospedada em `governanca/assets/fontes/` (quatro faces, subset pt-BR,
48 KB no total, convertidas para woff2). Escolhida porque é a única face na mesa
projetada para ser lida sob vibração e luz ruim — que é literalmente o requisito
de projetor. Não por associação temática com aeronáutica.

**Lei de uso:**
- `--mono` (B612 Mono): identificador, revisão, data, hora, número de cláusula,
  sigla, rótulo de cabeçalho, o carimbo. Os fatos de máquina do documento.
- `--sans` (B612): prosa e **quantidade medida**. Percentual e contagem em
  `.indices` são sans com `tabular-nums`, não mono — o ponto decimal em mono
  abre um vão que lê como espaço (`100. 0%`).

Escala de raiz responsiva: `clamp(14.5px, .36vw + 10.4px, 19px)`. A 1512px dá
15.8px; num projetor 1920 dá ~17.3px. Medida de prosa limitada a 68ch.

## 4. Composição

`.folha` é a folha (máx. 1240px, moldura de fio, sombra com deslocamento e
blur). Dentro:

- `.cabeca` — identidade em duas linhas deliberadas à esquerda, `.bloco` de
  título à direita (projeto, revisão, registros, auditoria) com borda de nanquim.
- `.corpo` — grade de duas colunas: rail de cláusulas de 15.5rem e `main`.
  Abaixo de 900px vira uma coluna e o rail vira faixa numerada que embrulha.
- `.rodape` — a regra do projeto e a procedência da folha.

**Um objeto dominante por página.** Estado abre com o carimbo; Grafo com o SVG
na moldura; Trilha com a espinha de registros. O carimbo **não** é card: não tem
borda nem fundo próprios, porque card é o container preguiçoso — o selo é tinta
na folha, e a moldura dele é a própria borda dupla do carimbo.

`.indices` é tabela de definição regrada, não fileira de tiles.

## 5. Estados e honestidade

Três estados de selo, e o terceiro existe porque a versão de dois mentia:

| selo | quando | cor |
|---|---|---|
| APROVADO | sem apontamento | `--carimbo` |
| REPROVADO | qualquer apontamento | `--lapis` |
| NÃO AUDITADO | sem meta ou sem decisão registrada | `--grafite` |

Antes disso, um banco vazio estampava APROVADO e declarava 100% de
rastreabilidade sobre zero registros — invertendo a única propriedade que o
projeto reivindica. `_pct` devolve `None` quando o denominador é zero e a página
imprime travessão, nunca 100%.

Vazio é estado de primeira classe: cada tabela tem texto de vazio próprio que
diz o que fazer (`"Nenhuma meta registrada. O projeto começa por ./gov meta."`),
não "sem registros".

## 6. Movimento

Um momento autorado: `@keyframes bate`, o carimbo assentando —
`scale(1.035)` + `blur(1.5px)` para nítido, 500ms, `cubic-bezier(.16,1,.3,1)`.
Parte de um default já visível (sem fade de opacidade). Anulado sob
`prefers-reduced-motion`. Nada mais anima.

## 7. Superfícies do navegador

Tematizadas, porque são a parte que ninguém desenha: `::selection` em anil
fraco, `:focus-visible` com contorno anil de 2px e offset, `scrollbar-color` e
`::-webkit-scrollbar` em fio forte, `text-underline-offset` em links,
`tabular-nums` em toda célula numérica, favicon SVG inline (carimbo) como data
URI.

## 8. Restrições que o mundo tem de respeitar

- **Zero dependência de rede.** Sem CDN, fonte remota, imagem remota ou fetch.
  A única string externa permitida é o namespace SVG.
- **Determinismo byte-a-byte** entre duas gerações do mesmo banco.
- **Todo texto é livre**, digitado por integrante: escapado em conteúdo e
  atributo, incluindo chave e valor crus do payload na trilha.
- **Contraste** acima de 4.5:1 para corpo. `--grafite` foi escurecido de
  `#767e87` (3.9:1, reprovado) para `#5c646d`.
- Identificador e data não quebram no meio: `_ID` e `_QUANDO` marcam a célula
  com `.ident` e `white-space:nowrap`.

## 9. Verificação feita

Rodada em lote a 1512px e 390px, cheio e vazio, com valores computados lidos no
navegador: sem overflow horizontal de página; tabelas largas rolam dentro do
próprio container; quatro faces carregadas; grade de duas colunas ativa acima de
900px. O detector mecânico rodou **degradado** (módulos de parser ausentes) e
não avalia custom properties nem contraste computado — o zero achados dele é
subcontagem, não atestado.
