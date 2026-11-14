# Python script for scraping raw play-by-play and other data using the chickenstats library

from pathlib import Path

import polars as pl

from chickenstats.chicken_nhl import Scraper, Season

# Generating a list of years to scrape
years = list(range(2024, 2009, -1))

# Folders for saving the files
SAVE_FOLDER = Path("./raw")
sub_folders = ["pbp", "stats", "lines", "team_stats", "scrapes"]

for sub_folder in sub_folders:
    (SAVE_FOLDER / sub_folder).mkdir(parents=True, exist_ok=True)

# Iterate through the years
for year in years:
    season = Season(year)

    # Only finished games have complete reports
    sched = season.schedule().filter(pl.col("game_state") == "OFF")

    game_ids = sched.get_column("game_id").unique(maintain_order=True).to_list()

    scraper = Scraper(game_ids)

    # Scrape the play by play for the year
    scraper.play_by_play.write_csv(SAVE_FOLDER / "pbp" / f"pbp_{year}.csv")

    # Keep the raw data, so Scraper.load can rebuild the aggregations without scraping again
    scraper.save(SAVE_FOLDER / "scrapes" / str(year))

    # Game-level stats, split by strength state
    scraper.prep_stats()
    scraper.stats.write_csv(SAVE_FOLDER / "stats" / f"stats_{year}.csv")

    # Game-level forward lines, split by strength state
    scraper.prep_lines()
    scraper.lines.write_csv(SAVE_FOLDER / "lines" / f"lines_{year}.csv")

    # Game-level team stats, split by strength state
    scraper.prep_team_stats()
    scraper.team_stats.write_csv(SAVE_FOLDER / "team_stats" / f"team_stats_{year}.csv")
