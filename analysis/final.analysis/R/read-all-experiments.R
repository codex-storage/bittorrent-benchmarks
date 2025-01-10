read_all_experiments <- function(base_path, skip_incomplete = TRUE) {
  roots <- list.files(base_path,
                      include.dirs = TRUE, no.. = TRUE, full.names = TRUE)

  experiments <- lapply(roots, read_single_experiment)
  names(experiments) <- sapply(roots, basename)

  # Validates that no experiment has missing data.
  key_sets <- lapply(experiments, ls) |> unique()
  # Selects the largest keyset which is presumably the most complete.
  key_set <- key_sets[[order(sapply(key_sets, length), decreasing = TRUE)[1]]]

  # Discards any experiment that doesn't have all keys.
  experiments <- lapply(experiments, function(experiment) {
    if (!(all(key_set %in% names(experiment)))) {
      warning(glue::glue('Experiment {experiment$experiment_id} is missing ',
                          'some keys and will be discarded.'))
      NULL
    } else {
      experiment
    }
  })

  experiments[!is.null(experiments)]
}
