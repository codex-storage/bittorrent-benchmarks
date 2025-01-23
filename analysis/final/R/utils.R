drop_nulls <- function(a_list) {
  a_copy <- a_list[!is.null(a_list)]
  a_copy
}
