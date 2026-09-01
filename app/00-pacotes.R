pacotes <- c("readr", "dplyr", "jsonlite")

faltando <- setdiff(pacotes, rownames(installed.packages()))
if (length(faltando) > 0) {
  stop(sprintf("pacotes ausentes: %s", paste(faltando, collapse = ", ")))
}

invisible(lapply(pacotes, library, character.only = TRUE))
