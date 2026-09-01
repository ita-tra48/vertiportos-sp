# Conjunto de locais candidatos

Critério de montagem do conjunto de candidatos a vertiporto no município de
São Paulo, executado por `app/01-baixa-candidatos.R` e
`app/02-locais-candidatos.R`, com saída em
`dados/tratado/locais_candidatos.csv`.

O enunciado (2.3) lista três origens possíveis de candidato — helipontos
existentes, terminais de transporte e áreas com viabilidade urbanística. Esta
entrega cobre as duas primeiras. A terceira depende do fator de zoneamento
(`tar-my3ius`) e entra numa segunda passada.

## Camadas

| Camada | Origem | n | Infraestrutura |
|---|---|---|---|
| `heliponto` | cadastro ANAC de helipontos privados | 185 | existente |
| `estacao_transporte` | estações de metrô do GeoSampa | 94 | a implantar |

Total: 279 sítios candidatos, 244 aptos na triagem cadastral.

A camada `heliponto` é o conjunto de locais já habilitados para pouso e
decolagem: custo de implantação baixo e viabilidade regulatória demonstrada.
A camada `estacao_transporte` existe porque a cadeia porta-a-porta do
enunciado (2.2) é dominada pelo acesso terrestre — um vertiporto sobre uma
estação de alta capacidade nasce com o trecho de acesso resolvido, ainda que
exija obra. As duas camadas entram no mesmo conjunto de decisão, com custo de
implantação distinto.

## Nenhum candidato é um vertiporto

São Paulo não tem vertiporto. Os 279 registros deste conjunto são **sítios
candidatos** — lugares onde um vertiporto poderia ser implantado — e não
infraestrutura aeronáutica pronta. A coluna `infra_aeronautica` diz apenas o
que existe hoje no local: `existente` para heliponto registrado, `inexistente`
para estação de metrô.

A distinção importa porque um heliponto não vira vertiporto por aprovação
cadastral. A conversão exige, em categorias que o cadastro da ANAC **não**
descreve:

| Requisito de vertiporto | Por que o cadastro de heliponto não responde |
|---|---|
| Geometria FATO/TLOF dimensionada pela dimensão de controle da aeronave eVTOL | o cadastro traz a dimensão construída para helicóptero, não a exigida pelo eVTOL de projeto |
| Alimentação elétrica para recarga | eVTOL recarrega entre ciclos; heliponto de cobertura não tem essa ordem de potência disponível |
| Superfícies de aproximação e decolagem sob norma de vertiporto | o campo de rampa do cadastro segue a norma de heliponto |
| Processamento de passageiros e capacidade de posições | operação comercial em rede, não pouso eventual |
| Reforço estrutural verificado por laudo | `resistencia_t` é valor cadastral, não laudo |

As normas de referência para esses requisitos — FAA EB-105 (vertiport design),
EASA PTS-VPT-DSN e, no Brasil, a ausência de regulamento específico da ANAC,
que hoje cobre heliponto pelo RBAC 155 — ainda **não foram confrontadas com o
conjunto**. Isso é `pen-` aberta, não conclusão.

## Triagem cadastral

A coluna `apto_triagem` **não** afirma aptidão a vertiporto. Ela registra
apenas que o sítio passou na triagem possível com os dados disponíveis, que na
camada `heliponto` são os atributos físicos do cadastro:

| Regra | Parâmetro | Efeito |
|---|---|---|
| resistência do pavimento ≥ MTOW de referência | 3,2 t | −35 |
| maior dimensão da área de pouso ≥ TLOF mínimo | 18 m | 0 |
| operação diurna VFR registrada | — | 0 |

O MTOW de referência de 3,2 t corresponde à classe de eVTOL de 7.000 lb
(Archer Midnight, Vertical VX4), que é o limite de categoria de certificação
sob o qual os projetos comerciais anunciados para São Paulo se enquadram. É um
critério de **descarte**, não de aprovação: reprovar por resistência elimina o
sítio, mas passar não qualifica ninguém como vertiporto.

Estações de metrô não têm atributo físico de pouso no cadastro e entram como
elegíveis por construção: a verificação delas é urbanística, não cadastral, e
fica pendente do fator de zoneamento.

## Sensibilidade do limiar de MTOW

Este é o parâmetro que mais move o conjunto, e ele não é contínuo:

| MTOW de referência | Helipontos elegíveis |
|---|---|
| 2,4 t (classe Joby S4) | 183 |
| 3,0 t | 183 |
| **3,2 t (adotado)** | **150** |
| 4,0 t | 148 |

O conjunto é plano até 3,0 t e cai de 183 para 150 em 3,2 t, porque 3,0 t é o
valor de projeto mais comum dos helipontos de cobertura da cidade. São 35 dos
185 helipontos — cerca de um quinto da camada, 13% do conjunto de 279 — que
entram ou saem por causa da aeronave de referência escolhida, e não por causa
do dado. O limiar fica parametrizado no topo de `app/02-locais-candidatos.R`
para entrar na análise de sensibilidade exigida em 4.4.

## Agrupamento espacial

A mediana da distância ao heliponto mais próximo é de 235 m, e 60 dos 185
helipontos têm vizinho a menos de 150 m — o eixo Faria Lima–Itaim–Berrini
concentra coberturas contíguas. Candidatos a menos de 150 m um do outro
recebem o mesmo `agrupamento_id`, e o primeiro de cada grupo é marcado em
`representante_agrupamento` (233 grupos).

O agrupamento é **coluna, não filtro**. Dois helipontos a 150 m são
infraestrutura distinta e real; tratá-los como um só ponto é redução de
instância, que é decisão da formulação (`tar-s26xcn`), não do dado. O conjunto
entregue permite as duas leituras sem reprocessamento.

## Esquema da saída

`dados/tratado/locais_candidatos.csv`, 279 linhas, 18 colunas:

| Coluna | Conteúdo |
|---|---|
| `id_candidato` | `CAN-0001`… , estável dentro de uma execução |
| `camada` | `heliponto` \| `estacao_transporte` |
| `infra_aeronautica` | `existente` (heliponto) \| `inexistente` (estação) |
| `nome` | nome cadastral |
| `lat`, `lon` | WGS84 graus decimais |
| `tipo_local` | `Elevado`/`No solo`, ou empresa e linha da estação |
| `tlof_m` | maior dimensão da área de pouso, em metros |
| `resistencia_t` | resistência do pavimento, em toneladas |
| `op_diurna`, `op_noturna` | regra de voo registrada |
| `apto_triagem` | passou na triagem cadastral — não é aptidão a vertiporto |
| `motivo_exclusao` | regra que reprovou, quando houver |
| `agrupamento_id` | id do representante do grupo a 150 m |
| `representante_agrupamento` | é o representante do próprio grupo |
| `fonte`, `fonte_id`, `codigo_oaci` | rastro até o registro de origem |

## Limitações conhecidas

- O cadastro ANAC de helipontos privados não cobre helipontos públicos nem
  helidecks; para o município de São Paulo os 185 registros são todos de uso
  privado, o que é uma restrição de acesso que o modelo não representa.
- A camada do GeoSampa é `estacao_metro`: traz Metrô e ViaQuatro, e não traz
  CPTM, terminais de ônibus nem o monotrilho da Linha 15 quando classificado
  fora dessa camada. Terminais de ônibus estão em `estacao_transbordo` e ficam
  para a segunda passada.
- A resistência do pavimento é a registrada no cadastro, não uma verificação
  estrutural: um heliponto aprovado aqui ainda exigiria laudo para receber
  eVTOL.
- Não há verificação de espaço aéreo, de proximidade de PZR ou de rampa de
  aproximação livre. Helipontos em SP operam sob restrições de tráfego que o
  conjunto não representa.
- Estações de metrô não têm viabilidade urbanística verificada. São candidatos
  por potencial de acesso, não por elegibilidade demonstrada.

## Reprodução

```
Rscript app/01-baixa-candidatos.R
Rscript app/02-locais-candidatos.R
```

Os dois arquivos brutos caem em `dados/bruto/` e não são versionados. O
primeiro script não sobrescreve o que já estiver lá.
