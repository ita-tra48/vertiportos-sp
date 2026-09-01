raio_terra_m <- 6371008.8

letras_acentuadas <- paste0(
  "áàâãäéèêë",
  "íìîïóòôõö",
  "úùûüçñ"
)
letras_simples <- "aaaaaeeeeiiiiooooouuuucn"

sem_acento <- function(x) {
  toupper(chartr(letras_acentuadas, letras_simples, tolower(trimws(x))))
}

padroniza_nome <- function(x) {
  y <- chartr(letras_acentuadas, letras_simples, tolower(x))
  gsub("^_|_$", "", gsub("[^a-z0-9]+", "_", y))
}

numero_br <- function(x) {
  suppressWarnings(as.numeric(gsub(",", ".", trimws(x), fixed = TRUE)))
}

maior_dimensao_m <- function(x) {
  achados <- regmatches(x, gregexpr("[0-9]+(?:[,.][0-9]+)?", x))
  vapply(achados, function(v) {
    if (length(v) == 0) {
      return(NA_real_)
    }
    max(numero_br(v), na.rm = TRUE)
  }, numeric(1))
}

distancia_m <- function(lat1, lon1, lat2, lon2) {
  rad <- pi / 180
  dlat <- (lat2 - lat1) * rad
  dlon <- (lon2 - lon1) * rad
  a <- sin(dlat / 2)^2 +
    cos(lat1 * rad) * cos(lat2 * rad) * sin(dlon / 2)^2
  2 * raio_terra_m * asin(pmin(1, sqrt(a)))
}

agrupa_por_proximidade <- function(dados, limiar_m) {
  n <- nrow(dados)
  chefe <- rep(NA_character_, n)
  for (i in seq_len(n)) {
    if (!is.na(chefe[i])) {
      next
    }
    chefe[i] <- dados$id_candidato[i]
    j <- seq_len(n)
    j <- j[j > i & is.na(chefe[j])]
    if (length(j) == 0) {
      next
    }
    d <- distancia_m(dados$lat[i], dados$lon[i], dados$lat[j], dados$lon[j])
    chefe[j[d < limiar_m]] <- dados$id_candidato[i]
  }
  chefe
}
