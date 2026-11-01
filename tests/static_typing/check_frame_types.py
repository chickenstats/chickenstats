"""Checked by ``ty check tests``, never run: each assertion fails the check if a backend's frame type regresses.

An ``Any`` result fails too, since ``assert_type`` compares the types exactly.
"""

from __future__ import annotations

from typing import Any, assert_type

import narwhals as nw
import pandas as pd
import polars as pl
import pyarrow as pa

from chickenstats import Game, Scraper, Season
from chickenstats.api import ChickenStats
from chickenstats.chicken_nhl import add_schedule_context, multi_season_schedule, search_players
from chickenstats.evolving_hockey.pbp import prep_pbp
from chickenstats.evolving_hockey.stats import (
    prep_gar,
    prep_ind,
    prep_lines,
    prep_oi,
    prep_stats,
    prep_team_stats,
    prep_xgar,
)
from chickenstats.utilities.enums import Backend

NarwhalsFrame = nw.DataFrame[pl.DataFrame]


def scraper_frames() -> None:
    polars = Scraper(2023020001)
    assert_type(polars, Scraper[pl.DataFrame])
    assert_type(polars.play_by_play, pl.DataFrame)
    assert_type(polars.play_by_play_ext, pl.DataFrame)
    assert_type(polars.xg_fields, pl.DataFrame)
    assert_type(polars.api_events, pl.DataFrame)
    assert_type(polars.api_rosters, pl.DataFrame)
    assert_type(polars.html_events, pl.DataFrame)
    assert_type(polars.html_rosters, pl.DataFrame)
    assert_type(polars.rosters, pl.DataFrame)
    assert_type(polars.changes, pl.DataFrame)
    assert_type(polars.shifts, pl.DataFrame)
    assert_type(polars.ind_stats, pl.DataFrame)
    assert_type(polars.oi_stats, pl.DataFrame)
    assert_type(polars.stats, pl.DataFrame)
    assert_type(polars.lines, pl.DataFrame)
    assert_type(polars.team_stats, pl.DataFrame)
    assert_type(polars.stints, pl.DataFrame)
    assert_type(polars.prep_stats().stats, pl.DataFrame)

    assert_type(Scraper(2023020001, backend="polars").play_by_play, pl.DataFrame)
    assert_type(Scraper(2023020001, backend=Backend.POLARS).play_by_play, pl.DataFrame)

    pandas = Scraper(2023020001, backend="pandas")
    assert_type(pandas, Scraper[pd.DataFrame])
    assert_type(pandas.play_by_play, pd.DataFrame)
    assert_type(pandas.stats, pd.DataFrame)
    assert_type(pandas.prep_lines().lines, pd.DataFrame)
    assert_type(Scraper(2023020001, backend=Backend.PANDAS).play_by_play, pd.DataFrame)

    pyarrow = Scraper(2023020001, backend="pyarrow")
    assert_type(pyarrow.play_by_play, pa.Table)
    assert_type(pyarrow.team_stats, pa.Table)
    assert_type(Scraper(2023020001, backend=Backend.PYARROW).play_by_play, pa.Table)

    narwhals = Scraper(2023020001, backend="narwhals")
    assert_type(narwhals.play_by_play, NarwhalsFrame)
    assert_type(narwhals.stints, NarwhalsFrame)
    assert_type(Scraper(2023020001, backend=Backend.NARWHALS).play_by_play, NarwhalsFrame)


def scraper_load() -> None:
    assert_type(Scraper.load("saved", backend="polars").play_by_play, pl.DataFrame)
    assert_type(Scraper.load("saved", backend="pandas").play_by_play, pd.DataFrame)
    assert_type(Scraper.load("saved", backend="pyarrow").play_by_play, pa.Table)
    assert_type(Scraper.load("saved", backend="narwhals").play_by_play, NarwhalsFrame)
    assert_type(Scraper.load("saved"), Scraper[Any])


def backend_known_only_at_runtime(backend: Backend) -> None:
    assert_type(Scraper(2023020001, backend=backend), Scraper[Any])
    assert_type(Game(2023020001, backend=backend), Game[Any])
    assert_type(Season(2023, backend=backend), Season[Any])
    assert_type(ChickenStats(backend=backend), ChickenStats[Any])


def game_frames() -> None:
    polars = Game(2023020001)
    assert_type(polars.play_by_play_df, pl.DataFrame)
    assert_type(polars.xg_fields_df, pl.DataFrame)
    assert_type(polars.api_events_df, pl.DataFrame)
    assert_type(polars.api_rosters_df, pl.DataFrame)
    assert_type(polars.html_events_df, pl.DataFrame)
    assert_type(polars.html_rosters_df, pl.DataFrame)
    assert_type(polars.rosters_df, pl.DataFrame)
    assert_type(polars.changes_df, pl.DataFrame)
    assert_type(polars.shifts_df, pl.DataFrame)

    assert_type(Game(2023020001, backend="pandas").play_by_play_df, pd.DataFrame)
    assert_type(Game(2023020001, backend="pyarrow").rosters_df, pa.Table)
    assert_type(Game(2023020001, backend="narwhals").shifts_df, NarwhalsFrame)


def season_frames() -> None:
    assert_type(Season(2023).standings, pl.DataFrame)
    assert_type(Season(2023).schedule(), pl.DataFrame)
    assert_type(Season(2023, backend="pandas").standings, pd.DataFrame)
    assert_type(Season(2023, backend="pandas").schedule(), pd.DataFrame)
    assert_type(Season(2023, backend="pyarrow").schedule(), pa.Table)
    assert_type(Season(2023, backend="narwhals").schedule(), NarwhalsFrame)


def schedule_functions(pd_schedule: pd.DataFrame, schedule: pl.DataFrame, backend: Backend) -> None:
    assert_type(multi_season_schedule(2023), pl.DataFrame)
    assert_type(multi_season_schedule(2023, backend="pandas"), pd.DataFrame)
    assert_type(multi_season_schedule(2023, backend="pyarrow"), pa.Table)
    assert_type(multi_season_schedule(2023, backend="narwhals"), NarwhalsFrame)
    assert_type(multi_season_schedule(2023, backend=backend), Any)

    assert_type(add_schedule_context(schedule), pl.DataFrame)
    assert_type(add_schedule_context(pd_schedule), pd.DataFrame)
    assert_type(add_schedule_context(pd_schedule, backend="polars"), pl.DataFrame)
    assert_type(add_schedule_context(schedule, backend="pandas"), pd.DataFrame)
    assert_type(add_schedule_context(schedule, backend="pyarrow"), pa.Table)
    assert_type(add_schedule_context(schedule, backend="narwhals"), NarwhalsFrame)


def player_search() -> None:
    assert_type(search_players("mcdavid"), pl.DataFrame)
    assert_type(search_players("mcdavid", backend="pandas"), pd.DataFrame)
    assert_type(search_players("mcdavid", backend="pyarrow"), pa.Table)
    assert_type(search_players("mcdavid", backend="narwhals"), NarwhalsFrame)


def api_frames() -> None:
    assert_type(ChickenStats().download_pbp(), pl.DataFrame)
    assert_type(ChickenStats().download_players(), pl.DataFrame)
    assert_type(ChickenStats().get_live_games(), pl.DataFrame)
    assert_type(ChickenStats(backend="polars").download_rapm(), pl.DataFrame)
    assert_type(ChickenStats(backend="pandas").download_pbp(), pd.DataFrame)
    assert_type(ChickenStats(backend="pyarrow").download_games(), pa.Table)
    assert_type(ChickenStats(backend="narwhals").download_shifts(), NarwhalsFrame)


def evolving_hockey_follows_the_input(
    polars: pl.DataFrame, pandas: pd.DataFrame, pyarrow: pa.Table, narwhals: nw.DataFrame[Any]
) -> None:
    assert_type(prep_ind(polars), pl.DataFrame)
    assert_type(prep_ind(pandas), pd.DataFrame)
    assert_type(prep_ind(pyarrow), pa.Table)
    assert_type(prep_ind(narwhals), nw.DataFrame[Any])
    assert_type(prep_oi(pandas), pd.DataFrame)
    assert_type(prep_stats(pandas, level="season"), pd.DataFrame)
    assert_type(prep_lines(pandas), pd.DataFrame)
    assert_type(prep_team_stats(pandas), pd.DataFrame)
    assert_type(prep_gar(pandas, pandas), pd.DataFrame)
    assert_type(prep_xgar(pandas), pd.DataFrame)
    assert_type(prep_pbp(pandas, pandas), pd.DataFrame)
    assert_type(prep_pbp([pandas, pandas], [pandas, pandas]), pd.DataFrame)


def evolving_hockey_takes_a_backend(pbp: pl.DataFrame, pandas: pd.DataFrame, backend: str) -> None:
    assert_type(prep_ind(pandas, backend="polars"), pl.DataFrame)
    assert_type(prep_ind(pbp, backend="pandas"), pd.DataFrame)
    assert_type(prep_ind(pbp, backend="pyarrow"), pa.Table)
    assert_type(prep_ind(pbp, backend="narwhals"), NarwhalsFrame)
    assert_type(prep_ind(pbp, backend=backend), Any)
    assert_type(prep_oi(pbp, backend="pandas"), pd.DataFrame)
    assert_type(prep_stats(pbp, backend=Backend.PANDAS), pd.DataFrame)
    assert_type(prep_lines(pbp, backend="pyarrow"), pa.Table)
    assert_type(prep_team_stats(pbp, backend="narwhals"), NarwhalsFrame)
    assert_type(prep_gar(pbp, pbp, backend="pandas"), pd.DataFrame)
    assert_type(prep_xgar(pbp, backend="pyarrow"), pa.Table)
    assert_type(prep_pbp(pbp, pbp, backend="narwhals"), NarwhalsFrame)
