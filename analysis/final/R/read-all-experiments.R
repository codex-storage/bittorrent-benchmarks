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

merge_experiments <- function(set_1, set_2, prefix) {
  maxid <- max(as.integer(sub(pattern = 'e', '', ls(deluge))))
  merged <- list()

  for (set_1_id in ls(set_1)) {
    merged[[set_1_id]] <- set_1[[set_1_id]]
  }

  for (set_2_id in ls(set_2)) {
    merged[[paste0(prefix, set_2_id)]] <- set_2[[set_2_id]]
  }

  merged
}
