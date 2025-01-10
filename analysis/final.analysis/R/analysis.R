extract_repetitions <- function(deluge_torrent_download) {
  deluge_torrent_download |>
    mutate(
      temp = str_remove(torrent_name, '^dataset-'),
      seed_set = as.numeric(str_extract(temp, '^\\d+')),
      run = as.numeric(str_extract(temp, '\\d+$'))
    ) |>
    rename(piece = value) |>
    select(-temp, -name)
}

compute_pieces <- function(deluge_torrent_download, n_pieces) {
  deluge_torrent_download |>
    group_by(node, seed_set, run) |>
    arrange(timestamp) |>
    mutate(
      piece_count = seq_along(timestamp)
    ) |>
    ungroup() |>
    mutate(completed = piece_count / n_pieces)
}

check_incomplete_downloads <- function(deluge_torrent_download, n_pieces) {
  incomplete_downloads <- downloads |>
    group_by(node, seed_set, run) |>
    count() |>
    ungroup() |>
    filter(n != n_pieces)

  nrow(incomplete_downloads) == 0
}

check_mismatching_repetitions <- function(deluge_torrent_download, repetitions) {
  mismatching_repetitions <- downloads |>
    select(seed_set, node, run) |>
    distinct() |>
    group_by(seed_set, node) |>
    count() |>
    filter(n != repetitions)

  nrow(mismatching_repetitions) == 0
}

compute_download_times <- function(meta, request_event, deluge_torrent_download, group_id) {
  n_leechers <- meta$nodes$network_size - meta$seeders

  download_start <- request_event |>
    select(-request_id) |>
    filter(name == 'leech', type == 'RequestEventType.end') |>
    mutate(
      # We didn't log those on the runner side so I have to reconstruct them.
      run = rep(rep(
        1:meta$repetitions - 1,
        each = n_leechers), times=meta$seeder_sets),
      seed_set = rep(
        1:meta$seeder_sets - 1,
        each = n_leechers * meta$repetitions),
    ) |>
    transmute(node = destination, run, seed_set, seed_request_time = timestamp)

  download_times <- deluge_torrent_download |>
    # FIXME remove this once we fix the chart
    mutate(node = sub(pattern = glue::glue('-{group_id}$'), replacement = '', x = node)) |>
    left_join(download_start, by = c('node', 'run', 'seed_set')) |>
    mutate(
      elapsed_download_time = as.numeric(timestamp - seed_request_time)
    ) |>
    group_by(node, run, seed_set) |>
    mutate(lookup_time = as.numeric(min(timestamp) - seed_request_time)) |>
    ungroup()

  if (nrow(download_times |>
           filter(elapsed_download_time < 0 | lookup_time < 0)) > 0) {
    stop('Calculation for download times contains negative numbers')
  }

  download_times
}

check_seeder_count <- function(download_times, seeders) {
  mismatching_seeders <- download_times |>
    filter(is.na(seed_request_time)) |>
    select(node, seed_set, run) |>
    distinct() |>
    group_by(seed_set, run) |>
    count() |>
    filter(n != seeders)

  nrow(mismatching_seeders) == 0
}

download_time_stats <- function(download_times) {
  download_times |>
    filter(!is.na(elapsed_download_time)) |>
    group_by(piece_count, completed) |>
    summarise(
      mean = mean(elapsed_download_time),
      median = median(elapsed_download_time),
      max = max(elapsed_download_time),
      min = min(elapsed_download_time),
      p90 = quantile(elapsed_download_time, p = 0.95),
      p10 = quantile(elapsed_download_time, p = 0.05),
      .groups = 'drop'
    )
}

