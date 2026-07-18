from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from chickenstats.chicken_nhl._scraper_core import _ScraperBase
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.utilities import data_directory

if TYPE_CHECKING:
    from typing_extensions import Self

# Maps a scrape-data key to the Scraper attribute holding its raw per-game DataFrame list.
_RAW_DATA_ATTRS: dict[str, str] = {
    "api_events": "_api_events",
    "api_rosters": "_api_rosters",
    "changes": "_changes",
    "html_events": "_html_events",
    "html_rosters": "_html_rosters",
    "rosters": "_rosters",
    "shifts": "_shifts",
    "play_by_play": "_play_by_play",
    "play_by_play_ext": "_play_by_play_ext",
    "xg_fields": "_xg_fields",
}

# Maps a scrape-data key to the Scraper attribute tracking which game IDs already have that
# data. play_by_play/play_by_play_ext/xg_fields share a single tracker since one "play_by_play"
# scrape populates all three at once (see _ScraperCore._scrape_single_game).
_SCRAPED_TRACKER_ATTRS: dict[str, str] = {
    "api_events": "_scraped_api_events",
    "api_rosters": "_scraped_api_rosters",
    "changes": "_scraped_changes",
    "html_events": "_scraped_html_events",
    "html_rosters": "_scraped_html_rosters",
    "rosters": "_scraped_rosters",
    "shifts": "_scraped_shifts",
    "play_by_play": "_scraped_play_by_play",
}


class _ScraperPersistMixin(_ScraperBase):
    def save(self, path: str | Path | None = None) -> Path:
        """Save all currently-scraped raw data to disk as parquet files.

        Writes one parquet file per populated raw data type, plus a ``_meta.json`` recording
        game IDs, failed games, and which game IDs already have which data type — that
        metadata is what lets :meth:`load` skip re-fetching already-scraped games.

        Parameters:
            path (str | Path | None):
                Directory to save into. Created if it doesn't exist. Defaults to
                ``data_directory()`` (``./data`` in the current working directory).

        Returns:
            Path: The directory the data was saved to.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper([2023020001, 2023020002])
            >>> pbp = scraper.play_by_play
            >>> save_path = scraper.save("my_scrape")
        """
        target = Path(path) if path is not None else data_directory()
        target.mkdir(parents=True, exist_ok=True)

        for key, attr in _RAW_DATA_ATTRS.items():
            frames: list[pl.DataFrame] = getattr(self, attr)
            if frames:
                pl.concat(frames).write_parquet(target / f"{key}.parquet")

        meta = {
            "game_ids": list(self.game_ids),
            "bad_games": list(self._bad_games),
            "backend": self._backend,
            "scraped": {key: sorted(getattr(self, attr)) for key, attr in _SCRAPED_TRACKER_ATTRS.items()},
        }
        (target / "_meta.json").write_text(json.dumps(meta, indent=2))

        return target

    def _apply_cache(self, path: Path, meta: dict | None = None) -> None:
        """Populate ``self`` with cached data previously written by :meth:`save`.

        Extends ``self.game_ids`` with any cached game IDs not already present (cached IDs
        first, matching :meth:`load`'s documented merge order), loads the raw parquet data,
        and marks the corresponding game IDs as already-scraped so subsequent property
        access (e.g. ``.play_by_play``) skips re-fetching them. Shared by
        ``__init__(cache=...)`` and :meth:`load`.

        Parameters:
            path (Path): Directory previously written by :meth:`save`.
            meta (dict | None): Already-parsed ``_meta.json`` contents, if the caller has
                them; read from ``path`` otherwise.
        """
        if meta is None:
            meta = json.loads((path / "_meta.json").read_text())

        cached_ids = meta["game_ids"]
        self.game_ids = list(dict.fromkeys([*cached_ids, *self.game_ids]))
        self._bad_games = list(dict.fromkeys([*self._bad_games, *meta.get("bad_games", [])]))

        for key, attr in _RAW_DATA_ATTRS.items():
            file = path / f"{key}.parquet"
            if file.exists():
                setattr(self, attr, [pl.read_parquet(file)])

        scraped = meta.get("scraped", {})
        for key, attr in _SCRAPED_TRACKER_ATTRS.items():
            getattr(self, attr).update(scraped.get(key, []))

    @classmethod
    def load(
        cls,
        path: str | Path,
        game_ids: list | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] | None = None,
    ) -> Self:
        """Load a Scraper from data previously written by :meth:`save`.

        Already-cached games are marked as scraped, so subsequent property access (e.g.
        ``.play_by_play``) doesn't re-fetch them. Passing ``game_ids`` not present in the
        cache extends the loaded Scraper's ``game_ids`` with those new IDs, so only the
        delta gets scraped on the next access — the same mechanism doubles as resumable
        scraping across process restarts.

        Parameters:
            path (str | Path):
                Directory previously written by :meth:`save`.
            game_ids (list | None):
                Additional game IDs to scrape beyond what's cached. Defaults to ``None``
                (only the cached games).
            disable_progress_bar (bool):
                Suppress the Rich progress bar globally for this instance. Default ``False``.
            transient_progress_bar (bool):
                Clear the progress bar from the terminal after it completes. Default ``False``.
            backend (str | None):
                DataFrame backend for all returned data. Defaults to whatever backend the
                saved Scraper used.

        Returns:
            Scraper: A new instance with the cached data pre-loaded.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper.load("my_scrape")
            >>> pbp = scraper.play_by_play  # no network calls for already-cached games

            Extend with new games — only the new ones get scraped
            >>> scraper = Scraper.load("my_scrape", game_ids=[2023020003])
            >>> pbp = scraper.play_by_play
        """
        source = Path(path)
        meta = json.loads((source / "_meta.json").read_text())

        extra_ids = list(game_ids) if game_ids else []

        scraper = cls(
            extra_ids,
            disable_progress_bar=disable_progress_bar,
            transient_progress_bar=transient_progress_bar,
            backend=backend or meta.get("backend", "polars"),
        )
        scraper._apply_cache(source, meta=meta)

        return scraper
