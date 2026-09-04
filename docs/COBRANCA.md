# Cobrança diária

Todo dia às 08h de Brasília o workflow `cobranca` reconstrói o banco do
`governanca/dump.sql`, lê as tarefas com `status = 'aberta'` e manda para
cada responsável um e-mail só com as tarefas dele.

**Quem está em dia não recebe nada.** Se ninguém tem tarefa aberta, o
workflow não envia e-mail nenhum. Receber o e-mail já é o sinal.

## O que vai na mensagem

As tarefas saem agrupadas por urgência — `ATRASADA`, `PARA HOJE`,
`ESTA SEMANA`, `MAIS ADIANTE`, `SEM PRAZO` —, cada uma com o prazo, o id
`tar-` e, quando houver, a pendência aberta que a bloqueia. O assunto diz
quantas são e quantas venceram.

## Segredos do repositório

O repo é público: e-mail de integrante não entra em arquivo versionado.
Os três valores ficam em *Settings → Secrets and variables → Actions*.

| Segredo | Conteúdo |
|---|---|
| `EMAILS_JSON` | mapa do campo `resp` da tarefa para o endereço |
| `SMTP_USUARIO` | conta remetente |
| `SMTP_SENHA` | senha de app da conta remetente, não a senha da conta |

O `EMAILS_JSON` casa a chave com o `resp` ignorando maiúscula e espaço
extra, e aceita mais de um endereço para o mesmo responsável — é assim
que a tarefa cujo `resp` é `grupo` chega a todo mundo:

    {
      "Gustavo": "...",
      "Italo": "...",
      "Carlos": "...",
      "Matheus": "...",
      "grupo": "..., ..., ..., ..."
    }

Responsável com tarefa aberta e sem endereço no mapa vira aviso no log do
workflow, não erro: o resto do envio continua.

## Testar sem enviar

    EMAILS_JSON='{"Italo":"italo@exemplo.com"}' \
      python governanca/scripts/cobranca.py --seco

Imprime as mensagens que sairiam. Pelo GitHub, *Actions → cobranca → Run
workflow* com a caixa **seco** marcada faz o mesmo no runner.
