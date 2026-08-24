# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing codebase answers this: the site is static HTML/CSS emitted by
`governanca/scripts/site_gov.py` (Python 3, stdlib only — no template engine),
read from a DuckDB database and published to GitHub Pages by a GitHub Actions
workflow. **Hard constraint: no network dependency of any kind** — no CDN, no
remote font, no remote image, no fetch. The site is navigated live during a
graded oral defence and a network failure must not degrade it. The only
permitted external-looking string is the SVG namespace URL.

## Users

**Primary — the professors.** Marcelo Xavier Guterres and Mayara Condé Rocha
Murça, who assess the project. The assignment states the site, not a prepared
presentation, is the starting point of every progress meeting ("o ponto de
partida é o site do grupo, não uma apresentação preparada para a ocasião"), and
that part of the final oral defence is conducted by navigating it. They arrive
knowing the assignment but not this group's conventions, and they are looking
for specific answers: why is this parameter value this, who decided it, which
script produced which figure, which conclusions still lack a supporting
experiment, and where did the group disagree with the AI.

**Secondary — the four group members**, during the five weeks of work. They use
it to see what is unlinked, what is overdue, and what still has no owner.

**Secondary — the other groups in the class.** Every group attacks the same
problem with the same base data, and the term ends with a comparative panel of
all groups' results side by side. Our site will be opened by people who do not
know our conventions and are looking for our numbers to compare against theirs.

**Secondary — outside readers, after the course.** The repository is public and
the work is intended to survive as something its author can show. The entry
page therefore has to explain what this is to someone with no context.

## Product Purpose

Make the *process* of an engineering project auditable, not just its result.
The assignment's rule is absolute: "O que não estiver no banco, não aconteceu."
Every methodological decision, data source, experiment and AI interaction is
recorded while the work happens, linked into a graph, scored by automatic audit
metrics, and published as a site generated from the database. Success is a
professor being able to answer, in one click, a question that would normally
require archaeology through e-mail.

## Positioning

The site is not documentation written after the fact — it is a **faithful
mirror of a database**, regenerated from scratch on every push by CI. Nothing
on it is hand-written, so nothing on it can be flattering. The audit publishes
the group's own weaknesses: orphan records, stale blockers, tasks with no
owner, and an AI acceptance rate that reads as a red flag when it is too high.
A neighbouring project could copy the layout but not this property, because the
property is structural.

## Operating Context

- **Two viewing situations, both required.** Projected in a classroom during
  the oral defence, read by a room; and on a professor's own laptop at close
  range during progress meetings. Type scale, contrast and table density must
  hold in both.
- Three scheduled progress meetings (26/08, 09/09, one on demand) plus the
  final defence on 23/09/2026.
- Deliverables also include a PDF engineering report and a slide deck; the site
  is the third, and it is the one that is regenerated rather than authored.
- The database is rebuilt from an append-only `governanca/dump.sql`; the binary
  database and the generated site are both gitignored.

## Capabilities and Constraints

- Nine record types, in Portuguese and used as-is on screen: metas, tarefas,
  pendências, decisões, fontes, arquivos, referências, experimentos, and
  interações com IA.
- Nine typed graph relations: `tem`, `atende`, `usa`, `produz`, `justifica`,
  `apoia`, `deriva`, `bloqueia`, `informa`. Each has fixed allowed endpoint
  types, validated on write.
- Eight pages, fixed by the assignment: Estado, Grafo executivo, Trilha,
  Tarefas e pendências, Interações com IA, Experimentos, Resultados,
  Reprodutibilidade.
- Four audit metric groups: rastreabilidade, cadência, higiene, postura crítica.
  Plus a pass/fail seal.
- **Determinism is required**: two regenerations of the same database must
  produce byte-identical files, so that a diff of the site is signal.
- All record text is free text typed by a group member and must be escaped;
  it can be long, empty, or absent.
- Early in the term most tables are empty or nearly so. Empty is the normal
  state for the first weeks, not an edge case.

## Brand Commitments

- Language is Portuguese (pt-BR) throughout.
- Institution is Instituto Tecnológico de Aeronáutica (ITA); course is TRA-48,
  "Inteligência Analítica: Dados, Modelos e Decisões", 2nd term 2026.
- No ITA logo or institutional mark is on hand, and none may be fabricated.
- GitHub organisation: `Projeto-TRA-48-Grupo-1`.

## Evidence on Hand

- The assignment PDF (`~/Documents/ITA/TRA-48/Projeto_TRA48.pdf`) and the course
  syllabus, both read.
- The subject matter: locating vertiports for urban air mobility in São Paulo.
  The mandatory base dataset is the São Paulo Metro Origin-Destination survey
  (last wave 2017).
- **Not on hand and not to be invented:** any model results, chosen vertiport
  locations, captured-demand figures, objective-function values, maps, or
  literature citations. The Operations Research layer has not been built yet.
  Every number the site shows must come from the database, and the database is
  currently empty. The Resultados page in particular must be honest that
  nothing has been produced yet rather than showing placeholder figures.
- The three other group members' names and GitHub usernames are not yet known.

## Product Principles

1. **The database is the only source.** If a number is on the site, a script
   put it there. Nothing is hand-authored, so nothing can be quietly improved.
2. **Publish the weaknesses.** Orphan records, stale blockers and a suspicious
   AI acceptance rate are shown prominently, not buried. Honesty about a
   limitation scores better than an unqualified claim, by the assignment's own
   grading criteria.
3. **Answer the provenance question in one click.** Every record must be
   reachable from the thing that depends on it, in both directions.
4. **Empty is a first-class state.** The site is born empty and fills over five
   weeks; it must read as deliberate and legible at every point on that curve.
5. **Legible at three metres and at fifty centimetres.** Both viewing distances
   are graded situations.

## Accessibility & Inclusion

No institution-specific standard was established. Self-imposed floor, driven by
the projector requirement: text contrast comfortably above WCAG AA, no meaning
carried by colour alone (the audit seal and the graph's entity types must both
survive being read in greyscale or by a colour-blind reader), full keyboard
navigability, and respect for `prefers-reduced-motion`.
