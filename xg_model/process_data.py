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
    years = list(range(2024, 2009, -1))

    # Empty lists to collect the data after we prep each year individually
    evens = []
    powerplays = []
    shorthandeds = []
    empty_fors = []
    empty_againsts = []

    # Setting up the progress bar to track everything
    with ChickenProgress(speed_estimate_period=300, transient=True) as progress:
        # Creating task to track everything
        pbar_message = "Prepping data for the xG experiments..."
        progress_task = progress.add_task(pbar_message, total=len(years))

        # Iterating through the years, keeping track of our place with idx for the progress bar
        for idx, year in enumerate(years):
            # Updating the progress bar message initially, no need to advance
            pbar_message = f"Prepping {year}..."
            progress.update(progress_task, description=pbar_message, advance=False, refresh=True)

            # Loading data to prep
            filepath = Path.cwd() / f"raw/pbp_{year}.csv"
            pbp = pl.read_csv(filepath)

            # Prepping the various dataframes
            even = prep_data_polars(pbp, "even")
            powerplay = prep_data_polars(pbp, "powerplay")
            shorthanded = prep_data_polars(pbp, "shorthanded")
            empty_for = prep_data_polars(pbp, "empty_for")
            empty_against = prep_data_polars(pbp, "empty_against")

            if year != 2024:
                # If it isn't the hold out year, we're appending to the empty lists above
                evens.append(even)
                powerplays.append(powerplay)
                shorthandeds.append(shorthanded)
                empty_fors.append(empty_for)
                empty_againsts.append(empty_against)

            else:
                # If it is 2024, then we're saving to a hold out
                hold_out_directory = Path.cwd() / "hold_out"

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
                pbar_message = "Finished prepping data"

            progress.update(progress_task, description=pbar_message, advance=1, refresh=True)

    # Concatenating the data before saving it
    even = pl.concat(evens)
    powerplay = pl.concat(powerplays)
    shorthanded = pl.concat(shorthandeds)
    empty_for = pl.concat(empty_fors)
    empty_against = pl.concat(empty_againsts)

    # Setting the directory for the processed data
    processed_directory = Path.cwd() / "processed"

    # Creating directory if it doesn't exist
    if not processed_directory.exists():
        processed_directory.mkdir()

    # Saving everything
    even.to_csv(processed_directory / "even_strength.csv")
    powerplay.to_csv(processed_directory / "powerplay.csv")
    shorthanded.to_csv(processed_directory / "shorthanded.csv")
    empty_for.to_csv(processed_directory / "empty_for.csv")
    empty_against.to_csv(processed_directory / "empty_against.csv")


if __name__ == "__main__":
    main()
