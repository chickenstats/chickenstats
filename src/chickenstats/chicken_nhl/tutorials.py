import pandas as pd


def load_data(source, series, data_type):
    """Load data for use in chickenstats tutorials."""
    if source not in ["evolving_hockey", "chicken_nhl"]:
        raise Exception(f"{source} is not a valid source")

    if series not in ["october_2023", "playoffs_2017"]:
        raise Exception(f"{series} is not a valid series")

    if data_type not in ["shifts", "pbp"]:
        raise Exception(f"{data_type} is not a valid data type")

    base_url = "https://raw.githubusercontent.com/chickenandstats/chickenstats/main/tutorials/data/raw/"

    url = f"{base_url}{source}/{series}/{data_type}.csv"

    data = pd.read_csv(url, low_memory=False)

    return data
