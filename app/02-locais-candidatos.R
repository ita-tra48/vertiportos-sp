source("app/00-pacotes.R")
source("app/R/candidatos.R")

municipio_alvo <- "SAO PAULO"
uf_alvo <- "SAO PAULO"
mtow_evtol_t <- 3.2
tlof_min_m <- 18
limiar_agrupamento_m <- 150

helipontos_bruto <- read_delim(
  "dados/bruto/anac_helipontos.csv",
  delim = ";", skip = 1, col_types = cols(.default = col_character()),
  locale = locale(encoding = "latin1")
)
names(helipontos_bruto) <- padroniza_nome(names(helipontos_bruto))

helipontos <- helipontos_bruto |>
  filter(
    sem_acento(municipio) == municipio_alvo,
    sem_acento(uf) == uf_alvo
  ) |>
  transmute(
    camada = "heliponto",
    infra_aeronautica = "existente",
    nome = trimws(nome),
    fonte = "anac_helipontos",
    fonte_id = trimws(ciad),
    codigo_oaci = trimws(codigo_oaci),
    lat = numero_br(latgeopoint),
    lon = numero_br(longeopoint),
    tipo_local = trimws(tipo),
    tlof_m = maior_dimensao_m(dimensoes),
    resistencia_t = numero_br(resistencia_do_pavimento),
    op_diurna = trimws(operacao_diurna),
    op_noturna = trimws(operacao_noturna)
  )

estacoes_bruto <- fromJSON(
  "dados/bruto/geosampa_estacao_metro.json",
  simplifyVector = FALSE
)

estacoes <- bind_rows(lapply(estacoes_bruto$features, function(f) {
  tibble(
    camada = "estacao_transporte",
    infra_aeronautica = "inexistente",
    nome = trimws(f$properties$nm_estacao_metro_trem),
    fonte = "geosampa_estacao_metro",
    fonte_id = as.character(f$properties$cd_identificador),
    codigo_oaci = NA_character_,
    lat = f$geometry$coordinates[[2]],
    lon = f$geometry$coordinates[[1]],
    tipo_local = paste(
      f$properties$nm_empresa_metro_trem,
      f$properties$nm_linha_metro_trem
    ),
    tlof_m = NA_real_,
    resistencia_t = NA_real_,
    op_diurna = NA_character_,
    op_noturna = NA_character_,
    situacao = trimws(f$properties$tx_situacao_metro_trem)
  )
})) |>
  filter(situacao == "OPERANDO") |>
  select(-situacao)

candidatos <- bind_rows(helipontos, estacoes) |>
  filter(!is.na(lat), !is.na(lon)) |>
  arrange(desc(camada == "heliponto"), nome) |>
  mutate(id_candidato = sprintf("CAN-%04d", row_number()))

candidatos$agrupamento_id <- agrupa_por_proximidade(
  candidatos, limiar_agrupamento_m
)

candidatos <- candidatos |>
  mutate(
    motivo_exclusao = case_when(
      camada != "heliponto" ~ NA_character_,
      is.na(resistencia_t) ~ "resistencia de pavimento ausente no cadastro",
      resistencia_t < mtow_evtol_t ~
        "resistencia cadastral abaixo do mtow evtol de referencia",
      is.na(tlof_m) ~ "dimensao da area de pouso ausente no cadastro",
      tlof_m < tlof_min_m ~ "area de pouso abaixo do tlof minimo adotado",
      coalesce(op_diurna, "") != "VFR" ~ "sem operacao diurna vfr registrada",
      TRUE ~ NA_character_
    ),
    apto_triagem = is.na(motivo_exclusao),
    representante_agrupamento = agrupamento_id == id_candidato
  ) |>
  select(
    id_candidato, camada, infra_aeronautica, nome, lat, lon, tipo_local,
    tlof_m, resistencia_t, op_diurna, op_noturna, apto_triagem,
    motivo_exclusao, agrupamento_id, representante_agrupamento,
    fonte, fonte_id, codigo_oaci
  )

dir.create("dados/tratado", showWarnings = FALSE, recursive = TRUE)
write_csv(candidatos, "dados/tratado/locais_candidatos.csv", na = "")

message(sprintf(
  "sitios: %d | aptos na triagem: %d | agrupamentos a %d m: %d",
  nrow(candidatos), sum(candidatos$apto_triagem), limiar_agrupamento_m,
  sum(candidatos$representante_agrupamento)
))
print(count(candidatos, camada, apto_triagem))
