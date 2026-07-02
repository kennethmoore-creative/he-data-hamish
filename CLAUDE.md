# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Various higher education data projects, developed in R using the tidyverse. The user runs code interactively in **Positron** (not RStudio).

## Running scripts

Scripts are run interactively in Positron:
- `Ctrl+Enter` — run current line or selection in the R console
- `Ctrl+Shift+Enter` — source the entire active script

There is no build step, test suite, or linter configured.

## Structure

- `scripts/` — R scripts for importing and processing data, plus Python scripts for scraping data that feeds into R (see "R-Python pipeline" below)
- `data/` — raw/source data files (Excel spreadsheets, CSVs produced by scrapers); tracked in git but not always committed
- `output/` — generated exports (e.g. `.xlsx` written by R via `writexl`); create with `dir.create("output")` if missing rather than assuming it exists

## Key conventions

- Use `tidyverse` functions throughout; `readxl` for Excel imports, `writexl::write_xlsx()` for Excel exports
- Excel source files may be open in Excel during development — close them before sourcing scripts to avoid R session crashes
- The data folder may contain Excel lock files (`~$filename.xlsx`) when a spreadsheet is open; these are harmless but can cause `readxl` to crash R if the main file is also locked — don't commit `~$` files

## R-Python pipeline

Some data isn't available as a clean download and needs scraping. Pattern used in this repo:

1. A Python script in `scripts/` scrapes an external source and writes a plain CSV into `data/` (e.g. `scrape_compared_institutions.py` → `data/compared-institutions.csv`). Run it manually (`py scripts/<name>.py`) whenever the source data needs refreshing — it's not invoked automatically from R.
2. The R script in `scripts/` (`import-data.R`) reads that CSV with `read_csv()` alongside the native Excel sources, and does the joining/matching/analysis in R, since that's where the user is most comfortable working.

**Before writing a new scraper**, check the target site's actual structure first rather than defaulting to BeautifulSoup: fetch the raw HTML and see whether the data is present in static markup, or whether it's a JS-rendered SPA (React/Angular/Vue) with a near-empty HTML shell. If it's a SPA, don't try to parse the shell — grep its JS bundles for the API base URL/endpoints it calls itself, and hit that JSON API directly with `requests`. Only reach for BeautifulSoup once the target HTML is confirmed to contain the data server-side.

**Fuzzy-matching institution names** across sources (e.g. matching a scraped name list against a rubric spreadsheet): prefer normalize-then-exact-match over a general fuzzy-distance library. Normalize both sides (trim/squish whitespace, handle non-breaking spaces, lowercase, strip a leading "The "), exact-match on the normalized strings, and hardcode any remaining known mismatches in a small manual override tibble. This is more auditable than a distance-threshold matcher and avoids the risk of a fuzzy matcher wrongly conflating distinct-but-similarly-named institutions (e.g. "University of Queensland" vs "Queensland University of Technology"). Only reach for a package like `stringdist` if the number of unresolved mismatches is too large to hand-verify.
