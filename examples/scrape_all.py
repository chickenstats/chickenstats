# Python script for scraping raw play-by-play and other data using the chickenstats library

from pathlib import Path

from chickenstats.chicken_nhl import Season, Scraper

# Generating a list of years to scrape
years = list(range(2023, 2009, -1))

# Folders for saving the files
SAVE_FOLDER = Path("./raw")
sub_folders = ["pbp", "stats", "lines", "team_stats"]

for sub_folder in sub_folders:
    sub_folder_path = SAVE_FOLDER / sub_folder
    sub_folder_path.mkdir(parents=True, exist_ok=True)

# Iterate through the years
for year in years:

    season = Season(year)

    sched = season.schedule()

    sched = sched.loc[sched.game_state == "OFF"].reset_index(drop=True)

    game_ids = sched.game_id.unique().tolist()

    scraper = Scraper(game_ids)

    # Scrape the play by play for the year
    pbp = scraper.play_by_play

    # Setting filepath
    filepath = SAVE_FOLDER / "pbp" / f"pbp_{year}.csv"

    # Saving files
    pbp.to_csv(filepath, index=False)

    scraper.prep_stats(level="period", score=True, teammates=True, opposition=True)
    stats = scraper.stats

    # Setting filepath
    filepath = SAVE_FOLDER / "stats" / f"stats_{year}.csv"

    # Saving files
    stats.to_csv(filepath, index=False)

    scraper.prep_lines(position="f", level="period", score=True, teammates=True, opposition=True)
    lines = scraper.lines

    # Setting filepath
    filepath = SAVE_FOLDER / "lines" / f"lines_{year}.csv"

    # Saving files
    lines.to_csv(filepath, index=False)

    scraper.prep_team_stats(level="period", strengths=True, score=True, opposition=True)
    team_stats = scraper.team_stats

    # Setting filepath
    filepath = SAVE_FOLDER / "team_stats" / f"team_stats_{year}.csv"

    # Saving files
    team_stats.to_csv(filepath, index=False)
