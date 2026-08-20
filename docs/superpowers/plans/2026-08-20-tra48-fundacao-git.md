# TRA-48 — Plano 1: Fundação do repositório e governança de Git

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ter um repositório público na org do grupo em que os 4 integrantes consigam abrir, revisar e mergear PRs, com `main` protegida, autoria rastreável e um guia que um iniciante em Git consegue seguir sozinho.

**Architecture:** Org GitHub nova hospeda um repo público único. A estrutura de pastas espelha o organograma de §5.2 do enunciado. A governança é declarativa: `CODEOWNERS` roteia revisão por frente, ruleset de branch protection exige aprovação de terceiro, templates de PR e issue obrigam a citação de registros. `.gitattributes` prepara o merge sem conflito do `dump.sql` que o Plano 2 vai criar.

**Tech Stack:** git, `gh` CLI (GitHub Actions e Python entram nos planos 2-4), Markdown.

**Spec:** `docs/superpowers/specs/2026-08-20-tra48-governanca-design.md`

## Global Constraints

- Conta GitHub a usar: **`gustavovfeitosa`**. A conta `gustavovidal-tiktok` NUNCA é usada neste projeto. Antes de qualquer comando `gh`, confirmar com `gh auth status` e trocar com `gh auth switch --user gustavovfeitosa`.
- Repositório **público** (exigência de §6.2: site e repo públicos; e Pages grátis).
- Linguagem da disciplina: **R**. Motor de governança em **Python 3**.
- `governanca/projeto.duckdb` nunca é versionado. `governanca/dump.sql` é o artefato versionado (§1.2 do spec).
- Comentário de código: teto de 1 linha por commit no diff inteiro. Contexto vai na descrição do PR.
- Mensagens de commit em português, minúsculas, imperativas, concisas.
- Ninguém aprova o próprio PR (§2 do spec).

---

### Task 1: Configuração da equipe como dado versionado

Antes de qualquer coisa no GitHub, os nomes e handles do grupo precisam existir em um arquivo, porque `CODEOWNERS`, convites e papéis todos derivam deles. Uma fonte única evita divergência entre os três.

**Files:**
- Create: `governanca/config/equipe.yml`
- Test: `governanca/config/equipe.test.sh`

**Interfaces:**
- Produces: `governanca/config/equipe.yml` com chaves `integrantes[].nome`, `.handle`, `.papel`, `.frente`. Os planos 2-4 leem este arquivo para atribuir autoria e validar `--resp`.

- [ ] **Step 1: Escrever o teste que falha**

```bash
# governanca/config/equipe.test.sh
set -euo pipefail
F="$(dirname "$0")/equipe.yml"

test -f "$F" || { echo "FALHA: equipe.yml nao existe"; exit 1; }

n=$(grep -c '^\s*- nome:' "$F")
[ "$n" -eq 4 ] || { echo "FALHA: esperados 4 integrantes, achei $n"; exit 1; }

for campo in handle papel frente; do
  c=$(grep -c "^\s*$campo:" "$F")
  [ "$c" -eq 4 ] || { echo "FALHA: campo '$campo' aparece $c vezes, esperado 4"; exit 1; }
done

if grep -q 'tiktok' "$F"; then echo "FALHA: conta proibida citada"; exit 1; fi

papeis=$(grep '^\s*papel:' "$F" | sed 's/.*papel: *//' | sort -u | wc -l | tr -d ' ')
[ "$papeis" -eq 4 ] || { echo "FALHA: papeis repetidos"; exit 1; }

echo "OK: equipe.yml valido"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `bash governanca/config/equipe.test.sh`
Expected: FAIL com "FALHA: equipe.yml nao existe"

- [ ] **Step 3: Criar o arquivo com os dados reais do grupo**

Substituir os quatro blocos pelos nomes e handles reais. Os quatro papéis são fixos (§2 do spec); o que varia é quem ocupa cada um.

```yaml
# governanca/config/equipe.yml
integrantes:
  - nome: Gustavo Vidal Feitosa
    handle: gustavovfeitosa
    papel: governanca
    frente: motor gov, auditoria, site, CI, integracao do relatorio
  - nome: NOME_REAL_2
    handle: HANDLE_REAL_2
    papel: dados
    frente: fontes, zonas OD, agregacao, demanda capturavel
  - nome: NOME_REAL_3
    handle: HANDLE_REAL_3
    papel: modelagem
    frente: formulacao, variaveis, restricoes, tratabilidade, solver
  - nome: NOME_REAL_4
    handle: HANDLE_REAL_4
    papel: experimentos
    frente: rodadas, relaxacao linear, dual, sensibilidade, fronteira
```

Se os nomes reais ainda não estiverem disponíveis, PARE aqui e peça ao usuário. Não prossiga com placeholders: `CODEOWNERS` com handle inválido faz o GitHub ignorar a regra silenciosamente, o que é pior que erro.

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `bash governanca/config/equipe.test.sh`
Expected: `OK: equipe.yml valido`

- [ ] **Step 5: Commit**

```bash
git add governanca/config/equipe.yml governanca/config/equipe.test.sh
git commit -m "config da equipe com papeis e handles"
```

---

### Task 2: Esqueleto de pastas fiel ao organograma do enunciado

**Files:**
- Create: `governanca/schemas/.gitkeep`, `governanca/scripts/.gitkeep`, `governanca/dashboard/.gitkeep`
- Create: `app/dados/bruto/.gitkeep`, `app/dados/tratado/.gitkeep`, `app/R/modelo/.gitkeep`, `app/R/exp/.gitkeep`, `app/resultados/.gitkeep`, `app/testes/.gitkeep`
- Create: `docs/.gitkeep`, `.github/workflows/.gitkeep`
- Modify: `.gitignore`
- Create: `.gitattributes`
- Test: `governanca/scripts/estrutura.test.sh`

**Interfaces:**
- Produces: a árvore de diretórios que os planos 2-4 assumem. `app/R/prep-*.R` (Dados), `app/R/modelo/` (Modelagem), `app/R/exp/` (Experimentos), `governanca/scripts/` (motor).

- [ ] **Step 1: Escrever o teste que falha**

```bash
# governanca/scripts/estrutura.test.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

esperados="governanca/schemas governanca/scripts governanca/dashboard governanca/config \
app/dados/bruto app/dados/tratado app/R/modelo app/R/exp app/resultados app/testes \
docs .github/workflows"

for d in $esperados; do
  test -d "$d" || { echo "FALHA: falta diretorio $d"; exit 1; }
done

grep -q 'projeto.duckdb' .gitignore || { echo "FALHA: .duckdb nao esta no gitignore"; exit 1; }
grep -q 'dump.sql merge=union' .gitattributes || { echo "FALHA: merge driver do dump ausente"; exit 1; }

if git ls-files --error-unmatch governanca/dump.sql >/dev/null 2>&1; then
  echo "FALHA: dump.sql versionado antes do Plano 2"; exit 1
fi

echo "OK: estrutura valida"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `bash governanca/scripts/estrutura.test.sh`
Expected: FAIL com "FALHA: falta diretorio governanca/schemas"

- [ ] **Step 3: Criar a estrutura**

```bash
mkdir -p governanca/{schemas,scripts,dashboard} \
         app/{dados/{bruto,tratado},R/{modelo,exp},resultados,testes} \
         docs .github/workflows
find governanca app docs .github -type d -empty -exec touch {}/.gitkeep \;
```

- [ ] **Step 4: Ajustar `.gitignore`**

Acrescentar ao final do `.gitignore` existente:

```
governanca/projeto.duckdb
governanca/projeto.duckdb.wal
governanca/dashboard/*.html
!governanca/dashboard/.gitkeep
.Rproj.user/
*.Rcheck/
```

- [ ] **Step 5: Criar `.gitattributes`**

O merge driver `union` faz o Git concatenar os dois lados quando duas pessoas adicionam registros diferentes ao dump na mesma janela, em vez de marcar conflito. Funciona porque o dump é append-only.

```
governanca/dump.sql merge=union linguist-generated=true
docs/** linguist-documentation=true
*.R text eol=lf
*.py text eol=lf
*.sh text eol=lf
```

- [ ] **Step 6: Rodar o teste e confirmar que passa**

Run: `bash governanca/scripts/estrutura.test.sh`
Expected: `OK: estrutura valida`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "esqueleto de pastas, gitignore e merge driver do dump"
```

---

### Task 3: CODEOWNERS e templates de PR e issue

**Files:**
- Create: `.github/CODEOWNERS`
- Create: `.github/pull_request_template.md`
- Create: `.github/ISSUE_TEMPLATE/pendencia.md`
- Create: `.github/ISSUE_TEMPLATE/tarefa.md`
- Test: `governanca/scripts/codeowners.test.sh`

**Interfaces:**
- Consumes: `governanca/config/equipe.yml` (Task 1) — os handles.
- Produces: `.github/pull_request_template.md` com a linha `Registros:` que o job `governanca` do Plano 4 parseia. O formato exato é `Registros: D-014, E-007` — prefixo, hífen, três dígitos, separados por vírgula.

- [ ] **Step 1: Escrever o teste que falha**

```bash
# governanca/scripts/codeowners.test.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
CO=.github/CODEOWNERS
PR=.github/pull_request_template.md

test -f "$CO" || { echo "FALHA: CODEOWNERS ausente"; exit 1; }
test -f "$PR" || { echo "FALHA: template de PR ausente"; exit 1; }

for h in $(grep '^\s*handle:' governanca/config/equipe.yml | sed 's/.*handle: *//'); do
  grep -q "@$h" "$CO" || { echo "FALHA: handle $h nao aparece no CODEOWNERS"; exit 1; }
done

for p in "app/R/modelo/" "app/R/exp/" "app/dados/" "governanca/" ".github/"; do
  grep -q "$p" "$CO" || { echo "FALHA: caminho $p sem owner"; exit 1; }
done

grep -q '^Registros:' "$PR" || { echo "FALHA: template de PR sem campo Registros"; exit 1; }
grep -qi 'critica' "$PR" || { echo "FALHA: template de PR nao pergunta pela critica a IA"; exit 1; }

echo "OK: codeowners e templates validos"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `bash governanca/scripts/codeowners.test.sh`
Expected: FAIL com "FALHA: CODEOWNERS ausente"

- [ ] **Step 3: Escrever o `CODEOWNERS`**

Trocar os handles pelos reais de `equipe.yml`. A última regra que casa é a que vale, então a ordem importa: geral primeiro, específico depois.

```
* @gustavovfeitosa

app/dados/            @HANDLE_DADOS
app/R/prep-*.R        @HANDLE_DADOS
app/R/modelo/         @HANDLE_MODELAGEM
app/R/exp/            @HANDLE_EXPERIMENTOS
app/resultados/       @HANDLE_EXPERIMENTOS
governanca/           @gustavovfeitosa
.github/              @gustavovfeitosa
docs/                 @gustavovfeitosa
```

- [ ] **Step 4: Escrever o template de PR**

```markdown
Registros: 

## O que muda

<!-- uma frase por mudança -->

## Por quê

<!-- o motivo. se a decisão metodológica é nova, ela precisa estar registrada
     no banco e citada acima em "Registros:" -->

## Como testar

- [ ] 

## IA neste PR

- [ ] Usei IA neste PR e registrei a interação (`./gov ia`), com crítica humana
- [ ] Não usei IA neste PR

Crítica registrada: 

## Antes de pedir revisão

- [ ] `Registros:` preenchido com IDs que existem no banco
- [ ] Rodei os testes localmente
- [ ] Comentários de código: no máximo 1 linha no diff inteiro
- [ ] Não vou aprovar meu próprio PR
```

- [ ] **Step 5: Escrever os templates de issue**

```markdown
---
name: Pendência
about: Algo que trava o projeto e depende de terceiro ou de definição
labels: pendencia
---

O que trava: 

Depende de: 

Registro no banco (`./gov pendencia`): P-
```

```markdown
---
name: Tarefa
about: Trabalho a fazer, com responsável e prazo
labels: tarefa
---

Tarefa: 

Responsável: 

Prazo (AAAA-MM-DD): 

Meta a que se vincula: M-

Registro no banco (`./gov tarefa`): T-
```

- [ ] **Step 6: Rodar o teste e confirmar que passa**

Run: `bash governanca/scripts/codeowners.test.sh`
Expected: `OK: codeowners e templates validos`

- [ ] **Step 7: Commit**

```bash
git add .github/
git commit -m "codeowners por frente e templates de pr e issue"
```

---

### Task 4: Guia de Git para iniciante

Este é entregável avaliado: §6.2 exige que terceiro consiga operar o projeto sem ajuda, e três dos quatro integrantes podem nunca ter usado Git.

**Files:**
- Create: `docs/GUIA-GIT.md`
- Modify: `README.md`
- Test: `governanca/scripts/guia.test.sh`

**Interfaces:**
- Consumes: o formato `Registros:` de Task 3.

- [ ] **Step 1: Escrever o teste que falha**

```bash
# governanca/scripts/guia.test.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
G=docs/GUIA-GIT.md
test -f "$G" || { echo "FALHA: guia ausente"; exit 1; }

for t in "git switch -c" "git add" "git commit" "git push" "gh pr create" "git pull" "conflito" "force"; do
  grep -qi -- "$t" "$G" || { echo "FALHA: guia nao cobre '$t'"; exit 1; }
done

grep -q 'GUIA-GIT' README.md || { echo "FALHA: README nao aponta pro guia"; exit 1; }
echo "OK: guia completo"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `bash governanca/scripts/guia.test.sh`
Expected: FAIL com "FALHA: guia ausente"

- [ ] **Step 3: Escrever o guia**

```markdown
# Guia de Git do projeto

Três conceitos, e depois o procedimento.

**Commit** é um pacote de mudanças salvo no histórico, com autor, data, mensagem e
as linhas exatas que mudaram. Não é "salvar arquivo": é criar um ponto do histórico
ao qual dá pra voltar e a quem dá pra atribuir responsabilidade.

**SHA** é o nome do commit: um código de 40 caracteres calculado do conteúdo dele.
Mudou uma vírgula, muda o SHA inteiro. Serve de âncora: gravar o SHA num experimento
significa "este número saiu deste código, não de uma versão parecida". No dia a dia
usamos os 7 primeiros.

**Branch** é uma linha de trabalho paralela. Você tira uma da `main`, mexe à vontade
sem afetar ninguém, e no fim pede pra juntar. `main` é o estado bom e publicado.

**PR** (pull request) é o pedido de juntar sua branch na `main`. É onde outra pessoa
revisa, comenta e aprova. Aqui nenhum código entra na `main` sem PR aprovado.

## O procedimento, do começo ao fim

Uma vez só, na primeira vez:

    git clone https://github.com/ORG/REPO.git
    cd REPO
    git config user.name "Seu Nome"
    git config user.email "seu@email"

A cada tarefa nova:

    git switch main
    git pull

Sempre comece atualizado. `pull` traz o que os outros mergearam.

    git switch -c dados/demanda-od

Cria a branch e já entra nela. Nome no padrão `frente/assunto-curto`: `dados/...`,
`modelo/...`, `exp/...`, `gov/...`.

Trabalhe. Quando tiver algo coerente:

    git status
    git add app/R/prep-od.R
    git commit -m "le a pesquisa od e agrega por zona"

`status` mostra o que mudou. `add` escolhe o que entra no commit. `commit` fecha o
pacote. Um commit por ideia: não junte três coisas diferentes num só, porque na hora
de desfazer uma você desfaz as três.

Antes de subir, registre no banco o que precisa ser registrado:

    ./gov decisao "Agregacao por zona OD 2017" --just "..." --alt "..."

Anote o ID que ele devolve (`D-014`). Suba:

    git push -u origin dados/demanda-od
    gh pr create --draft

Preencha o template. O campo `Registros:` recebe os IDs (`Registros: D-014`). PR sem
isso é reprovado pelo robô de verificação.

Peça revisão a alguém de outra frente. Quando aprovarem e as verificações estiverem
verdes, tire de rascunho e mergeie pela interface do GitHub.

Depois do merge, volte pra `main` e atualize:

    git switch main
    git pull

## Quando der conflito

Conflito é o Git dizendo "duas pessoas mudaram a mesma linha, decida você". Não é
erro nem perda de trabalho. Traga a `main` pra sua branch:

    git switch main
    git pull
    git switch sua-branch
    git merge main

Se acusar conflito, abra o arquivo apontado. Você vai ver:

    <<<<<<< HEAD
    sua versão
    =======
    a versão da main
    >>>>>>> main

Apague os marcadores e deixe o texto correto (às vezes é um dos lados, às vezes é a
combinação). Depois:

    git add ARQUIVO
    git commit
    git push

Na dúvida sobre qual lado fica, chame quem escreveu o outro lado. Adivinhar aqui
apaga o trabalho de alguém.

## O que não fazer

- **Não commite na `main`.** Ela é protegida; a tentativa vai ser recusada.
- **Nunca `git push --force`.** Reescreve o histórico e apaga trabalho dos outros.
  Se achar que precisa, pergunte antes.
- **Não aprove o próprio PR.** Regra do projeto e do enunciado.
- **Não commite dados brutos grandes** em `app/dados/bruto/`: ele é ignorado pelo
  Git de propósito. Registre a fonte com `./gov fonte` e deixe o script baixar.
- **Não commite `governanca/projeto.duckdb`.** É binário; o versionado é o `dump.sql`.

## Se der errado

Nada que ainda não foi para o `push` é irreversível.

- Mexi e quero descartar um arquivo: `git restore ARQUIVO`
- Commitei e quero desfazer o commit mantendo as mudanças: `git reset --soft HEAD~1`
- Não sei o que fiz: `git status` e mande a saída no grupo antes de tentar consertar.
```

- [ ] **Step 4: Apontar o guia no `README.md`**

Acrescentar ao `README.md`:

```markdown
## Como contribuir

Leia `docs/GUIA-GIT.md` antes do primeiro commit. Fluxo: branch → commit → PR →
revisão de alguém de outra frente → merge. Nada entra na `main` direto.
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `bash governanca/scripts/guia.test.sh`
Expected: `OK: guia completo`

- [ ] **Step 6: Commit**

```bash
git add docs/GUIA-GIT.md README.md
git commit -m "guia de git para iniciante e ponteiro no readme"
```

---

### Task 5: Org e repositório no GitHub

**Files:**
- Nenhum arquivo local. Estado remoto.
- Test: `governanca/scripts/remoto.test.sh`

**Interfaces:**
- Consumes: `governanca/config/equipe.yml` (handles para os convites).
- Produces: o remote `origin`, que as tasks 6 e 7 configuram.

- [ ] **Step 1: Confirmar a conta ativa**

```bash
gh auth status
gh auth switch --user gustavovfeitosa
gh api user --jq .login
```

Expected: `gustavovfeitosa`. Se sair `gustavovidal-tiktok`, PARE: essa conta é proibida neste projeto.

- [ ] **Step 2: Escrever o teste que falha**

```bash
# governanca/scripts/remoto.test.sh
set -euo pipefail
REPO="${1:?uso: remoto.test.sh ORG/REPO}"

gh repo view "$REPO" --json visibility --jq .visibility | grep -q PUBLIC \
  || { echo "FALHA: repo nao e publico"; exit 1; }

n=$(gh api "repos/$REPO/collaborators" --jq 'length')
[ "$n" -ge 4 ] || { echo "FALHA: $n colaboradores, esperados 4"; exit 1; }

gh api "repos/$REPO/branches/main/protection" --jq '.required_pull_request_reviews.required_approving_review_count' \
  | grep -q '^1$' || { echo "FALHA: main nao exige 1 aprovacao"; exit 1; }

gh api "repos/$REPO/branches/main/protection" --jq '.allow_force_pushes.enabled' \
  | grep -q '^false$' || { echo "FALHA: force push permitido"; exit 1; }

echo "OK: remoto configurado"
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `bash governanca/scripts/remoto.test.sh tra48-vertiportos/projeto-b1`
Expected: FAIL — o repo ainda não existe (`gh` retorna erro de not found)

- [ ] **Step 4: Criar a org**

Org não se cria por API. Abrir `https://github.com/organizations/plan` no navegador, escolher o plano Free, nome `tra48-vertiportos`. Confirmar:

```bash
gh api user/orgs --jq '.[].login'
```

Expected: a lista inclui `tra48-vertiportos`.

- [ ] **Step 5: Criar o repo e empurrar o histórico local**

```bash
cd ~/Documents/ITA/TRA-48_Projeto
gh repo create tra48-vertiportos/projeto-b1 --public \
  --description "TRA-48 Projeto B1: localizacao de vertiportos em Sao Paulo" \
  --source . --remote origin --push
```

- [ ] **Step 6: Convidar os três**

Um comando por handle, lidos de `equipe.yml`:

```bash
for h in $(grep '^\s*handle:' governanca/config/equipe.yml | sed 's/.*handle: *//' | grep -v gustavovfeitosa); do
  gh api -X PUT "repos/tra48-vertiportos/projeto-b1/collaborators/$h" -f permission=push
done
```

- [ ] **Step 7: Proteger a `main`**

Verificações obrigatórias ficam de fora aqui: os jobs de CI só existem no Plano 4, e exigir um check inexistente travaria todo merge. O Plano 4 acrescenta.

```bash
gh api -X PUT repos/tra48-vertiportos/projeto-b1/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "require_code_owner_reviews": true,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": true
}
JSON
```

- [ ] **Step 8: Rodar o teste e confirmar que passa**

Run: `bash governanca/scripts/remoto.test.sh tra48-vertiportos/projeto-b1`
Expected: `OK: remoto configurado`

- [ ] **Step 9: Commit**

```bash
git add governanca/scripts/remoto.test.sh
git commit -m "teste de conformidade do repositorio remoto"
git push
```

---

### Task 6: PR de fumaça que prova que a governança morde

Toda a Task 5 é configuração declarada. Configuração declarada e não exercitada é configuração que você descobre estar errada na véspera. Esta task exercita.

**Files:**
- Create: `docs/CHECK-GOVERNANCA.md`
- Test: o próprio PR é o teste.

- [ ] **Step 1: Abrir uma branch e um PR de teste**

```bash
git switch main && git pull
git switch -c gov/fumaca
printf '# Verificação de governança\n\nPR de fumaça: ver histórico do PR #1.\n' > docs/CHECK-GOVERNANCA.md
git add docs/CHECK-GOVERNANCA.md
git commit -m "pr de fumaca da governanca"
git push -u origin gov/fumaca
gh pr create --title "PR de fumaça" --body "Registros: (nenhum, PR de infraestrutura)" --draft
```

- [ ] **Step 2: Provar que push direto na `main` é recusado**

```bash
git switch main
printf 'teste\n' >> docs/CHECK-GOVERNANCA.md
git add -A && git commit -m "tentativa de push direto"
git push
```

Expected: FALHA, com mensagem de protected branch. Desfazer o commit local:

```bash
git reset --hard origin/main
```

Se o push **passar**, a proteção não está ativa: volte à Task 5 Step 7.

- [ ] **Step 3: Provar que merge sem aprovação é recusado**

```bash
gh pr ready
gh pr merge --squash
```

Expected: FALHA por falta de aprovação. Registre a mensagem exata.

- [ ] **Step 4: Pedir aprovação real a um integrante e mergear**

O outro integrante aprova pela interface. Depois:

```bash
gh pr merge --squash --delete-branch
git switch main && git pull
```

- [ ] **Step 5: Anotar o resultado dos três testes**

Substituir o conteúdo de `docs/CHECK-GOVERNANCA.md` pelo que de fato aconteceu, com a mensagem de erro de cada tentativa recusada. Isso é evidência de auditoria: mostra que a proteção foi verificada, não presumida.

- [ ] **Step 6: Commit pelo fluxo normal**

```bash
git switch -c gov/evidencia-fumaca
git add docs/CHECK-GOVERNANCA.md
git commit -m "evidencia dos testes de protecao da main"
git push -u origin gov/evidencia-fumaca
gh pr create --title "Evidência dos testes de proteção" --body "Registros: (infraestrutura)"
```

---

### Task 7: `CLAUDE.md` do repositório

O repo vai ser operado por quatro pessoas com assistentes de IA. As regras do enunciado precisam estar onde o assistente lê, não só onde o humano lê.

**Files:**
- Create: `CLAUDE.md` (na raiz do repo do grupo)
- Test: `governanca/scripts/claudemd.test.sh`

- [ ] **Step 1: Escrever o teste que falha**

```bash
# governanca/scripts/claudemd.test.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
C=CLAUDE.md
test -f "$C" || { echo "FALHA: CLAUDE.md ausente"; exit 1; }
for t in "nao aconteceu" "critica" "gustavovfeitosa" "dump.sql" "./gov" "R"; do
  grep -qi -- "$t" "$C" || { echo "FALHA: CLAUDE.md nao menciona '$t'"; exit 1; }
done
grep -qi 'tiktok' "$C" || { echo "FALHA: falta a proibicao explicita da conta"; exit 1; }
echo "OK: CLAUDE.md completo"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `bash governanca/scripts/claudemd.test.sh`
Expected: FAIL com "FALHA: CLAUDE.md ausente"

- [ ] **Step 3: Escrever o `CLAUDE.md`**

```markdown
# TRA-48 — Projeto B1: localização de vertiportos em São Paulo

Grupo de 4. Duas camadas avaliadas: **A** (modelo de Pesquisa Operacional, 55%) e
**B** (governança computável do próprio trabalho, 25% + comunicação).

## A regra que governa tudo

O que não estiver no banco de governança, não aconteceu. Toda decisão metodológica,
fonte, experimento e interação com IA vira registro via `./gov` **antes** do commit
que a materializa. O PR cita os IDs no campo `Registros:`.

## Uso de IA

Interação relevante com IA é registrada com `./gov ia`, e o campo de crítica humana
é obrigatório: o que estava errado, incompleto ou discutível na resposta. Registro
sem crítica é recusado pela CLI. Taxa de aceite integral é métrica pública do
projeto: aceitar tudo é sinal de ausência de revisão e será cobrado na arguição.
Não operar em modo automático: cada sugestão passa por leitura humana.

## Regras técnicas

- Linguagem do projeto: **R** (`app/`). Motor de governança: **Python 3** (`governanca/`).
- `governanca/projeto.duckdb` nunca é versionado. O versionado é `governanca/dump.sql`.
- Escrita no banco só via `./gov`. Leitura pelo assistente via MCP, só-leitura.
- Comentário de código: teto de 1 linha por commit no diff inteiro. Contexto vai no PR.
- Nada entra na `main` sem PR aprovado por integrante de outra frente.

## Conta GitHub

Este projeto usa **`gustavovfeitosa`**. A conta `gustavovidal-tiktok` NUNCA é usada
aqui: verificar com `gh auth status` antes de qualquer push ou PR.

## Ler antes de trabalhar

- `docs/GUIA-GIT.md` — fluxo branch → commit → PR
- `docs/superpowers/specs/2026-08-20-tra48-governanca-design.md` — desenho da camada B
- `~/Documents/ITA/TRA-48/Projeto_TRA48.pdf` — enunciado
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `bash governanca/scripts/claudemd.test.sh`
Expected: `OK: CLAUDE.md completo`

- [ ] **Step 5: Commit e PR**

```bash
git switch -c gov/claude-md
git add CLAUDE.md governanca/scripts/claudemd.test.sh
git commit -m "claude.md com as regras do enunciado e da conta"
git push -u origin gov/claude-md
gh pr create --title "CLAUDE.md do repositório" --body "Registros: (infraestrutura)"
```

---

### Task 8: Runner único dos testes de infraestrutura

Cinco scripts `.test.sh` espalhados só são rodados se houver um comando que roda todos. O Plano 4 chama este runner no CI.

**Files:**
- Create: `governanca/scripts/testes.sh`
- Test: ele próprio, mais a conferência de que cobre todos os `.test.sh`.

**Interfaces:**
- Produces: `governanca/scripts/testes.sh`, saída com código 0 se tudo passa. O job `governanca` do Plano 4 executa exatamente este comando.

- [ ] **Step 1: Escrever o runner**

```bash
# governanca/scripts/testes.sh
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

falhas=0
for t in $(find governanca -name '*.test.sh' | sort); do
  case "$t" in *remoto.test.sh) continue;; esac
  printf '%-50s' "$(basename "$t")"
  if bash "$t" >/tmp/tra48-teste.log 2>&1; then
    echo "PASSOU"
  else
    echo "FALHOU"
    sed 's/^/    /' /tmp/tra48-teste.log
    falhas=$((falhas+1))
  fi
done

[ "$falhas" -eq 0 ] || { echo; echo "$falhas teste(s) falharam"; exit 1; }
echo; echo "todos os testes de infraestrutura passaram"
```

`remoto.test.sh` é excluído porque depende de rede e de credencial, e roda à mão.

- [ ] **Step 2: Rodar e confirmar que todos passam**

Run: `bash governanca/scripts/testes.sh`
Expected: `todos os testes de infraestrutura passaram`

- [ ] **Step 3: Provar que o runner detecta falha**

```bash
mv governanca/config/equipe.yml /tmp/equipe.bak
bash governanca/scripts/testes.sh; echo "codigo de saida: $?"
mv /tmp/equipe.bak governanca/config/equipe.yml
```

Expected: `equipe.test.sh FALHOU` e código de saída 1. Um runner que nunca falha não é teste.

- [ ] **Step 4: Commit e PR**

```bash
git switch -c gov/runner-testes
git add governanca/scripts/testes.sh
git commit -m "runner unico dos testes de infraestrutura"
git push -u origin gov/runner-testes
gh pr create --title "Runner dos testes de infra" --body "Registros: (infraestrutura)"
```

---

## Critério de pronto do Plano 1

1. `bash governanca/scripts/testes.sh` passa.
2. `bash governanca/scripts/remoto.test.sh tra48-vertiportos/projeto-b1` passa.
3. `docs/CHECK-GOVERNANCA.md` registra as três tentativas recusadas, com as mensagens.
4. Os 4 integrantes constam como colaboradores e ao menos um deles já aprovou um PR.
5. Um integrante que nunca usou Git consegue, só com `docs/GUIA-GIT.md`, clonar, abrir branch, commitar e abrir PR.

O critério 5 é o único que exige um humano: peça a um dos três para executar o guia sem ajuda e anote onde ele travou. Onde travou, o guia está errado.
