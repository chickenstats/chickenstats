from rich.progress import TaskID
from pathlib import Path

import polars as pl

from chickenstats.chicken_nhl.xg import prep_data_polars
from chickenstats.utilities import ChickenProgress


def main():
    """Preps data for xG experiments.

    Play-by-play data are from 2010-2024, with 2024 as the hold-out period.
    Reads data stored in the ./raw directory, then saves data to the ./hold_out
    and ./processed directories.
    """
    # The years we want to process
    years: list[int] = list(range(2024, 2009, -1))

    # Empty lists to collect the data after we prep each year individually
    evens: list[pl.DataFrame] = []
    powerplays: list[pl.DataFrame] = []
    shorthandeds: list[pl.DataFrame] = []
    empty_fors: list[pl.DataFrame] = []
    empty_againsts: list[pl.DataFrame] = []

    # Setting up the progress bar to track everything
    with ChickenProgress(speed_estimate_period=300, transient=True) as progress:
        # Creating task to track everything
        pbar_message: str = "Prepping data for the xG experiments..."
        progress_task: TaskID = progress.add_task(pbar_message, total=len(years))

        # Iterating through the years, keeping track of our place with idx for the progress bar
        for idx, year in enumerate(years):
            # Updating the progress bar message initially, no need to advance
            pbar_message: str = f"Prepping {year}..."
            progress.update(progress_task, description=pbar_message, advance=False, refresh=True)

            # Loading data to prep
            filepath: Path = Path.cwd() / f"raw/pbp_{year}.csv"
            pbp: pl.DataFrame = pl.read_csv(filepath, infer_schema_length=1_000_000)

            # Prepping the various dataframes
            even: pl.DataFrame = prep_data_polars(pbp, "even")
            powerplay: pl.DataFrame = prep_data_polars(pbp, "powerplay")
            shorthanded: pl.DataFrame = prep_data_polars(pbp, "shorthanded")
            empty_for: pl.DataFrame = prep_data_polars(pbp, "empty_for")
            empty_against: pl.DataFrame = prep_data_polars(pbp, "empty_against")

            if year != 2024:
                # If it isn't the hold out year, we're appending to the empty lists above
                evens.append(even)
                powerplays.append(powerplay)
                shorthandeds.append(shorthanded)
                empty_fors.append(empty_for)
                empty_againsts.append(empty_against)

            else:
                # If it is 2024, then we're saving to a hold out
                hold_out_directory: Path = Path.cwd() / "hold_out"

                # Creating the directory if it doesn't exist
                if not hold_out_directory.exists():
                    hold_out_directory.mkdir()

                # Saving the hold out files
                even.write_csv(hold_out_directory / "even_strength.csv")
                powerplay.write_csv(hold_out_directory / "powerplay.csv")
                shorthanded.write_csv(hold_out_directory / "shorthanded.csv")
                empty_for.write_csv(hold_out_directory / "empty_for.csv")
                empty_against.write_csv(hold_out_directory / "empty_against.csv")

            if idx == len(years) - 1:
                pbar_message: str = "Finished prepping data"

            progress.update(progress_task, description=pbar_message, advance=1, refresh=True)

    # Concatenating the data before saving it
    even: pl.DataFrame = pl.concat(evens, how="diagonal")
    powerplay: pl.DataFrame = pl.concat(powerplays, how="diagonal")
    shorthanded: pl.DataFrame = pl.concat(shorthandeds, how="diagonal")
    empty_for: pl.DataFrame = pl.concat(empty_fors, how="diagonal")
    empty_against: pl.DataFrame = pl.concat(empty_againsts, how="diagonal")

    # Setting the directory for the processed data
    processed_directory: Path = Path.cwd() / "processed"

    # Creating directory if it doesn't exist
    if not processed_directory.exists():
        processed_directory.mkdir()

    # Saving everything
    even.write_csv(processed_directory / "even_strength.csv")
    powerplay.write_csv(processed_directory / "powerplay.csv")
    shorthanded.write_csv(processed_directory / "shorthanded.csv")
    empty_for.write_csv(processed_directory / "empty_for.csv")
    empty_against.write_csv(processed_directory / "empty_against.csv")


if __name__ == "__main__":
    main()
