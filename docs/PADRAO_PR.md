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
    reporta (`exp-...`). Um id por linha, com um fragmento do título.

    ## Como verificar
    Comandos concretos: o teste que cobre, o script que roda, a página
    do site que muda.

## Regras

1. Sem seção vazia. Sem "vários ajustes", "melhorias gerais", "WIP".
2. Título da PR: minúsculo, imperativo, ≤ 72 caracteres
   (ex.: `estima demanda capturavel por limiar de tempo`).
3. PR de IA declara o registro `ia-...` correspondente em **Registros**.
4. Uma PR = uma tarefa. Se a descrição precisa de "além disso", divida.
