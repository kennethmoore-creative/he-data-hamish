"""
Scrapes the institution list from ComparED (https://www.compared.edu.au/browse-institutions).

The browse-institutions page is an Angular single-page app — its HTML is empty
until JavaScript runs, so BeautifulSoup can't parse institution names directly
off that page. Instead, the app itself pulls institution data from a JSON API
(https://api.compared.edu.au/institutions/), which is what this script queries.

The API returns all institutions (161 as of writing), including ones with no
outcome data. The page's default view only *displays* institutions that have
at least one undergraduate metric (this matches the site's own default filter
logic, reverse-engineered from its JS bundle) — that default view is what
gives the commonly cited count of 135 institutions.

Each institution's undergraduate outcome percentages (as shown on its
individual /institution/<alias>/undergraduate page) are also present in this
same bulk response, under undergraduate.highlights — no separate per-
institution scrape is needed. See HIGHLIGHT_ALIASES below for which highlight
aliases map to which output columns.

Output: data/compared-institutions.csv
"""

import csv
import time

import requests

API_URL = "https://api.compared.edu.au/institutions/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
TIMEOUT = 30
MAX_RETRIES = 3
OUT_PATH = "data/compared-institutions.csv"

# undergraduate.highlights[].alias -> output CSV column
HIGHLIGHT_ALIASES = {
    "educational-experience": "pct_positive_overall_experience",
    "skills-development": "pct_positive_skills_development",
    "full-time-employment": "pct_found_full_time_employment",
}


def fetch(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            print(f"  attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts")


def has_undergraduate_data(inst):
    """Mirrors ComparED's default browse-institutions filter (study level = undergraduate)."""
    u = inst.get("undergraduate") or {}
    return (
        u.get("graduateEmploymentCount", -2) > -2
        or u.get("graduateSatisfactionCount", -2) > -2
        or u.get("studentExperienceCount", -2) > -2
    )


def get_highlight_scores(inst):
    """Undergraduate outcome percentages, keyed by output column name.

    -2.0 is the API's sentinel for "no data" and is written as an empty
    string so it comes through as NA when read with readr::read_csv().
    """
    highlights = (inst.get("undergraduate") or {}).get("highlights") or []
    by_alias = {h.get("alias"): h.get("score") for h in highlights}
    return {
        col: "" if by_alias.get(alias) is None or by_alias[alias] <= -2.0 else by_alias[alias]
        for alias, col in HIGHLIGHT_ALIASES.items()
    }


def main():
    print(f"Fetching institution list from {API_URL} ...")
    institutions = fetch(API_URL)
    print(f"  {len(institutions)} institutions returned by API")

    shown = [i for i in institutions if has_undergraduate_data(i)]
    shown.sort(key=lambda i: i["title"].upper())
    print(f"  {len(shown)} institutions match the site's default browse view")

    columns = ["title", "type", "location", "website_url", *HIGHLIGHT_ALIASES.values()]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for inst in shown:
            scores = get_highlight_scores(inst)
            writer.writerow(
                [
                    inst["title"],
                    inst.get("type", ""),
                    ";".join(inst.get("location") or []),
                    inst.get("websiteUrl", ""),
                    *(scores[col] for col in HIGHLIGHT_ALIASES.values()),
                ]
            )

    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    main()
