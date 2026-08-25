CREATE TABLE IF NOT EXISTS evento (
    evento_id   TEXT PRIMARY KEY,
    ts          TIMESTAMP NOT NULL,
    autor       TEXT NOT NULL,
    tipo        TEXT NOT NULL,
    entidade_id TEXT NOT NULL,
    payload     JSON NOT NULL
);

CREATE OR REPLACE VIEW no AS
SELECT evento_id, ts, autor, tipo, entidade_id, payload
FROM (
    SELECT *, row_number() OVER (
               PARTITION BY entidade_id ORDER BY ts DESC, evento_id DESC) AS rn
    FROM evento WHERE tipo <> 'aresta'
) WHERE rn = 1;

CREATE OR REPLACE VIEW criacao AS
SELECT entidade_id,
       min(ts)              AS criado_em,
       arg_min(autor, ts)   AS criado_por
FROM evento WHERE tipo <> 'aresta'
GROUP BY entidade_id;

CREATE OR REPLACE VIEW aresta AS
SELECT evento_id, ts, autor,
       entidade_id          AS origem,
       payload->>'relacao'  AS relacao,
       payload->>'destino'  AS destino
FROM evento WHERE tipo = 'aresta';

CREATE OR REPLACE VIEW meta AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por, n.autor AS autor_ult,
       n.payload->>'titulo' AS titulo,
       n.payload->>'desc'   AS descricao,
       coalesce(n.payload->>'status', 'aberta') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'meta';

CREATE OR REPLACE VIEW tarefa AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS titulo,
       n.payload->>'resp'   AS resp,
       try_cast(n.payload->>'prazo' AS DATE) AS prazo,
       coalesce(n.payload->>'status', 'aberta') AS status,
       n.payload->>'branch' AS branch
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'tarefa';

CREATE OR REPLACE VIEW pendencia AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo'    AS titulo,
       n.payload->>'resolucao' AS resolucao,
       coalesce(n.payload->>'status', 'aberta') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'pendencia';

CREATE OR REPLACE VIEW decisao AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS titulo,
       n.payload->>'just'   AS justificativa,
       n.payload->'alt'     AS alternativas,
       coalesce(n.payload->>'status', 'vigente') AS status
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'decisao';

CREATE OR REPLACE VIEW fonte AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo'     AS nome,
       n.payload->>'origem'     AS origem,
       n.payload->>'formato'    AS formato,
       n.payload->>'cobertura'  AS cobertura,
       n.payload->>'limitacoes' AS limitacoes
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'fonte';

CREATE OR REPLACE VIEW arquivo AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS caminho,
       n.payload->>'desc'   AS descricao
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'arquivo';

CREATE OR REPLACE VIEW referencia AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'titulo' AS citacao,
       n.payload->>'url'    AS url,
       n.payload->>'doi'    AS doi
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'referencia';

CREATE OR REPLACE VIEW experimento AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'variante'  AS variante,
       n.payload->'p'          AS parametros,
       n.payload->>'commit'    AS commit_sha,
       try_cast(n.payload->>'obj'   AS DOUBLE) AS obj,
       try_cast(n.payload->>'gap'   AS DOUBLE) AS gap,
       try_cast(n.payload->>'tempo' AS DOUBLE) AS tempo_s,
       n.payload->>'hipotese'  AS hipotese,
       n.payload->>'conclusao' AS conclusao
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'experimento';

CREATE OR REPLACE VIEW ia AS
SELECT n.entidade_id AS id, c.criado_em, c.criado_por,
       n.payload->>'proposito' AS proposito,
       n.payload->>'modelo'    AS modelo,
       n.payload->>'pedido'    AS pedido,
       n.payload->>'retorno'   AS retorno,
       n.payload->>'aceito'    AS aceito,
       n.payload->>'critica'   AS critica
FROM no n JOIN criacao c USING (entidade_id) WHERE n.tipo = 'ia';
