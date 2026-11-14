"""Shared offline fixtures for the evolving_hockey tests."""

import time
from types import SimpleNamespace

import polars as pl
import pytest
from .eh_converter import (
    SAVED_GAME_IDS,
    csv_round_trip,
    to_eh_gar_goalies,
    to_eh_gar_skaters,
    to_eh_pbp,
    to_eh_shifts,
    to_eh_xgar_skaters,
)

from chickenstats.chicken_nhl import Scraper
from chickenstats.evolving_hockey import prep_pbp


SHARED_FRAMES_TIMEOUT = 180


def build_frames() -> dict[str, pl.DataFrame]:
    """Scrape the saved games, convert them to Evolving-Hockey exports and run prep_pbp on those."""
    scraper = Scraper([*SAVED_GAME_IDS], disable_progress_bar=True)
    play_by_play, rosters, shifts = scraper.play_by_play, scraper.rosters, scraper.shifts
    raw_pbp = csv_round_trip(to_eh_pbp(play_by_play, rosters))
    raw_shifts = csv_round_trip(to_eh_shifts(shifts, play_by_play))

    return {
        "play_by_play": play_by_play,
        "play_by_play_ext": scraper.play_by_play_ext,
        "rosters": rosters,
        "shifts": shifts,
        "raw_pbp": raw_pbp,
        "raw_shifts": raw_shifts,
        "pbp": prep_pbp(pbp=raw_pbp, shifts=raw_shifts, disable_progress_bar=True),
    }


@pytest.fixture(scope="session")
def frames(tmp_path_factory, worker_id) -> dict[str, pl.DataFrame]:
    """The frames every test here starts from, built by the first worker to ask and read from disk by the others."""
    if worker_id == "master":
        return build_frames()

    shared = tmp_path_factory.getbasetemp().parent / "eh_frames"
    finished = shared / "finished"

    # mkdir succeeds for one worker only, which needs no lock file and works on every platform
    try:
        shared.mkdir()
    except FileExistsError:
        deadline = time.monotonic() + SHARED_FRAMES_TIMEOUT
        while not finished.exists():
            # The folder goes away if the build failed; build here so this worker reports the same error
            if not shared.exists() or time.monotonic() > deadline:
                return build_frames()
            time.sleep(0.05)
        return {path.stem: pl.read_parquet(path) for path in shared.glob("*.parquet")}

    try:
        built = build_frames()
    except Exception:
        shared.rmdir()
        raise

    for name, frame in built.items():
        frame.write_parquet(shared / f"{name}.parquet")
    finished.touch()

    return built


@pytest.fixture(scope="session")
def chicken(frames):
    """The chicken_nhl frames for the saved games, read from the saved responses."""
    return SimpleNamespace(
        play_by_play=frames["play_by_play"],
        play_by_play_ext=frames["play_by_play_ext"],
        rosters=frames["rosters"],
        shifts=frames["shifts"],
    )


@pytest.fixture(scope="session")
def raw_pbp_polars(frames):
    """The saved games as an Evolving-Hockey play-by-play export."""
    return frames["raw_pbp"]


@pytest.fixture(scope="session")
def raw_shifts_polars(frames):
    """The saved games as an Evolving-Hockey shifts export."""
    return frames["raw_shifts"]


@pytest.fixture(scope="session")
def pbp_polars(frames):
    return frames["pbp"]


@pytest.fixture(scope="session")
def pbp_lazy(pbp_polars):
    return pbp_polars.lazy()


@pytest.fixture(scope="session")
def pbp_pandas(pbp_polars):
    return pbp_polars.to_pandas()


@pytest.fixture(scope="session")
def pbp_pyarrow(raw_pbp_polars, raw_shifts_polars):
    return prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, backend="pyarrow", disable_progress_bar=True)


@pytest.fixture(scope="session")
def raw_gar_skater_polars(chicken):
    return csv_round_trip(to_eh_gar_skaters(chicken.shifts))


@pytest.fixture(scope="session")
def raw_gar_goalie_polars(chicken):
    return csv_round_trip(to_eh_gar_goalies(chicken.shifts))


@pytest.fixture(scope="session")
def raw_xgar_polars(chicken):
    return csv_round_trip(to_eh_xgar_skaters(chicken.shifts))


@pytest.fixture(scope="session")
def raw_gar_skater_pandas(raw_gar_skater_polars):
    return raw_gar_skater_polars.to_pandas()


@pytest.fixture(scope="session")
def raw_gar_goalie_pandas(raw_gar_goalie_polars):
    return raw_gar_goalie_polars.to_pandas()


@pytest.fixture(scope="session")
def raw_xgar_pandas(raw_xgar_polars):
    return raw_xgar_polars.to_pandas()


@pytest.fixture(scope="session")
def raw_gar_skater_pyarrow(raw_gar_skater_polars):
    return raw_gar_skater_polars.to_arrow()


@pytest.fixture(scope="session")
def raw_gar_goalie_pyarrow(raw_gar_goalie_polars):
    return raw_gar_goalie_polars.to_arrow()


@pytest.fixture(scope="session")
def raw_xgar_pyarrow(raw_xgar_polars):
    return raw_xgar_polars.to_arrow()
