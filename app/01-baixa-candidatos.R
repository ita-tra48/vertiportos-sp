source("app/00-pacotes.R")

url_anac_helipontos <- paste0(
  "https://sistemas.anac.gov.br/dadosabertos/Aerodromos/",
  "Aer%C3%B3dromos%20Privados/Lista%20de%20aer%C3%B3dromos%20privados/",
  "Heliponto/Helipontos.csv"
)

url_geosampa_estacoes <- paste0(
  "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
  "?service=WFS&version=1.0.0&request=GetFeature",
  "&typeName=geoportal:estacao_metro",
  "&outputFormat=application/json&srsName=EPSG:4326"
)

tentativas <- 4

baixa <- function(url, destino) {
  if (file.exists(destino)) {
    message(sprintf("ja existe, mantido: %s", destino))
    return(invisible(destino))
  }
  for (tentativa in seq_len(tentativas)) {
    ok <- tryCatch({
      utils::download.file(url, destino, mode = "wb", quiet = TRUE)
      TRUE
    }, error = function(e) FALSE, warning = function(w) FALSE)
    if (ok && file.exists(destino) && file.size(destino) > 0) {
      message(sprintf("baixado: %s (%s bytes)", destino, file.size(destino)))
      return(invisible(destino))
    }
    unlink(destino)
    Sys.sleep(2 * tentativa)
  }
  stop(sprintf("falha ao baixar apos %d tentativas: %s", tentativas, url))
}

dir.create("dados/bruto", showWarnings = FALSE, recursive = TRUE)
baixa(url_anac_helipontos, "dados/bruto/anac_helipontos.csv")
baixa(url_geosampa_estacoes, "dados/bruto/geosampa_estacao_metro.json")
