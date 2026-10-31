from __future__ import annotations

import json
import os
import warnings
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from chickenstats.chicken_nhl._scraper_core import (
    _SCRAPE_REGISTRY,
    FINAL_STATE,
    _ScraperBase,
    _user_stacklevel,
    normalize_game_ids,
)
from chickenstats.exceptions import SaveFormatError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.utilities import data_directory

if TYPE_CHECKING:
    from typing_extensions import Self

    from chickenstats.utilities.utilities import ChickenSession

# Bump when a saved frame's columns or types change
SAVE_FORMAT = 5

_META_FILE = "_meta.json"


def _split_by_game(frame: pl.DataFrame) -> dict[int, pl.DataFrame]:
    """One type's saved rows, split by game.

    play_by_play_ext has no game_id column; its id is the game ID followed by a four-digit event index.
    """
    game_id = pl.col("game_id") if "game_id" in frame.columns else pl.col("id") // 10_000
    keyed = frame.with_columns(_game=game_id)
    return {key: rows.drop("_game") for (key,), rows in keyed.partition_by("_game", as_dict=True).items()}


def _replace_file(path: Path, write: Callable[[Path], object]) -> None:
    """Write a file under a temporary name and swap it in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        write(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class _ScraperPersistMixin(_ScraperBase):
    def save(self, path: str | Path | None = None) -> Path:
        """Save all currently-scraped raw data to disk as parquet files.

        Writes one parquet file per data type, then ``_meta.json``, which records each game's types, whether
        it was final, and its failures. A save replaces an earlier one in the same directory.

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

        types: dict[str, list[int]] = {}
        for key, spec in _SCRAPE_REGISTRY.items():
            stored: dict[int, pl.DataFrame] = getattr(self, spec.list_attr)
            if stored:
                _replace_file(target / f"{key}.parquet", self._concat_stored(stored, spec.schema).write_parquet)
                types[key] = [game_id for game_id in self.game_ids if game_id in stored]

        # A game is saved as OFF only once every type is, so a type fetched earlier is fetched again on load
        states = {
            str(game_id): state
            for game_id, state in self._game_states.items()
            if state != FINAL_STATE or self._fetched_final(game_id)
        }
        meta = {
            "format": SAVE_FORMAT,
            "version": version("chickenstats"),
            "backend": self._backend,
            "game_ids": list(self.game_ids),
            "types": types,
            "states": states,
            "failed": {str(game_id): sorted(failed) for game_id, failed in self._failed_types.items() if failed},
            "reasons": {str(game_id): reason for game_id, reason in self._failure_reasons.items()},
        }
        # Written last, and only the files it lists are loaded, so a save stopped partway loads the earlier one
        _replace_file(target / _META_FILE, lambda file: file.write_text(json.dumps(meta, indent=2)))

        return target

    def _apply_saved(self, path: Path, meta: dict) -> None:
        """Populate ``self`` with the frames, states and failures that :meth:`save` wrote to path."""
        saved_ids = normalize_game_ids(meta["game_ids"]) if meta["game_ids"] else []
        self.game_ids = list(dict.fromkeys([*saved_ids, *self.game_ids]))

        for key, game_ids in meta["types"].items():
            spec = _SCRAPE_REGISTRY[key]
            by_game = _split_by_game(pl.read_parquet(path / f"{key}.parquet"))
            stored: dict[int, pl.DataFrame] = getattr(self, spec.list_attr)
            for game_id in game_ids:
                stored[game_id] = by_game.get(game_id, pl.DataFrame(schema=spec.schema))

        # A game with no recorded state is provisional, so it is fetched again on its next scrape
        for key, state in meta["states"].items():
            game_id = int(key)
            self._game_states[game_id] = state
            if state == FINAL_STATE:
                self._final_types[game_id] = {x for x, ids in meta["types"].items() if game_id in ids}

        for key, failed in meta["failed"].items():
            game_id = int(key)
            self._failed_types[game_id] = set(failed)
            self._bad_games.append(game_id)

            reason = meta["reasons"].get(key)
            if reason:
                self._failure_reasons[game_id] = reason

    @classmethod
    def load(
        cls,
        path: str | Path,
        game_ids: list | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] | None = None,
        requests_session: ChickenSession | None = None,
    ) -> Self:
        """Load a Scraper from data previously written by :meth:`save`.

        Saved games are marked as scraped, except a game that was not final when it was saved, which is
        fetched again on its next scrape. ``game_ids`` that were not saved are added and scraped on next
        access.

        Parameters:
            path (str | Path):
                Directory previously written by :meth:`save`.
            game_ids (list | None):
                Additional game IDs to scrape beyond what was saved. Defaults to ``None``
                (only the saved games).
            disable_progress_bar (bool):
                Suppress the Rich progress bar globally for this instance. Default ``False``.
            transient_progress_bar (bool):
                Clear the progress bar from the terminal after it completes. Default ``False``.
            backend (str | None):
                DataFrame backend for all returned data. Defaults to whatever backend the
                saved Scraper used.
            requests_session (ChickenSession | None):
                ChickenSession to use for requests, e.g., with a custom user agent. Defaults to a new ChickenSession.

        Returns:
            Scraper: A new instance with the saved data pre-loaded.

        Raises:
            FileNotFoundError: If path holds no save.
            SaveFormatError: If the save was written in another format, such as by chickenstats before 1.9.0.

        Warns:
            UserWarning: If another version of chickenstats wrote the save, since a later release can change
                values without changing columns. ``refresh()`` fetches the games again.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper.load("my_scrape")
            >>> pbp = scraper.play_by_play  # no network calls for already-saved games

            Extend with new games — only the new ones get scraped
            >>> scraper = Scraper.load("my_scrape", game_ids=[2023020003])
            >>> pbp = scraper.play_by_play
        """
        source = Path(path)
        file = source / _META_FILE
        if not file.exists():
            raise FileNotFoundError(f"No chickenstats save in {source}")

        meta = json.loads(file.read_text())
        if meta.get("format") != SAVE_FORMAT:
            raise SaveFormatError(
                f"The data in {source} was saved by another version of chickenstats and cannot be read. "
                "Scrape those games again.",
                path=source,
            )
        current = version("chickenstats")
        if meta["version"] != current:
            warnings.warn(
                f"The data in {source} was saved by chickenstats {meta['version']}, not {current}, which can give "
                "different values for the same game. Call refresh() to fetch the games again.",
                UserWarning,
                stacklevel=_user_stacklevel(),
            )

        extra_ids: list[str | float | int] = list(normalize_game_ids(game_ids)) if game_ids else []

        scraper = cls(
            extra_ids,
            disable_progress_bar=disable_progress_bar,
            transient_progress_bar=transient_progress_bar,
            backend=backend or meta.get("backend", "polars"),
            requests_session=requests_session,
        )
        scraper._apply_saved(source, meta)

        return scraper
