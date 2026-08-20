# Prompt de retomada

Abrir aba nova no terminal e rodar:

    cd ~/Documents/ITA/TRA-48_Projeto && claude

Colar:

---
Projeto TRA-48 (ITA, 2º sem/2026): "Localização de vertiportos em São Paulo".
Grupo de 4, eu incluído. Leia primeiro, nesta ordem:

1. ~/Documents/ITA/TRA-48/Projeto_TRA48.pdf  (regras do Projeto B1 — pdftotext -layout)
2. ~/Documents/ITA/Plano de Disciplina TRA-48 2026.pdf
3. CLAUDE.md deste repo
4. docs/superpowers/specs/*-tra48-governanca-design.md  (o design aprovado)

Contexto do que já foi decidido em sessão anterior (19-20/08/2026):

- O projeto tem 2 camadas avaliadas: A = substantiva (o modelo de PO) e
  B = metodológica (governança computável do próprio trabalho, com IA).
- Estamos construindo a infra da camada B do zero. O PDF diz que o professor
  entrega um repositório-modelo pronto; ele NÃO chegou até 20/08. Se chegar,
  migramos os registros por script.
- Abordagem aprovada: motor `gov.py` em Python + DuckDB como fonte de verdade,
  `app/` 100% em R, site estático gerado do banco e publicado no GitHub Pages.
- Correção deliberada ao organograma do professor: `projeto.duckdb` NÃO é
  versionado no git (binário, 4 pessoas, conflito garantido). O versionado é
  `governanca/dump.sql`, append-only, e o `./gov` reconstrói o banco dele.
- GitHub: org nova do grupo, repo público. Conta a usar é `gustavovfeitosa`.
  NUNCA usar a conta `gustavovidal-tiktok` neste projeto.
- Linguagem da disciplina é R. Comentário de código: quase zero (ver
  ~/.claude/CLAUDE.md); o contexto vai no PR.

Regra dura do projeto: "o que não estiver no banco, não aconteceu". Toda decisão
metodológica, fonte, experimento e interação com IA vira registro via `./gov`
antes do commit. Interação com IA sem o campo de crítica humana é inválida.

Comece rodando `./gov status` (ou, se a infra ainda não existir, leia o plano em
docs/superpowers/plans/ e continue de onde parou).
---
