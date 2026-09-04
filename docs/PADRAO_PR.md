# Padrão de descrição de PR

Vale para qualquer autor — humano ou IA. O Mach1-Bot cobra este padrão.

## Estrutura obrigatória

    ## O que muda
    Uma a três frases, no presente, sem jargão vazio.

    ## Por quê
    A motivação. Se existe decisão registrada, ela é citada aqui.

    ## Registros
    Ids `gov` desta PR (obrigatório ≥ 1): a tarefa que ela executa
    (`tar-...`), decisões que aplica (`dec-...`), experimentos que
    reporta (`exp-...`), a interação com IA que a produziu (`ia-...`).
    Um id por linha, com um fragmento do título.

    ## Como verificar
    Comandos concretos: o teste que cobre, o script que roda, a página
    do site que muda.

## Regras

1. Sem seção vazia. Sem "vários ajustes", "melhorias gerais", "WIP".
2. Título da PR: minúsculo, imperativo, ≤ 72 caracteres
   (ex.: `estima demanda capturavel por limiar de tempo`).
3. Uma PR = uma tarefa. Se a descrição precisa de "além disso", divida.

## Registro de IA: obrigatório declarar

Toda PR declara em **Registros** o `ia-...` da interação que a produziu,
ou traz a linha literal `sem IA nesta PR` na mesma seção. Não existe
terceira opção: o projeto inteiro é desenvolvido com IA, e o enunciado
5.6 pede o registro com crítica humana de toda interação relevante.

O `ia-...` entra por `./gov ia --critica "..."`, que recusa crítica com
menos de 20 caracteres. A crítica é do integrante, não da IA: diz o que
foi corrigido, o que foi recusado e o que foi aceito com ressalva. Taxa
de aceite integral próxima de 100% será examinada na arguição.

## Teto de tamanho

Uma PR cabe na cabeça de quem revisa. Os tetos:

| Medida | Teto | Como contar |
|---|---|---|
| Decisões novas | 3 | registros `dec-` criados nesta PR |
| Linhas adicionadas | 400 | só escrita humana |
| Arquivos alterados | 10 | todos |

Escrita humana exclui `dados/`, `governanca/dump.sql` e
`governanca/site/`: são saída de script, não texto escrito à mão.

O teto que morde é o de decisões. Linha e arquivo medem volume; decisão
mede quantas escolhas independentes o revisor precisa julgar de uma vez.
Uma PR com seis decisões novas são seis discussões diferentes empilhadas
num único fio de comentários, e nenhuma delas recebe a atenção que
mereceria.

**Estourou qualquer um dos três:** ou divide a PR, ou acrescenta a seção

    ## Por que não dividi

com a razão pela qual as partes não se sustentam separadas — dependência
técnica real, não pressa. Sem essa seção, o Mach1-Bot aponta a violação.

Divida por decisão, não por arquivo: cada `dec-` que muda o resultado
puxa consigo o código, o dado e a documentação que a aplicam.
