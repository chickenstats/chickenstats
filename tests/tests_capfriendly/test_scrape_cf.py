import pandas as pd

from chickenstats.capfriendly.scrape import scrape_capfriendly


def test_scrape_capfriendly():
    cf = scrape_capfriendly(2022)

    assert isinstance(cf, pd.DataFrame) is True


def test_scrape_capfriendly_fail():
    cf = scrape_capfriendly(20222)

    assert isinstance(cf, pd.DataFrame) is True
