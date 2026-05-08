# Python script for scraping raw play-by-play data using the chickenstats library

from pathlib import Path
import json

import polars as pl

from chickenstats.chicken_nhl import Season, Scraper


def main():
    """Scrapes play-by-play data for the 2010-2024 seasons, in reverse chronological order.

    Skips the season if there is already a csv file for that year. Data are saved to the
    ./raw directory, for later usage in the process data workflow.

    """
    # Generating a list of years to scrape
    years = list(range(2024, 2009, -1))

    save_folder = Path(__file__).parent / "data" / "raw"

    save_folder.mkdir(parents=True, exist_ok=True)

    # Iterate through the years
    for year in years:
        filepath = save_folder / f"pbp_{year}.parquet"

        if filepath.exists():
            continue

        # Scraping the schedule information
        season = Season(year)
        sched = season.schedule(transient_progress_bar=True)
        sched = sched.filter(pl.col("game_state") == "OFF")

        # Getting the game IDs and setting up the scraper object
        game_ids = sched["game_id"].to_list()
        scraper = Scraper(game_ids, transient_progress_bar=True)

        # Scrape the play by play for the year
        pbp = scraper.play_by_play

        # Saving files
        pbp.write_parquet(filepath)

        if scraper.failed_games:
            failed_path = Path(__file__).parent / "data" / f"failed_games_{year}.json"
            with open(failed_path, "w") as f:
                json.dump(scraper.failed_games, f)


if __name__ == "__main__":
    main()
