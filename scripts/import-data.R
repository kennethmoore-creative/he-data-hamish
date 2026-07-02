# setup

library("tidyverse")

# Get excel data

university_rating <- readxl::read_excel(
  "data/Univerity Rating SDG Rubric MASTER.xlsx",
  sheet = "SUMMARY",
  skip = 1
)

# Get ComparED institution list
# Produced by scripts/scrape_compared_institutions.py — run that script first
# to (re)generate data/compared-institutions.csv

compared_institutions <- read_csv("data/compared-institutions.csv")

# Match compared_institutions against university_rating
#
# Names are formatted differently between the two sources (whitespace,
# a non-breaking space in one HEI value, a leading "The " on some CSV
# titles), so a plain == won't line them up. Normalize both sides, then
# resolve a small number of known name-format mismatches via an explicit
# override table rather than a fuzzy/edit-distance matcher — with only 42
# HEIs, a hardcoded lookup is easier to audit and can't accidentally
# conflate distinct institutions (e.g. University of Queensland vs
# Queensland University of Technology).

normalize_name <- function(x) {
  x |>
    str_replace_all("[  ]", " ") |>
    str_squish() |>
    str_to_lower() |>
    str_remove("^the ")
}

university_rating_named <- university_rating |>
  filter(!str_detect(HEI, regex("total", ignore_case = TRUE))) |>
  mutate(hei_norm = normalize_name(HEI))

manual_overrides <- tribble(
  ~title_norm, ~hei_norm,
  "cquniversity australia", "cq university",
  "federation university australia", "federation university of australia",
  "torrens university", "torrens university australia"
)

compared_institutions_norm <- compared_institutions |>
  mutate(title_norm = normalize_name(title)) |>
  left_join(manual_overrides, by = "title_norm") |>
  mutate(hei_norm = coalesce(hei_norm, title_norm))

matched_institutions <- compared_institutions_norm |>
  filter(hei_norm %in% university_rating_named$hei_norm) |>
  select(-title_norm, -hei_norm)

# Verification — confirm all 42 HEIs were accounted for
nrow(matched_institutions)
setdiff(university_rating_named$hei_norm, compared_institutions_norm$hei_norm)

# Add the three ComparED score columns onto university_rating
#
# Joins on hei_norm, the same normalized-name key used to build
# matched_institutions above (compared_institutions_norm holds the same rows
# as matched_institutions plus that key, so this reuses the existing match
# rather than re-deriving it).

university_rating_scores <- university_rating_named |>
  left_join(
    compared_institutions_norm |>
      select(
        hei_norm,
        pct_positive_overall_experience,
        pct_positive_skills_development,
        pct_found_full_time_employment
      ),
    by = "hei_norm"
  ) |>
  select(-hei_norm)

# Verification — every row should have all three scores populated
nrow(university_rating_scores)
sum(is.na(university_rating_scores$pct_positive_overall_experience) |
      is.na(university_rating_scores$pct_positive_skills_development) |
      is.na(university_rating_scores$pct_found_full_time_employment))

# Export university_rating_scores to xlsx

if (!dir.exists("output")) dir.create("output")
writexl::write_xlsx(university_rating_scores, "output/university_rating_scores.xlsx")
