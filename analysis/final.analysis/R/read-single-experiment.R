read_single_experiment <- function(experiment_folder) {
  # This is a structural assumption: the base folder for the experiment
  # corresponds to its ID.
  experiment_id <- basename(experiment_folder)
  print(glue::glue('Reading experiment {experiment_id}'))

  meta <- jsonlite::read_json(.lookup_experiment_config(experiment_folder))
  table_files <- list.files(path = experiment_folder, '\\.csv$')
  data <- lapply(table_files, function(table_file) {
    read_csv(
      file.path(experiment_folder, table_file),
      show_col_types = FALSE
    ) |>
      mutate(
        experiment_id = !!experiment_id
      ) |>
      arrange(timestamp)
  })

  names(data) <- gsub('(\\..*)$', '', table_files)
  data$meta <- meta
  data$experiment_id <- experiment_id

  data
}

.lookup_experiment_config <- function(experiment_folder) {
  candidates <- list.files(path = experiment_folder,
                           pattern = '_experiment_config_log_entry.jsonl$')

  if (length(candidates) != 1) {
    stop(glue::glue(
      'Cannot establish the correct config file at {experiment_folder}.'))
  }

  file.path(experiment_folder, candidates)
}
