from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from chickenstats.chicken_nhl._scraper_core import _SCRAPE_REGISTRY, FINAL_STATE, _ScraperBase, normalize_game_ids
from chickenstats.exceptions import CacheFormatError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.utilities import data_directory

if TYPE_CHECKING:
    from typing_extensions import Self

# Raised whenever what a cache stores changes; a cache in any other format is refused, never cast (R29)
CACHE_FORMAT = 2

_META_FILE = "_meta.json"


def _split_by_game(frame: pl.DataFrame) -> dict[int, pl.DataFrame]:
    """One type's saved rows, split by game.

    play_by_play_ext has no game_id column; its id is the game ID followed by a four-digit event index.
    """
    game_id = pl.col("game_id") if "game_id" in frame.columns else pl.col("id") // 10_000
    keyed = frame.with_columns(_game=game_id)
    return {key: rows.drop("_game") for (key,), rows in keyed.partition_by("_game", as_dict=True).items()}


def _replace_file(path: Path, write: Callable[[Path], object]) -> None:
    """Write a file under a temporary name and swap it in, so a reader never sees it half-written (N54)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        write(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_meta(path: Path) -> dict | None:
    """The cache's metadata, or None if the directory holds no cache.

    Raises:
        CacheFormatError: If the cache was written in another format, such as by chickenstats before 1.9.0.
    """
    file = path / _META_FILE
    if not file.exists():
        return None

    meta = json.loads(file.read_text())
    if meta.get("format") != CACHE_FORMAT:
        raise CacheFormatError(
            f"The cache in {path} was written by another version of chickenstats and cannot be read. Delete it, "
            "or pass overwrite=True to replace it.",
            path=path,
        )
    return meta


def _new_meta(backend: str) -> dict:
    return {"format": CACHE_FORMAT, "backend": backend, "game_ids": [], "games": {}, "failed": {}, "reasons": {}}


def _remove_cache_files(path: Path) -> None:
    """Remove the files an existing cache's ``_meta.json`` lists, and the metadata itself; with none, nothing.

    ``cache=True`` uses ``./data``, which can hold the user's own files, such as a ``play_by_play.parquet``, so
    only the files a cache recorded are removed, and the directory itself is kept (in-01).
    """
    file = path / _META_FILE
    if not file.exists():
        return

    meta = json.loads(file.read_text())
    if "games" in meta:
        files = [
            path / key / name
            for game_id, entry in meta["games"].items()
            for key in entry.get("types", [])
            for name in (f"{game_id}.parquet", f".{game_id}.parquet.tmp")
        ]
    else:
        # chickenstats before 1.9.0 wrote one file per type next to _meta.json
        files = [path / f"{key}.parquet" for key in _SCRAPE_REGISTRY]

    for listed in files:
        listed.unlink(missing_ok=True)
    for key in _SCRAPE_REGISTRY:
        folder = path / key
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    file.unlink()


class _ScraperPersistMixin(_ScraperBase):
    def save(self, path: str | Path | None = None) -> Path:
        """Save all currently-scraped raw data to disk as parquet files.

        Writes one parquet file per game and data type, in a folder per type, then ``_meta.json``, which
        records each game's types, API state and failures. Games already saved in the directory by another
        Scraper are kept.

        Parameters:
            path (str | Path | None):
                Directory to save into. Created if it doesn't exist. Defaults to
                ``data_directory()`` (``./data`` in the current working directory).

        Returns:
            Path: The directory the data was saved to.

        Raises:
            CacheFormatError: If the directory holds a cache in another format.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper([2023020001, 2023020002])
            >>> pbp = scraper.play_by_play
            >>> save_path = scraper.save("my_scrape")
        """
        target = Path(path) if path is not None else data_directory()
        target.mkdir(parents=True, exist_ok=True)

        meta = _read_meta(target) or _new_meta(self._backend)
        for game_id in self.game_ids:
            self._write_game(target, meta, game_id, _SCRAPE_REGISTRY)
        _replace_file(target / _META_FILE, lambda file: file.write_text(json.dumps(meta, indent=2)))

        return target

    def _write_game(self, path: Path, meta: dict, game_id: int, keys: Iterable[str]) -> None:
        """Write game_id's frames for keys under path, and record the game in meta; meta is written by the caller."""
        for key in keys:
            frame = getattr(self, _SCRAPE_REGISTRY[key].list_attr).get(game_id)
            if frame is not None:
                _replace_file(path / key / f"{game_id}.parquet", frame.write_parquet)

        if game_id not in meta["game_ids"]:
            meta["game_ids"].append(game_id)
        types = [key for key, spec in _SCRAPE_REGISTRY.items() if game_id in getattr(self, spec.list_attr)]
        if types:
            # A game is saved as OFF only once every type is, so a type fetched earlier is fetched again on load
            state = self._game_states.get(game_id)
            if state == FINAL_STATE and not self._fetched_final(game_id):
                state = None
            meta["games"][str(game_id)] = {"state": state, "types": types}
        failed = self._failed_types.get(game_id)
        # A cache from before reasons were saved has no "reasons" key
        reasons = meta.setdefault("reasons", {})
        if failed:
            meta["failed"][str(game_id)] = sorted(failed)
            if game_id in self._failure_reasons:
                reasons[str(game_id)] = self._failure_reasons[game_id]
        else:
            meta["failed"].pop(str(game_id), None)
            reasons.pop(str(game_id), None)

    def _cache_game(self, game_id: int, keys: Iterable[str]) -> None:
        """Write one game to the cache as soon as its scrape ends, so an interrupted run keeps it (N53).

        The game's files are written before ``_meta.json``, and only files the metadata lists are loaded, so
        a run stopped between the two loads as if the game had not been scraped.
        """
        if self._cache_dir is None:
            return
        if self._cache_meta is None:
            self._cache_meta = _read_meta(self._cache_dir) or _new_meta(self._backend)
        meta = self._cache_meta
        self._write_game(self._cache_dir, meta, game_id, keys)
        _replace_file(self._cache_dir / _META_FILE, lambda file: file.write_text(json.dumps(meta, indent=2)))

    def _clear_cache(self, path: Path) -> None:
        """Remove an existing cache's files, for overwrite=True (R38)."""
        _remove_cache_files(path)
        self._cache_meta = None

    def _apply_cache(
        self, path: Path, meta: dict | None = None, add_cached_games: bool = True, only: list[int] | None = None
    ) -> None:
        """Populate ``self`` with cached data previously written by :meth:`save`.

        Loads the raw parquet data for the Scraper's games and marks them as already scraped.

        Parameters:
            path (Path): Directory previously written by :meth:`save`.
            meta (dict | None): Already-read ``_meta.json`` contents, if the caller has
                them; read from ``path`` otherwise.
            add_cached_games (bool): Extend ``self.game_ids`` with every cached game (cached
                first), as :meth:`load` does. ``cache=`` passes ``False``, so a Scraper asked for
                one game returns that game (N84).
            only (list[int] | None): Read only these games, so the frames already held for the others are
                kept. ``add_games()`` passes the games it adds (bA-07).
        """
        meta = meta or _read_meta(path)
        if meta is None:
            return

        if add_cached_games:
            cached_ids = normalize_game_ids(meta["game_ids"]) if meta["game_ids"] else []
            self.game_ids = list(dict.fromkeys([*cached_ids, *self.game_ids]))
        scope = set(self.game_ids if only is None else only)
        games = {int(game_id): entry for game_id, entry in meta["games"].items() if int(game_id) in scope}

        for key, spec in _SCRAPE_REGISTRY.items():
            # A listed file that is missing is left out, so its game is fetched again
            files = {
                game_id: path / key / f"{game_id}.parquet" for game_id, entry in games.items() if key in entry["types"]
            }
            present = {game_id: file for game_id, file in files.items() if file.exists()}
            frame = pl.read_parquet(list(present.values())) if present else pl.DataFrame(schema=spec.schema)
            by_game = _split_by_game(frame)
            stored: dict[int, pl.DataFrame] = getattr(self, spec.list_attr)
            for game_id in present:
                stored[game_id] = by_game.get(game_id, pl.DataFrame(schema=spec.schema))

        # A game with no recorded state is provisional, so it is fetched again on its next scrape
        self._game_states.update({game_id: entry["state"] for game_id, entry in games.items() if entry["state"]})
        self._final_types.update(
            {game_id: set(entry["types"]) for game_id, entry in games.items() if entry["state"] == FINAL_STATE}
        )

        for game_id, types in meta["failed"].items():
            if int(game_id) in scope:
                self._failed_types.setdefault(int(game_id), set()).update(types)
                if int(game_id) not in self._bad_games:
                    self._bad_games.append(int(game_id))
                reason = meta.get("reasons", {}).get(game_id)
                if reason:
                    self._failure_reasons[int(game_id)] = reason

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

        Already-cached games are marked as scraped, except a game that was not final when it was saved, which
        is fetched again on its next scrape. ``game_ids`` not present in the cache are added and scraped on
        next access.

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

        Raises:
            CacheFormatError: If the cache was written in another format, such as by chickenstats before 1.9.0.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper.load("my_scrape")
            >>> pbp = scraper.play_by_play  # no network calls for already-cached games

            Extend with new games — only the new ones get scraped
            >>> scraper = Scraper.load("my_scrape", game_ids=[2023020003])
            >>> pbp = scraper.play_by_play
        """
        source = Path(path)
        meta = _read_meta(source)
        if meta is None:
            raise FileNotFoundError(f"No chickenstats cache in {source}")

        extra_ids: list[str | float | int] = list(normalize_game_ids(game_ids)) if game_ids else []

        scraper = cls(
            extra_ids,
            disable_progress_bar=disable_progress_bar,
            transient_progress_bar=transient_progress_bar,
            backend=backend or meta.get("backend", "polars"),
        )
        scraper._apply_cache(source, meta=meta)

        return scraper
